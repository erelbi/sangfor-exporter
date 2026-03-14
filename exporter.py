#!/usr/bin/env python3
"""
Sangfor SCP Prometheus Exporter

Ortam değişkenleri:
    SCP_HOST          — SCP IP ya da hostname (zorunlu)
    SCP_ACCESS_KEY    — EC2 access key (zorunlu, ec2 auth)
    SCP_SECRET_KEY    — EC2 secret key (zorunlu, ec2 auth)
    SCP_VERIFY_SSL    — SSL sertifikasını doğrula (varsayılan: false)
    EXPORTER_PORT     — HTTP dinleme portu (varsayılan: 9877)
    SCRAPE_INTERVAL   — Metrik yenileme aralığı saniye (varsayılan: 60)
    LOG_LEVEL         — Loglama seviyesi: DEBUG|INFO|WARNING (varsayılan: INFO)
"""
import logging
import os
import sys
import time

from prometheus_client import REGISTRY, start_http_server
from prometheus_client import PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sangfor_scp import SCPClient
from collector import SangforCollector


def _setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger("sangfor_exporter")

    # ---- Configuration ------------------------------------------------
    host = os.environ.get("SCP_HOST", "").strip()
    if not host:
        logger.error("SCP_HOST environment variable is required.")
        sys.exit(1)

    access_key = os.environ.get("SCP_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("SCP_SECRET_KEY", "").strip()

    if not access_key or not secret_key:
        logger.error("SCP_ACCESS_KEY and SCP_SECRET_KEY are required.")
        sys.exit(1)

    verify_ssl = os.environ.get("SCP_VERIFY_SSL", "false").lower() in ("true", "1", "yes")
    port = int(os.environ.get("EXPORTER_PORT", "9877"))
    refresh_interval = int(os.environ.get("SCRAPE_INTERVAL", "60"))

    # ---- SCP Client ---------------------------------------------------
    logger.info("Connecting to Sangfor SCP at https://%s", host)
    client = SCPClient(
        host=host,
        access_key=access_key,
        secret_key=secret_key,
        verify_ssl=verify_ssl,
    )

    # Retry adapter: sunucu keep-alive bağlantısını kapatırsa otomatik yeniden dener
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    client._session.mount("https://", adapter)
    client._session.mount("http://", adapter)

    # ---- Prometheus ---------------------------------------------------
    # Prometheus'un default process/platform metric'lerini kaldır
    # (opsiyonel — yorum satırına alınabilir)
    REGISTRY.unregister(PROCESS_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(GC_COLLECTOR)

    collector = SangforCollector(client=client, refresh_interval=refresh_interval)
    REGISTRY.register(collector)

    logger.info(
        "Sangfor SCP Exporter started — port=%d, refresh_interval=%ds, verify_ssl=%s",
        port, refresh_interval, verify_ssl,
    )
    start_http_server(port)

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Exporter stopped.")


if __name__ == "__main__":
    main()
