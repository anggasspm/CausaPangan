"""
Enum `penyebab` — SESUAI API_CONTRACT.md §5.1

PENTING: Role 2 (NLP & ML) adalah owner enum ini. Menambah/mengubah value
WAJIB melalui proses berikut (jangan langsung ubah file ini):
  1. Diskusikan & sepakati di grup tim
  2. Update API_CONTRACT.md §5 terlebih dahulu
  3. Baru update enum ini + informasikan ke Role Frontend (Role 3) karena
     mereka mapping value ini ke label display & warna di peta.

Jangan menambahkan value baru di sini tanpa mengikuti proses di atas,
walau modelnya "ingin" mengembalikan kategori baru saat inference.
"""

from enum import Enum


class Penyebab(str, Enum):
    CUACA_GAGAL_PANEN = "cuaca_gagal_panen"
    GANGGUAN_DISTRIBUSI = "gangguan_distribusi"
    PENIMBUNAN_SPEKULASI = "penimbunan_spekulasi"
    KENAIKAN_BIAYA_INPUT = "kenaikan_biaya_input"
    LONJAKAN_PERMINTAAN_MUSIMAN = "lonjakan_permintaan_musiman"
    KEBIJAKAN_PEMERINTAH = "kebijakan_pemerintah"
    FAKTOR_GLOBAL = "faktor_global"


# Deskripsi singkat tiap kategori — dipakai untuk membangun system prompt LLM.
# Sumber: API_CONTRACT.md §5.1 dan PRD §5.4.
PENYEBAB_DESKRIPSI: dict[Penyebab, str] = {
    Penyebab.CUACA_GAGAL_PANEN: (
        "Cuaca ekstrem (kekeringan, curah hujan tinggi, banjir) atau bencana alam "
        "yang menyebabkan gagal panen / penurunan volume & kualitas hasil panen di "
        "wilayah sentra produksi."
    ),
    Penyebab.GANGGUAN_DISTRIBUSI: (
        "Keterlambatan logistik, kerusakan jalur transportasi, hambatan pengiriman "
        "fisik dari sentra produksi ke pasar, termasuk periode transisi antar sentra "
        "panen yang menyebabkan kekosongan stok sementara."
    ),
    Penyebab.PENIMBUNAN_SPEKULASI: (
        "Indikasi penahanan stok oleh pelaku pasar (pedagang besar/distributor) "
        "untuk sengaja menaikkan harga, termasuk sidak gudang atau operasi pasar "
        "oleh pemerintah untuk menindak praktik ini."
    ),
    Penyebab.KENAIKAN_BIAYA_INPUT: (
        "Kenaikan harga pupuk, BBM, tenaga kerja, atau biaya produksi lain di "
        "tingkat petani/produsen yang terbawa ke harga jual akhir."
    ),
    Penyebab.LONJAKAN_PERMINTAAN_MUSIMAN: (
        "Perubahan permintaan (naik ATAU turun) yang dipicu hari besar keagamaan, "
        "liburan, musim tertentu, atau program pemerintah musiman (mis. Makan "
        "Bergizi Gratis) yang mengubah pola konsumsi."
    ),
    Penyebab.KEBIJAKAN_PEMERINTAH: (
        "Kebijakan impor/ekspor, subsidi, program distribusi pemerintah (mis. "
        "Fasilitasi Distribusi Pangan), atau regulasi lain yang secara langsung "
        "memengaruhi harga."
    ),
    Penyebab.FAKTOR_GLOBAL: (
        "Fluktuasi harga komoditas dunia atau nilai tukar rupiah yang memengaruhi "
        "harga — paling relevan untuk komoditas impor seperti minyak goreng, gula, "
        "kedelai."
    ),
}
