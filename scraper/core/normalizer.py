from datetime import datetime
import pytz

WIB = pytz.timezone("Asia/Jakarta")

def ke_utc_iso8601(dt_struct, asumsi_wib=True) -> str:
    dt = datetime(*dt_struct[:6])
    if asumsi_wib:
        dt = WIB.localize(dt).astimezone(pytz.utc)
    else:
        dt = pytz.utc.localize(dt)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def normalisasi_artikel(entry, sumber_nama: str) -> dict:
    return {
        "judul": entry.title,
        "url": entry.link,
        "sumber_media": sumber_nama,
        "tanggal_terbit": ke_utc_iso8601(entry.published_parsed),
        "isi_teks": getattr(entry, "summary", ""),   # internal only, bukan field kontrak
        "komoditas_terdeteksi": [],  # diisi step filter
        "wilayah_terdeteksi": [],
    }