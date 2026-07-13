from core.fetcher import fetch_rss
from core.parser import relevan, deteksi_komoditas, deteksi_wilayah
from core.normalizer import normalisasi_artikel
from config.sumber import SUMBER_BERITA
from storage.local_store import simpan_batch
import json

def run(debug=True):
    hasil = []
    for sumber in SUMBER_BERITA:
        try:
            entries = fetch_rss(sumber["rss"])
        except Exception as e:
            print(f"[WARN] Gagal fetch {sumber['nama']}: {e}")
            continue

        print(f"[INFO] {sumber['nama']}: {len(entries)} entries ditemukan")

        for entry in entries:
            teks = f"{entry.title} {getattr(entry, 'summary', '')}"
            komoditas_match = deteksi_komoditas(teks)
            if debug:
                print(f"  - {entry.title[:70]}  -> komoditas: {komoditas_match}")

            if not relevan(entry.title, getattr(entry, "summary", "")):
                continue
            artikel = normalisasi_artikel(entry, sumber["nama"])
            artikel["komoditas_terdeteksi"] = komoditas_match
            artikel["wilayah_terdeteksi"] = deteksi_wilayah(teks)
            hasil.append(artikel)

    simpan_batch(hasil)
    print(f"Selesai. {len(hasil)} artikel relevan disimpan.")

if __name__ == "__main__":
    run()