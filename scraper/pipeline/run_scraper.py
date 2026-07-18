from core.fetcher import fetch_rss
from core.parser import relevan, deteksi_komoditas, deteksi_wilayah, deteksi_provinsi
from core.normalizer import normalisasi_artikel
from core.article_fetcher import perkaya_artikel
from config.sumber import SUMBER_BERITA
from storage.local_store import simpan_batch

def run(debug=False, fetch_isi_lengkap=True):
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

            # Fallback level provinsi -- HANYA diisi kalau tidak ada
            # kota/kabupaten spesifik yang terdeteksi. Kalau wilayah_terdeteksi
            # sudah ada isinya, provinsi_terdeteksi dikosongkan supaya tidak
            # ambigu field mana yang harus dipakai consumer downstream.
            wilayah_kota = artikel["wilayah_terdeteksi"]
            artikel["provinsi_terdeteksi"] = [] if wilayah_kota else deteksi_provinsi(teks)

            hasil.append(artikel)

    print(f"[INFO] {len(hasil)} artikel lolos filter relevansi.")

    if fetch_isi_lengkap and hasil:
        print("[INFO] Mengambil isi artikel lengkap (ini butuh waktu, ada delay antar-request)...")
        hasil = perkaya_artikel(hasil)

    simpan_batch(hasil)
    print(f"Selesai. {len(hasil)} artikel relevan disimpan.")


if __name__ == "__main__":
    run(debug=True)