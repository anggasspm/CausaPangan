import re
from config.komoditas import KOMODITAS_KEYWORDS
from config.wilayah import WILAYAH_TARGET, PROVINSI_TARGET


def deteksi_komoditas(teks: str) -> list[str]:
    teks_lower = teks.lower()
    return [kode for kode, sinonim in KOMODITAS_KEYWORDS.items()
            if any(k in teks_lower for k in sinonim)]


def _cari_kandidat(teks_lower: str) -> dict[str, list[str]]:
    """
    Return {nama_kota_lower: [daftar kode_wilayah yang punya nama itu]}
    Dipakai untuk tahu kota mana yang ambigu (dimiliki >1 kode_wilayah).
    """
    kandidat = {}
    for kode_wilayah, data in WILAYAH_TARGET.items():
        for kota in data["kota"]:
            kota_lower = kota.lower()
            if kota_lower in teks_lower:
                kandidat.setdefault(kota_lower, []).append(kode_wilayah)
    return kandidat


def deteksi_wilayah(teks: str) -> list[str]:
    """
    Deteksi kode_wilayah (kab/kota, 4 digit) yang disebut dalam teks.

    Kalau nama kota dimiliki lebih dari satu kode_wilayah (mis. "Semarang"
    ada di Kabupaten Semarang & Kota Semarang), coba disambiguasi pakai
    kata "kota"/"kabupaten"/"kab." yang muncul tepat sebelum nama kota.
    Kalau tidak ada penanda eksplisit, KEDUANYA dikembalikan -- lebih
    aman daripada menebak salah satu secara diam-diam.
    """
    teks_lower = teks.lower()
    kandidat = _cari_kandidat(teks_lower)
    hasil = set()

    for kota_lower, daftar_kode in kandidat.items():
        if len(daftar_kode) == 1:
            hasil.add(daftar_kode[0])
            continue

        # ambigu -> cek prefix "kota"/"kabupaten"/"kab." di depan nama kota
        cocok_kota = re.search(rf"\bkota\s+{re.escape(kota_lower)}", teks_lower)
        cocok_kab = re.search(rf"\bkab(?:upaten|\.)?\s+{re.escape(kota_lower)}", teks_lower)

        ditemukan_spesifik = False
        for kode_wilayah in daftar_kode:
            nama_wilayah = WILAYAH_TARGET[kode_wilayah]["nama"].lower()
            if cocok_kota and nama_wilayah.startswith("kota"):
                hasil.add(kode_wilayah)
                ditemukan_spesifik = True
            elif cocok_kab and nama_wilayah.startswith("kabupaten"):
                hasil.add(kode_wilayah)
                ditemukan_spesifik = True

        if not ditemukan_spesifik:
            # tidak ada penanda eksplisit -> masukkan semua kandidat,
            # biar tidak diam-diam salah assign
            hasil.update(daftar_kode)

    return list(hasil)


def deteksi_provinsi(teks: str) -> list[str]:
    """
    Deteksi kode_provinsi (2 digit) yang disebut dalam teks.

    Dipakai SEBAGAI FALLBACK TERPISAH -- untuk kasus artikel yang tidak
    menyebut kota/kabupaten spesifik apapun (wilayah_terdeteksi kosong)
    tapi jelas membahas satu/lebih provinsi secara umum. Ini mayoritas
    kasus untuk berita ekonomi nasional (Bulog, Kementan, PIHPS) yang
    bicara level provinsi/nasional, bukan kota tertentu.

    SENGAJA dikembalikan sebagai field terpisah (provinsi_terdeteksi),
    BUKAN digabung ke dalam wilayah_terdeteksi -- supaya tidak mencampur
    kode 4-digit (kab/kota) dengan kode 2-digit (provinsi) dalam satu
    array yang sama, yang akan salah diinterpretasikan sebagai kode
    kab/kota oleh consumer downstream (Role 2/Role 1 backend).
    """
    teks_lower = teks.lower()
    hasil = []
    for kode_provinsi, data in PROVINSI_TARGET.items():
        if any(alias in teks_lower for alias in data["alias"]):
            hasil.append(kode_provinsi)
    return hasil


def relevan(judul: str, ringkasan: str) -> bool:
    teks = f"{judul} {ringkasan}"
    return bool(deteksi_komoditas(teks))  # wilayah dilonggarkan dulu