"""
Query layer. Semua fungsi di sini mengembalikan dict/list dict mentah dari
database — konversi ke Pydantic model + penegakan aturan null (§4)
dilakukan di main.py, bukan di sini, supaya layer ini murni soal SQL.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def list_wilayah(db: Session):
    rows = db.execute(text("""
        SELECT kode_wilayah, nama_kota, kode_provinsi, nama_provinsi
        FROM wilayah
        ORDER BY kode_wilayah
    """)).mappings().all()
    return [dict(r) for r in rows]


def list_prediksi(db: Session, kode_wilayah: str, kode_komoditas: str | None = None):
    """
    Dipakai endpoint GET /api/v1/prediksi?kota=&komoditas=
    Kalau tabel `prediksi` masih kosong (belum diisi Role 2), ini
    otomatis mengembalikan list kosong -- bukan error -- karena ini
    query SELECT biasa.
    """
    def iso(dt):
        """Convert datetime object (dari kolom TIMESTAMPTZ) ke string ISO 8601
        format 'YYYY-MM-DDTHH:mm:ssZ' sesuai API_CONTRACT §1 -- SQLAlchemy
        balikin objek datetime, bukan string, jadi wajib dikonversi manual
        sebelum masuk Pydantic model yang expect str."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    query = """
        SELECT p.kode_wilayah, w.nama_kota, w.kode_provinsi, w.nama_provinsi,
               p.kode_komoditas, p.nama_komoditas, p.harga_terakhir, p.satuan,
               p.persentase_perubahan, p.arah, p.confidence, p.tier_data,
               p.penyebab, p.penyebab_detail,
               p.rekomendasi_target, p.rekomendasi_aksi, p.rekomendasi_urgensi,
               p.terakhir_diperbarui
        FROM prediksi p
        JOIN wilayah w ON w.kode_wilayah = p.kode_wilayah
        WHERE p.kode_wilayah = :kode_wilayah
    """
    params = {"kode_wilayah": kode_wilayah}
    if kode_komoditas:
        query += " AND p.kode_komoditas = :kode_komoditas"
        params["kode_komoditas"] = kode_komoditas

    rows = db.execute(text(query), params).mappings().all()
    result = []
    for r in rows:
        row = dict(r)
        row["terakhir_diperbarui"] = iso(row["terakhir_diperbarui"])
        # susun ulang jadi bentuk nested sesuai API_CONTRACT §3.1
        row["rekomendasi"] = None
        if row["rekomendasi_target"]:
            row["rekomendasi"] = {
                "target": row.pop("rekomendasi_target"),
                "aksi": row.pop("rekomendasi_aksi"),
                "urgensi": row.pop("rekomendasi_urgensi"),
            }
        else:
            row.pop("rekomendasi_target", None)
            row.pop("rekomendasi_aksi", None)
            row.pop("rekomendasi_urgensi", None)

        sumber = db.execute(text("""
            SELECT judul, url, sumber_media, tanggal_terbit
            FROM sumber_berita
            WHERE kode_wilayah = :kw AND kode_komoditas = :kk
            ORDER BY tanggal_terbit DESC
        """), {"kw": row["kode_wilayah"], "kk": row["kode_komoditas"]}).mappings().all()
        row["sumber_berita"] = [
            {**dict(s), "tanggal_terbit": iso(s["tanggal_terbit"])} for s in sumber
        ]
        result.append(row)
    return result


def list_ringkasan(db: Session):
    """Dipakai GET /api/v1/prediksi/ringkasan -- payload ringan buat peta."""
    rows = db.execute(text("""
        SELECT kode_wilayah, kode_komoditas, persentase_perubahan, arah, confidence, tier_data
        FROM prediksi
        ORDER BY kode_wilayah, kode_komoditas
    """)).mappings().all()
    return [dict(r) for r in rows]