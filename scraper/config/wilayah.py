# WILAYAH_TARGET: kode kabupaten/kota (4 digit, standar Kemendagri/BPS)
# sebagai source of truth, nama kota hanya untuk matching teks berita.
#
# PENTING: kode-kode ini perlu diverifikasi ulang oleh Role 1 terhadap
# tabel resmi Kemendagri/BPS sebelum dipakai untuk join ke data harga
# Bapanas/PIHPS. Jangan dianggap final tanpa cross-check.

WILAYAH_TARGET = {
    # ---------------- JAWA BARAT (32) ----------------
    "3201": {"nama": "Kabupaten Bogor", "kota": ["Bogor"]},
    "3204": {"nama": "Kabupaten Bandung", "kota": ["Bandung"]},
    "3209": {"nama": "Kabupaten Cirebon", "kota": ["Cirebon"]},
    "3216": {"nama": "Kabupaten Bekasi", "kota": ["Bekasi"]},
    "3271": {"nama": "Kota Bogor", "kota": ["Bogor"]},
    "3273": {"nama": "Kota Bandung", "kota": ["Bandung"]},
    "3274": {"nama": "Kota Cirebon", "kota": ["Cirebon"]},
    "3275": {"nama": "Kota Bekasi", "kota": ["Bekasi"]},
    "3276": {"nama": "Kota Depok", "kota": ["Depok"]},
    "3277": {"nama": "Kota Cimahi", "kota": ["Cimahi"]},

    # ---------------- JAWA TENGAH (33) ----------------
    "3302": {"nama": "Kabupaten Banyumas", "kota": ["Banyumas", "Purwokerto"]},
    "3311": {"nama": "Kabupaten Sukoharjo", "kota": ["Sukoharjo"]},
    "3322": {"nama": "Kabupaten Semarang", "kota": ["Ungaran"]},
    "3326": {"nama": "Kabupaten Pekalongan", "kota": ["Pekalongan"]},
    "3328": {"nama": "Kabupaten Tegal", "kota": ["Tegal"]},
    "3371": {"nama": "Kota Magelang", "kota": ["Magelang"]},
    "3372": {"nama": "Kota Surakarta", "kota": ["Surakarta", "Solo"]},
    "3373": {"nama": "Kota Salatiga", "kota": ["Salatiga"]},
    "3374": {"nama": "Kota Semarang", "kota": ["Semarang"]},
    "3375": {"nama": "Kota Pekalongan", "kota": ["Pekalongan"]},
    "3376": {"nama": "Kota Tegal", "kota": ["Tegal"]},

    # ---------------- JAWA TIMUR (35) ----------------
    "3515": {"nama": "Kabupaten Sidoarjo", "kota": ["Sidoarjo"]},
    "3517": {"nama": "Kabupaten Jombang", "kota": ["Jombang"]},
    "3525": {"nama": "Kabupaten Gresik", "kota": ["Gresik"]},
    "3571": {"nama": "Kota Kediri", "kota": ["Kediri"]},
    "3572": {"nama": "Kota Blitar", "kota": ["Blitar"]},
    "3573": {"nama": "Kota Malang", "kota": ["Malang"]},
    "3577": {"nama": "Kota Madiun", "kota": ["Madiun"]},
    "3578": {"nama": "Kota Surabaya", "kota": ["Surabaya"]},
}