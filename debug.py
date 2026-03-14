#!/usr/bin/env python3
"""
Ham API yanıtlarını görmek için debug scripti.
Kullanım: python3 debug.py
"""
import json
import os
import sys

from sangfor_scp import SCPClient

host = os.environ.get("SCP_HOST", "")
ak   = os.environ.get("SCP_ACCESS_KEY", "")
sk   = os.environ.get("SCP_SECRET_KEY", "")

if not all([host, ak, sk]):
    print("ERROR: SCP_HOST, SCP_ACCESS_KEY, SCP_SECRET_KEY gerekli")
    sys.exit(1)

client = SCPClient(host=host, access_key=ak, secret_key=sk, verify_ssl=False)

def dump(label, obj):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)
    print(json.dumps(obj, indent=2, default=str, ensure_ascii=False))

# 1. Overview
try:
    ov = client.resource_pools.overview()
    dump("resource_pools.overview()", ov)
except Exception as e:
    print(f"\n[!] overview() HATA: {e}")

# 2. Resource pool listesi
try:
    pools = client.resource_pools.list()
    dump("resource_pools.list() — ilk kayıt", pools[0] if pools else [])

    # İlk pool için get()
    if pools:
        az_id = pools[0].get("id", "")
        try:
            detail = client.resource_pools.get(az_id)
            dump(f"resource_pools.get({az_id!r})", detail)
        except Exception as e:
            print(f"\n[!] resource_pools.get() HATA: {e}")
except Exception as e:
    print(f"\n[!] resource_pools.list() HATA: {e}")

# 3. Volumes
try:
    vols = list(client.volumes.list_all())
    dump("volumes.list_all() — ilk kayıt", vols[0] if vols else "BOŞ LISTE")
    print(f"  Toplam volume sayısı: {len(vols)}")
except Exception as e:
    print(f"\n[!] volumes.list_all() HATA: {e}")

# 4. Hosts
try:
    hosts = list(client.system.list_all_hosts())
    dump("system.list_all_hosts() — ilk host", hosts[0] if hosts else [])
except Exception as e:
    print(f"\n[!] list_all_hosts() HATA: {e}")
