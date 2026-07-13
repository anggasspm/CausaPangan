import json
from datetime import datetime

def simpan_batch(data: list[dict], folder="seed_data"):
    filename = f"{folder}/berita_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)