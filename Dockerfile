FROM python:3.11-slim

LABEL maintainer="sangfor-scp-exporter"
LABEL description="Prometheus exporter for Sangfor SCP cloud platform"

WORKDIR /app

# Bağımlılıkları önce kopyala (layer cache için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kaynak dosyaları kopyala
COPY exporter.py collector.py ./

# Prometheus metrics portu
EXPOSE 9877

# Varsayılan ortam değişkenleri
ENV SCP_HOST="" \
    SCP_ACCESS_KEY="" \
    SCP_SECRET_KEY="" \
    SCP_VERIFY_SSL="false" \
    EXPORTER_PORT="9877" \
    SCRAPE_INTERVAL="60" \
    LOG_LEVEL="INFO"

# Root olmayan kullanıcı ile çalıştır
RUN useradd -r -u 1000 -s /sbin/nologin exporter
USER exporter

CMD ["python", "exporter.py"]
