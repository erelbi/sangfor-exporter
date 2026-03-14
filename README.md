# sangfor-exporter

Prometheus exporter for Sangfor SCP (Software Cloud Platform) HCI environments.
Collects metrics from the SCP API and exposes them on a `/metrics` HTTP endpoint
for scraping by Prometheus.

Built on top of the [sangfor-scp](https://github.com/erelbi/sangfor-scp) Python client library.
Thanks to that project for handling authentication, pagination, and API abstractions.

---

## Features

- Virtual machine counts by status, resource pool, and tenant
- Physical host availability and capacity (CPU cores, memory)
- Resource pool (AZ) CPU, memory, and storage utilization from physical resources
- GlusterFS storage tier breakdown — capacity and allocation per tier
- Tenant count
- EIP (Elastic IP) allocation status
- Grafana dashboard with AZ-level filtering
- Docker Compose stack including Prometheus and Grafana

---

## Requirements

- Python 3.9 or later
- A Sangfor SCP environment with EC2 (AK/SK) credentials
- Docker and Docker Compose (for containerized deployment)

---

## Quick Start

### Running with Docker Compose

```bash
git clone https://github.com/erelbi/sangfor-exporter.git
cd sangfor-exporter

cp .env.example .env
# Edit .env and fill in SCP_HOST, SCP_ACCESS_KEY, SCP_SECRET_KEY

docker compose up -d
```

Services:

| Service | URL |
|---------|-----|
| Exporter metrics | http://localhost:9877/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana default credentials: `admin / admin` (configurable via `GRAFANA_PASSWORD` in `.env`).
The Sangfor SCP dashboard is provisioned automatically on first startup.

### Running directly with Python

```bash
pip install -r requirements.txt

export SCP_HOST=192.168.1.100
export SCP_ACCESS_KEY=your_access_key
export SCP_SECRET_KEY=your_secret_key

python3 exporter.py
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCP_HOST` | — | SCP IP address or hostname (required) |
| `SCP_ACCESS_KEY` | — | EC2 access key (required) |
| `SCP_SECRET_KEY` | — | EC2 secret key (required) |
| `SCP_VERIFY_SSL` | `false` | Verify SSL certificate |
| `EXPORTER_PORT` | `9877` | HTTP listen port |
| `SCRAPE_INTERVAL` | `60` | Metric refresh interval in seconds |
| `LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING |

---

## Metrics Reference

### Virtual Machines

| Metric | Labels | Description |
|--------|--------|-------------|
| `sangfor_servers_total` | — | Total VM count |
| `sangfor_server_up` | server_id, name, az_id, tenant_id, status | 1 if VM is running |
| `sangfor_server_cores` | server_id, name, az_id, tenant_id | vCPU count |
| `sangfor_server_memory_bytes` | server_id, name, az_id, tenant_id | Allocated memory |

### Resource Pools (AZs)

| Metric | Labels | Description |
|--------|--------|-------------|
| `sangfor_resource_pool_up` | az_id, az_name, type | 1 if pool is online |
| `sangfor_resource_pool_cpu_total` | az_id, az_name | Total CPU capacity (MHz) |
| `sangfor_resource_pool_cpu_used` | az_id, az_name | Used CPU (MHz) |
| `sangfor_resource_pool_memory_total_bytes` | az_id, az_name | Total memory |
| `sangfor_resource_pool_memory_used_bytes` | az_id, az_name | Used memory |
| `sangfor_resource_pool_storage_total_bytes` | az_id, az_name | Total storage |
| `sangfor_resource_pool_storage_used_bytes` | az_id, az_name | Used storage |

### GlusterFS Storage Tiers

| Metric | Labels | Description |
|--------|--------|-------------|
| `sangfor_storage_tier_total_bytes` | tier, az_id, az_name | Usable capacity per tier |
| `sangfor_storage_tier_allocated_bytes` | tier, az_id, az_name | Allocated capacity per tier |

### Physical Hosts

| Metric | Labels | Description |
|--------|--------|-------------|
| `sangfor_host_up` | host_id, name, az_id | 1 if host is online |
| `sangfor_host_cpu_total` | host_id, name, az_id | Physical CPU core count |
| `sangfor_host_memory_total_bytes` | host_id, name, az_id | Physical memory |

### Platform Overview

| Metric | Description |
|--------|-------------|
| `sangfor_hosts_total` | Total physical host count |
| `sangfor_hosts_online_total` | Online physical host count |
| `sangfor_az_total` | Total AZ count |
| `sangfor_tenants_total` | Total tenant count |
| `sangfor_eips_total` | Total EIP count |
| `sangfor_eips_bound_total` | Bound EIP count |
| `sangfor_eips_unbound_total` | Unbound EIP count |

### Exporter Health

| Metric | Description |
|--------|-------------|
| `sangfor_up` | 1 if last API scrape succeeded |
| `sangfor_scrape_success` | 1 if last collection succeeded |
| `sangfor_scrape_duration_seconds` | Duration of last collection |

---

## Grafana Dashboard

The dashboard is automatically provisioned when using Docker Compose.
For manual import, use the JSON file at:

```
grafana/provisioning/dashboards/sangfor-scp.json
```

The dashboard includes a Resource Pool dropdown at the top. Selecting a specific AZ
filters all panels to that pool. Selecting "All" shows platform-wide data.

Dashboard sections:

- Platform Overview — VM counts, host counts, AZ count, API status
- Resource Utilization — CPU, memory, and storage usage gauges
- Per AZ Utilization — bar gauges broken down by resource pool
- Virtual Machines — VM distribution by status, AZ, and tenant
- Storage Tiers (GlusterFS) — per-tier capacity and allocation breakdown
- Elastic IPs — EIP binding status
- Exporter Health — scrape duration and success

---

## Notes

- Sangfor HCI uses a distributed filesystem (GlusterFS). There are typically no
  standalone block volumes. Storage metrics come from the GlusterFS tier data
  exposed by the SCP API under `virtual_resources`.
- The exporter refreshes metrics in a background thread. The Prometheus scrape
  interval and `SCRAPE_INTERVAL` can be set independently.
- Self-signed certificates are common in SCP deployments. Set `SCP_VERIFY_SSL=false`
  to skip certificate verification.
- Tested against SCP version 6.11.2.

---

## Acknowledgements

This exporter relies on [sangfor-scp](https://github.com/erelbi/sangfor-scp),
a Python client library for the Sangfor SCP API. Authentication, pagination,
and resource abstractions are handled by that library.

---

---

# sangfor-exporter (Türkçe)

Sangfor SCP (Software Cloud Platform) HCI ortamları için Prometheus exporter.
SCP API'sinden metrik toplar ve Prometheus tarafından scrape edilmek üzere
`/metrics` HTTP endpoint'inde sunar.

[sangfor-scp](https://github.com/erelbi/sangfor-scp) Python istemci kütüphanesi
üzerine inşa edilmiştir. Kimlik doğrulama, sayfalama ve API soyutlamaları için
bu projeye teşekkürler.

---

## Özellikler

- Sanal makine sayıları: durum, resource pool ve tenant bazında
- Fiziksel host erişilebilirliği ve kapasitesi (CPU, bellek)
- Resource pool (AZ) CPU, bellek ve depolama kullanımı (fiziksel kaynaklar)
- GlusterFS storage tier dökümü: tier başına kapasite ve tahsisat
- Tenant sayısı
- EIP (Elastic IP) bağlanma durumu
- AZ bazında filtreleme destekleyen Grafana dashboard
- Prometheus ve Grafana dahil Docker Compose stack

---

## Gereksinimler

- Python 3.9 veya üstü
- EC2 (AK/SK) kimlik bilgileri olan bir Sangfor SCP ortamı
- Docker ve Docker Compose (konteyner ile kullanım için)

---

## Hızlı Başlangıç

### Docker Compose ile

```bash
git clone https://github.com/erelbi/sangfor-exporter.git
cd sangfor-exporter

cp .env.example .env
# .env dosyasını düzenle: SCP_HOST, SCP_ACCESS_KEY, SCP_SECRET_KEY gir

docker compose up -d
```

Servisler:

| Servis | Adres |
|--------|-------|
| Exporter metrikleri | http://localhost:9877/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana varsayılan giriş: `admin / admin` (`.env` içindeki `GRAFANA_PASSWORD` ile değiştirilebilir).
Sangfor SCP dashboard ilk başlatmada otomatik yüklenir.

### Python ile doğrudan

```bash
pip install -r requirements.txt

export SCP_HOST=192.168.1.100
export SCP_ACCESS_KEY=erisim_anahtari
export SCP_SECRET_KEY=gizli_anahtar

python3 exporter.py
```

---

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `SCP_HOST` | — | SCP IP adresi veya hostname (zorunlu) |
| `SCP_ACCESS_KEY` | — | EC2 erişim anahtarı (zorunlu) |
| `SCP_SECRET_KEY` | — | EC2 gizli anahtar (zorunlu) |
| `SCP_VERIFY_SSL` | `false` | SSL sertifikası doğrulama |
| `EXPORTER_PORT` | `9877` | HTTP dinleme portu |
| `SCRAPE_INTERVAL` | `60` | Metrik yenileme aralığı (saniye) |
| `LOG_LEVEL` | `INFO` | Log seviyesi: DEBUG, INFO, WARNING |

---

## Notlar

- Sangfor HCI dağıtık bir dosya sistemi (GlusterFS) kullanır. Genellikle bağımsız
  blok volume bulunmaz. Depolama metrikleri, SCP API'sinin `virtual_resources`
  alanında sunduğu GlusterFS tier verilerinden gelir.
- Exporter, metrikleri bir arka plan thread'inde yeniler. Prometheus scrape
  aralığı ile `SCRAPE_INTERVAL` bağımsız olarak ayarlanabilir.
- SCP kurulumlarında self-signed sertifika yaygındır. Sertifika doğrulamayı
  atlamak için `SCP_VERIFY_SSL=false` kullanın.
- SCP 6.11.2 sürümünde test edilmiştir.

---

## Teşekkür

Bu exporter, Sangfor SCP API için bir Python istemci kütüphanesi olan
[sangfor-scp](https://github.com/erelbi/sangfor-scp) projesine dayanmaktadır.
Kimlik doğrulama, sayfalama ve kaynak soyutlamaları bu kütüphane tarafından sağlanmaktadır.
