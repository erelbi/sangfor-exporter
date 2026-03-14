#!/usr/bin/env python3
"""
Grafana.com dashboard yayını için sangfor-scp.json'u dönüştürür.

Provisioning versiyonu ${datasource} variable kullanır (Docker Compose için).
Grafana.com versiyonu ${DS_PROMETHEUS} kullanır (import sırasında çözümlenir).

Kullanım:
    python3 export_for_grafana_com.py
    # sangfor-scp-grafana-com.json dosyası oluşturulur
"""
import json

SRC = "grafana/provisioning/dashboards/sangfor-scp.json"
DST = "sangfor-scp-grafana-com.json"

with open(SRC) as f:
    content = f.read()

content = content.replace('"uid": "${datasource}"', '"uid": "${DS_PROMETHEUS}"')
content = content.replace(
    '"datasource": {"type": "prometheus", "uid": "${datasource}"}',
    '"datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}',
)

data = json.loads(content)

# id null olmalı Grafana.com import için
data["id"] = None

with open(DST, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Grafana.com versiyonu olusturuldu: {DST}")
print(f"Bu dosyayi grafana.com/grafana/dashboards adresinden yukleyebilirsiniz.")
