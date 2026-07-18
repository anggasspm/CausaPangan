"""
Prompt engineering untuk event classifier.

Few-shot examples di bawah dirangkum ulang (bukan kutipan langsung) dari
sample dataset Role 1 (`Sample Dataset Kategori Event Berita`), dipersingkat
supaya prompt tetap ringkas. Kalau nanti tim mau menambah/mengganti contoh,
edit `FEW_SHOT_EXAMPLES` di bawah — jangan tempel isi artikel penuh, cukup
inti sinyalnya saja.
"""

from __future__ import annotations

from .enums import Penyebab, PENYEBAB_DESKRIPSI

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "teks": (
            "Curah hujan tinggi di sentra produksi cabai menyebabkan "
            "pembusukan dini tanaman, volume dan kualitas panen turun tajam."
        ),
        "penyebab": Penyebab.CUACA_GAGAL_PANEN.value,
        "penyebab_detail": "Curah hujan tinggi menyebabkan gagal panen cabai di sentra produksi.",
    },
    {
        "teks": (
            "Transisi sentra panen dari Jawa Timur ke Jawa Tengah dan Jawa "
            "Barat menyebabkan kekosongan stok sementara di pasar."
        ),
        "penyebab": Penyebab.GANGGUAN_DISTRIBUSI.value,
        "penyebab_detail": "Transisi antar sentra panen menyebabkan kekosongan stok sementara.",
    },
    {
        "teks": (
            "Kementerian Perdagangan menggencarkan sidak gudang untuk "
            "menindak praktik penahanan stok yang memicu kelangkaan artifisial."
        ),
        "penyebab": Penyebab.PENIMBUNAN_SPEKULASI.value,
        "penyebab_detail": "Ada indikasi penahanan stok yang direspons dengan sidak gudang pemerintah.",
    },
    {
        "teks": (
            "Kenaikan harga pupuk dan biaya transportasi membuat biaya "
            "produksi petani cabai naik, terbawa ke harga jual di pasar."
        ),
        "penyebab": Penyebab.KENAIKAN_BIAYA_INPUT.value,
        "penyebab_detail": "Kenaikan biaya pupuk dan transportasi menaikkan biaya produksi.",
    },
    {
        "teks": (
            "Permintaan cabai naik tajam menjelang Idulfitri karena "
            "konsumsi masyarakat meningkat dibanding pasokan yang tersedia."
        ),
        "penyebab": Penyebab.LONJAKAN_PERMINTAAN_MUSIMAN.value,
        "penyebab_detail": "Permintaan naik menjelang Idulfitri melebihi pasokan yang tersedia.",
    },
    {
        "teks": (
            "Pemerintah menjalankan program distribusi pangan dari daerah "
            "surplus ke daerah defisit untuk stabilisasi harga jelang Ramadan."
        ),
        "penyebab": Penyebab.KEBIJAKAN_PEMERINTAH.value,
        "penyebab_detail": "Program distribusi pemerintah antar daerah untuk stabilisasi harga.",
    },
    {
        "teks": (
            "Fluktuasi harga CPO dunia dan pelemahan nilai tukar rupiah "
            "ikut mendorong naiknya harga minyak goreng kemasan di dalam negeri."
        ),
        "penyebab": Penyebab.FAKTOR_GLOBAL.value,
        "penyebab_detail": "Fluktuasi harga CPO dunia dan nilai tukar rupiah menekan harga minyak goreng.",
    },
    {
        "teks": (
            "Seorang perempuan diamankan polisi karena diduga mencuri "
            "minyak goreng dan sembako di sebuah minimarket."
        ),
        "penyebab": None,
        "penyebab_detail": None,
        "catatan": "Berita kriminal, TIDAK ada sinyal penyebab pergerakan harga -> null.",
    },
    {
        "teks": (
            "Pemkab menggelar seremoni panen padi organik dan mendorong "
            "petani memperluas lahan pertanian berkelanjutan."
        ),
        "penyebab": None,
        "penyebab_detail": None,
        "catatan": "Berita seremonial/program jangka panjang, tidak menjelaskan penyebab pergerakan harga saat ini -> null.",
    },
]


def build_system_prompt() -> str:
    kategori_list = "\n".join(
        f'- `{p.value}`: {PENYEBAB_DESKRIPSI[p]}' for p in Penyebab
    )
    contoh_list = []
    for ex in FEW_SHOT_EXAMPLES:
        contoh_list.append(
            f'Teks: "{ex["teks"]}"\n'
            f'Output: {{"penyebab": {json_val(ex["penyebab"])}, '
            f'"penyebab_detail": {json_val(ex["penyebab_detail"])}, '
            f'"llm_certainty": {"0.9" if ex["penyebab"] else "0.95"}}}'
        )
    contoh_text = "\n\n".join(contoh_list)

    return f"""Kamu adalah classifier yang menentukan PENYEBAB pergerakan harga pangan
di Indonesia berdasarkan teks berita, untuk sistem peringatan dini harga pangan.

Kategori yang tersedia (WAJIB pilih salah satu dari 7 ini, atau null):
{kategori_list}

ATURAN PENTING:
1. Kembalikan `penyebab: null` jika teks TIDAK secara jelas & eksplisit
   menunjukkan salah satu dari 7 kategori di atas. JANGAN memaksakan
   artikel ke kategori yang paling "mirip" kalau sinyalnya lemah/tidak
   langsung — berita murni statistik harga, berita seremonial, berita
   kriminal, atau laporan capaian program tanpa kaitan jelas ke penyebab
   harga, semuanya harus null.
2. Jika `penyebab` null, maka `penyebab_detail` WAJIB null juga.
3. `penyebab_detail` singkat (maksimal 1 kalimat), berbasis konteks
   langsung dari teks, bukan template generik.
4. `llm_certainty` mencerminkan seberapa eksplisit sinyalnya di teks
   (bukan seberapa yakin kamu soal fakta di baliknya).
5. Output HARUS berupa JSON valid sesuai schema, tanpa teks tambahan
   apapun di luar JSON.
6. Asumsikan teks yang diberikan SUDAH relevan secara waktu (kamu tidak
   perlu menilai kapan berita ini terbit) — fokus HANYA pada isi teksnya.

Contoh:

{contoh_text}
"""


def json_val(v: str | None) -> str:
    return "null" if v is None else f'"{v}"'


def build_user_prompt(
    judul: str,
    isi_teks: str,
    komoditas_hint: list[str] | None = None,
    isi_teks_status: str | None = None,
) -> str:
    hint_line = ""
    if komoditas_hint:
        hint_line = f"\nKomoditas yang terdeteksi terkait artikel ini: {', '.join(komoditas_hint)}"

    status_note = ""
    if isi_teks_status == "fallback":
        status_note = (
            "\n[CATATAN: isi teks di bawah adalah hasil fallback scraper "
            "(kemungkinan snippet/ringkasan, bukan artikel penuh) — kalau "
            "sinyalnya tidak jelas karena teks terpotong, lebih baik kembalikan "
            "null daripada menebak.]"
        )
    elif isi_teks_status == "gagal_pakai_summary_rss":
        status_note = (
            "\n[CATATAN: ekstraksi isi artikel GAGAL TOTAL — teks di bawah "
            "cuma cuplikan RSS 1-2 kalimat, bukan isi artikel lengkap. Kalau "
            "cuplikan ini tidak cukup untuk menentukan penyebab secara "
            "eksplisit, WAJIB kembalikan null.]"
        )

    return f"""Judul: {judul}{hint_line}{status_note}

Teks:
{isi_teks}

Klasifikasikan penyebab pergerakan harga dari teks di atas sesuai instruksi."""
