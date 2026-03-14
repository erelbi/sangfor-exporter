"""
Sangfor SCP Prometheus Collector

Her scrape için API'den metrik toplar.
Bir arka plan thread'i belirli aralıklarla verileri yeniler;
collect() sadece önbelleği döndürür.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Iterator, List, Optional

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from sangfor_scp import SCPClient

logger = logging.getLogger(__name__)


class SangforCollector(Collector):
    """Sangfor SCP için Prometheus Collector."""

    def __init__(self, client: SCPClient, refresh_interval: int = 60) -> None:
        self._client = client
        self._refresh_interval = refresh_interval
        self._cache: List[Any] = []
        self._lock = threading.Lock()

        # İlk yüklemeyi senkron yap (exporter başlarken boş dönmesin)
        logger.info("Initial metrics collection started...")
        try:
            self._cache = self._build_metrics()
            logger.info("Initial metrics collection completed.")
        except Exception as exc:
            logger.error("Initial metrics collection failed: %s", exc)

        # Arka plan yenileme thread'i
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ #
    # Prometheus Collector interface                                       #
    # ------------------------------------------------------------------ #

    def collect(self) -> Iterator:
        with self._lock:
            yield from self._cache

    # ------------------------------------------------------------------ #
    # Background refresh                                                  #
    # ------------------------------------------------------------------ #

    def _refresh_loop(self) -> None:
        while True:
            time.sleep(self._refresh_interval)
            logger.debug("Refreshing metrics...")
            try:
                new_metrics = self._build_metrics()
                with self._lock:
                    self._cache = new_metrics
                logger.debug("Metrics refreshed successfully.")
            except Exception as exc:
                logger.error("Metrics refresh failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Main build                                                          #
    # ------------------------------------------------------------------ #

    def _build_metrics(self) -> List[Any]:
        start = time.time()
        metrics: List[Any] = []
        success = 1

        try:
            metrics.extend(self._collect_overview())
        except Exception as exc:
            logger.warning("overview collection failed: %s", exc)
            success = 0

        try:
            metrics.extend(self._collect_resource_pools())
        except Exception as exc:
            logger.warning("resource_pools collection failed: %s", exc)

        try:
            metrics.extend(self._collect_servers())
        except Exception as exc:
            logger.warning("servers collection failed: %s", exc)
            success = 0

        try:
            metrics.extend(self._collect_volumes())
        except Exception as exc:
            logger.warning("volumes collection failed: %s", exc)

        try:
            metrics.extend(self._collect_tenants())
        except Exception as exc:
            logger.warning("tenants collection failed: %s", exc)

        try:
            metrics.extend(self._collect_hosts())
        except Exception as exc:
            logger.warning("hosts collection failed: %s", exc)

        try:
            metrics.extend(self._collect_eips())
        except Exception as exc:
            logger.debug("EIPs collection skipped (might not be configured): %s", exc)

        duration = time.time() - start

        g = GaugeMetricFamily(
            "sangfor_up",
            "1 if last SCP API scrape was successful",
        )
        g.add_metric([], float(success))
        metrics.append(g)

        g = GaugeMetricFamily(
            "sangfor_scrape_duration_seconds",
            "Duration of the last SCP metrics collection in seconds",
        )
        g.add_metric([], duration)
        metrics.append(g)

        g = GaugeMetricFamily(
            "sangfor_scrape_success",
            "1 if the last SCP metrics collection succeeded",
        )
        g.add_metric([], float(success))
        metrics.append(g)

        return metrics

    # ------------------------------------------------------------------ #
    # Overview (platform-wide summary)                                    #
    # ------------------------------------------------------------------ #

    def _collect_overview(self) -> List[Any]:
        metrics: List[Any] = []
        ov = self._client.resource_pools.overview()

        host_info = ov.get("host", {})
        server_info = ov.get("server", {})
        az_info = ov.get("az", {})

        _gauge(metrics, "sangfor_hosts_total",
               "Total physical host count (platform overview)",
               float(host_info.get("total", 0)))
        _gauge(metrics, "sangfor_hosts_online_total",
               "Online physical host count (platform overview)",
               float(host_info.get("online_count", 0)))

        _gauge(metrics, "sangfor_overview_servers_total",
               "Total VM count reported by platform overview",
               float(server_info.get("total", 0)))
        _gauge(metrics, "sangfor_overview_servers_running",
               "Running VM count reported by platform overview",
               float(server_info.get("running_count", 0)))

        _gauge(metrics, "sangfor_az_total",
               "Total AZ (resource pool) count",
               float(az_info.get("total", 0)))
        _gauge(metrics, "sangfor_az_online_total",
               "Online AZ count",
               float(az_info.get("online_count", 0)))

        # Platform-wide physical resources (actual usage)
        # physical_resources: [{name: cpu/memory/storage, total, used, unit}]
        for res in ov.get("physical_resources", []):
            name = res.get("name", "").lower()
            total = float(res.get("total", 0))
            used = float(res.get("used", 0))

            if name == "cpu":
                # unit: mhz
                _gauge(metrics, "sangfor_platform_cpu_total",
                       "Platform total CPU capacity (MHz)", total)
                _gauge(metrics, "sangfor_platform_cpu_used",
                       "Platform used CPU (MHz)", used)
            elif name == "memory":
                # unit: mb → bytes
                _gauge(metrics, "sangfor_platform_memory_bytes_total",
                       "Platform total memory (bytes)", total * 1024 * 1024)
                _gauge(metrics, "sangfor_platform_memory_bytes_used",
                       "Platform used memory (bytes)", used * 1024 * 1024)
            elif name == "storage":
                # unit: mb → bytes
                _gauge(metrics, "sangfor_platform_storage_bytes_total",
                       "Platform total storage (bytes)", total * 1024 * 1024)
                _gauge(metrics, "sangfor_platform_storage_bytes_used",
                       "Platform used storage (bytes)", used * 1024 * 1024)

        return metrics

    # ------------------------------------------------------------------ #
    # Resource pools (AZs)                                                #
    # ------------------------------------------------------------------ #

    def _collect_resource_pools(self) -> List[Any]:
        up_g = GaugeMetricFamily(
            "sangfor_resource_pool_up",
            "1 if resource pool is online",
            labels=["az_id", "az_name", "type"],
        )
        cpu_total = GaugeMetricFamily(
            "sangfor_resource_pool_cpu_total",
            "Total vCPU count in resource pool",
            labels=["az_id", "az_name"],
        )
        cpu_used = GaugeMetricFamily(
            "sangfor_resource_pool_cpu_used",
            "Used vCPU count in resource pool",
            labels=["az_id", "az_name"],
        )
        mem_total = GaugeMetricFamily(
            "sangfor_resource_pool_memory_total_bytes",
            "Total memory in resource pool (bytes)",
            labels=["az_id", "az_name"],
        )
        mem_used = GaugeMetricFamily(
            "sangfor_resource_pool_memory_used_bytes",
            "Used memory in resource pool (bytes)",
            labels=["az_id", "az_name"],
        )
        stor_total = GaugeMetricFamily(
            "sangfor_resource_pool_storage_total_bytes",
            "Total storage in resource pool (bytes)",
            labels=["az_id", "az_name"],
        )
        stor_used = GaugeMetricFamily(
            "sangfor_resource_pool_storage_used_bytes",
            "Used storage in resource pool (bytes)",
            labels=["az_id", "az_name"],
        )

        pools = self._client.resource_pools.list()
        for pool in pools:
            az_id = pool.get("id", "")
            az_name = pool.get("name", "")
            az_type = pool.get("type", "")
            status = pool.get("status", "")
            # "normal" → SCP'nin online durumu
            is_up = 1.0 if status in ("online", "active", "running", "normal") else 0.0
            labels = [az_id, az_name]

            up_g.add_metric([az_id, az_name, az_type], is_up)

            # Try detailed endpoint for resource data, fall back to list item
            try:
                detail = self._client.resource_pools.get(az_id)
            except Exception:
                detail = pool

            # physical_resources: [{name, total, used, unit}]
            for res in detail.get("physical_resources", []):
                name = res.get("name", "").lower()
                total = float(res.get("total", 0))
                used = float(res.get("used", 0))

                if name == "cpu":
                    # unit: mhz
                    cpu_total.add_metric(labels, total)
                    cpu_used.add_metric(labels, used)
                elif name == "memory":
                    # unit: mb → bytes
                    mem_total.add_metric(labels, total * 1024 * 1024)
                    mem_used.add_metric(labels, used * 1024 * 1024)
                elif name == "storage":
                    # unit: mb → bytes
                    stor_total.add_metric(labels, total * 1024 * 1024)
                    stor_used.add_metric(labels, used * 1024 * 1024)

        return [up_g, cpu_total, cpu_used, mem_total, mem_used, stor_total, stor_used]

    # ------------------------------------------------------------------ #
    # Servers (VMs)                                                       #
    # ------------------------------------------------------------------ #

    def _collect_servers(self) -> List[Any]:
        metrics: List[Any] = []

        status_counts: Dict[str, int] = {}
        az_counts: Dict[str, int] = {}
        tenant_counts: Dict[str, int] = {}
        total = 0

        server_up = GaugeMetricFamily(
            "sangfor_server_up",
            "1 if VM is in running state",
            labels=["server_id", "name", "az_id", "tenant_id", "status"],
        )
        server_cores = GaugeMetricFamily(
            "sangfor_server_cores",
            "VM vCPU count",
            labels=["server_id", "name", "az_id", "tenant_id"],
        )
        server_memory = GaugeMetricFamily(
            "sangfor_server_memory_bytes",
            "VM allocated memory (bytes)",
            labels=["server_id", "name", "az_id", "tenant_id"],
        )

        for vm in self._client.servers.list_all():
            total += 1
            sid = vm.get("id", "")
            name = vm.get("name", "")
            az_id = vm.get("az_id", "")
            tenant_id = vm.get("tenant_id", "")
            status = vm.get("status", "unknown")
            cores = float(vm.get("cores", 0))
            memory_mb = float(vm.get("memory_mb", 0))

            status_counts[status] = status_counts.get(status, 0) + 1
            az_counts[az_id] = az_counts.get(az_id, 0) + 1
            tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1

            is_running = 1.0 if status == "running" else 0.0
            server_up.add_metric([sid, name, az_id, tenant_id, status], is_running)
            server_cores.add_metric([sid, name, az_id, tenant_id], cores)
            server_memory.add_metric([sid, name, az_id, tenant_id], memory_mb * 1024 * 1024)

        _gauge(metrics, "sangfor_servers_total", "Total VM count", float(total))

        by_status = GaugeMetricFamily(
            "sangfor_servers_by_status",
            "VM count grouped by status",
            labels=["status"],
        )
        for status, count in status_counts.items():
            by_status.add_metric([status], float(count))
        metrics.append(by_status)

        by_az = GaugeMetricFamily(
            "sangfor_servers_by_az",
            "VM count grouped by resource pool",
            labels=["az_id"],
        )
        for az_id, count in az_counts.items():
            by_az.add_metric([az_id], float(count))
        metrics.append(by_az)

        by_tenant = GaugeMetricFamily(
            "sangfor_servers_by_tenant",
            "VM count grouped by tenant",
            labels=["tenant_id"],
        )
        for tid, count in tenant_counts.items():
            by_tenant.add_metric([tid], float(count))
        metrics.append(by_tenant)

        metrics.extend([server_up, server_cores, server_memory])
        return metrics

    # ------------------------------------------------------------------ #
    # Volumes                                                             #
    # ------------------------------------------------------------------ #

    def _collect_volumes(self) -> List[Any]:
        metrics: List[Any] = []

        total = 0
        total_size_mb = 0.0
        status_counts: Dict[str, int] = {}

        vol_size = GaugeMetricFamily(
            "sangfor_volume_size_bytes",
            "Individual volume size (bytes)",
            labels=["volume_id", "name", "status", "az_id"],
        )

        for vol in self._client.volumes.list_all():
            total += 1
            vid = vol.get("id", "")
            name = vol.get("name", "")
            az_id = vol.get("az_id", "")
            status = vol.get("status", "unknown")
            size_mb = float(vol.get("size_mb", 0))

            total_size_mb += size_mb
            status_counts[status] = status_counts.get(status, 0) + 1
            vol_size.add_metric([vid, name, status, az_id], size_mb * 1024 * 1024)

        _gauge(metrics, "sangfor_volumes_total", "Total volume count", float(total))
        _gauge(metrics, "sangfor_volumes_total_size_bytes",
               "Sum of all volume sizes (bytes)", total_size_mb * 1024 * 1024)

        by_status = GaugeMetricFamily(
            "sangfor_volumes_by_status",
            "Volume count grouped by status",
            labels=["status"],
        )
        for status, count in status_counts.items():
            by_status.add_metric([status], float(count))
        metrics.append(by_status)
        metrics.append(vol_size)
        return metrics

    # ------------------------------------------------------------------ #
    # Tenants                                                             #
    # ------------------------------------------------------------------ #

    def _collect_tenants(self) -> List[Any]:
        metrics: List[Any] = []
        total = 0
        enabled = 0

        for tenant in self._client.tenants.list_all():
            total += 1
            if tenant.get("enabled", False):
                enabled += 1

        _gauge(metrics, "sangfor_tenants_total", "Total tenant count", float(total))
        _gauge(metrics, "sangfor_tenants_enabled", "Enabled tenant count", float(enabled))
        return metrics

    # ------------------------------------------------------------------ #
    # Physical hosts                                                      #
    # ------------------------------------------------------------------ #

    def _collect_hosts(self) -> List[Any]:
        host_up = GaugeMetricFamily(
            "sangfor_host_up",
            "1 if physical host is online",
            labels=["host_id", "name", "az_id"],
        )
        host_cpu = GaugeMetricFamily(
            "sangfor_host_cpu_total",
            "Physical host CPU core count",
            labels=["host_id", "name", "az_id"],
        )
        host_mem = GaugeMetricFamily(
            "sangfor_host_memory_total_bytes",
            "Physical host total memory (bytes)",
            labels=["host_id", "name", "az_id"],
        )

        for host in self._client.system.list_all_hosts():
            hid = host.get("id", "")
            hname = host.get("name", host.get("hostname", ""))
            az_id = host.get("az_id", "")
            status = host.get("status", "")
            is_up = 1.0 if status in ("online", "running", "active") else 0.0
            labels = [hid, hname, az_id]

            host_up.add_metric(labels, is_up)

            # CPU bilgisi nested dict: host["cpu"]["core_count"]
            cpu_info = host.get("cpu", {})
            if isinstance(cpu_info, dict):
                cpu_count = float(cpu_info.get("core_count", cpu_info.get("cpus", 0)))
            else:
                cpu_count = float(cpu_info)

            # Memory bilgisi nested dict: host["memory"]["total_mb"]
            mem_info = host.get("memory", {})
            if isinstance(mem_info, dict):
                mem_mb = float(mem_info.get("total_mb", mem_info.get("memory_mb", 0)))
            else:
                mem_mb = float(mem_info)

            host_cpu.add_metric(labels, cpu_count)
            host_mem.add_metric(labels, mem_mb * 1024 * 1024)

        return [host_up, host_cpu, host_mem]

    # ------------------------------------------------------------------ #
    # EIPs (Floating IPs)                                                 #
    # ------------------------------------------------------------------ #

    def _collect_eips(self) -> List[Any]:
        metrics: List[Any] = []
        total = 0
        bound = 0
        unbound = 0

        eip_g = GaugeMetricFamily(
            "sangfor_eip_bound",
            "1 if EIP is bound to a VM",
            labels=["eip_id", "ip", "az_id"],
        )

        for eip in self._client.eips.list_all():
            total += 1
            eid = eip.get("id", "")
            ip = eip.get("ip", eip.get("address", ""))
            az_id = eip.get("az_id", "")
            is_bound = 1.0 if eip.get("server_id") else 0.0

            if is_bound:
                bound += 1
            else:
                unbound += 1

            eip_g.add_metric([eid, ip, az_id], is_bound)

        _gauge(metrics, "sangfor_eips_total", "Total EIP count", float(total))
        _gauge(metrics, "sangfor_eips_bound_total", "Bound EIP count", float(bound))
        _gauge(metrics, "sangfor_eips_unbound_total", "Unbound (free) EIP count", float(unbound))
        metrics.append(eip_g)
        return metrics


# ------------------------------------------------------------------ #
# Helper                                                              #
# ------------------------------------------------------------------ #

def _gauge(metrics: List[Any], name: str, doc: str, value: float) -> None:
    """Tek değerli bir GaugeMetricFamily oluşturup listeye ekler."""
    g = GaugeMetricFamily(name, doc)
    g.add_metric([], value)
    metrics.append(g)
