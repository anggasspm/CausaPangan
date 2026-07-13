import json
import os
from datetime import datetime

def simpan_batch(data: list[dict], folder="seed_data"):
    os.makedirs(folder, exist_ok=True)
    
    # Simpan snapshot per-run (untuk histori/debug)
    filename = f"{folder}/berita_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Simpan juga versi "latest" (untuk dikonsumsi Role 1 sebagai seed data terbaru)
    latest_path = f"{folder}/latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[STORAGE] Disimpan ke {filename} dan {latest_path}")