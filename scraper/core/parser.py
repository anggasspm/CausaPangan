from config.komoditas import KOMODITAS_KEYWORDS
from config.wilayah import WILAYAH_TARGET

def deteksi_komoditas(teks: str) -> list[str]:
    teks_lower = teks.lower()
    return [kode for kode, sinonim in KOMODITAS_KEYWORDS.items()
            if any(k in teks_lower for k in sinonim)]

def deteksi_wilayah(teks: str) -> list[str]:
    teks_lower = teks.lower()
    hasil = []
    for kode_prov, data in WILAYAH_TARGET.items():
        if any(kota.lower() in teks_lower for kota in data["kota"]):
            hasil.append(kode_prov)
    return hasil

def relevan(judul: str, ringkasan: str) -> bool:
    teks = f"{judul} {ringkasan}"
    return bool(deteksi_komoditas(teks)) and bool(deteksi_wilayah(teks))