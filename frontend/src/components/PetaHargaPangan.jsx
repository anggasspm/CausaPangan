import React, { useMemo, useState } from "react";
import {
  MapPin,
  TrendingUp,
  TrendingDown,
  Minus,
  Newspaper,
  Info,
  ArrowUpRight,
  X,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Data acuan — sesuai API_CONTRACT.md (kota x komoditas x tanggal)     */
/* Data di bawah adalah data tiruan untuk keperluan purwarupa tampilan. */
/* ------------------------------------------------------------------ */

const KOMODITAS = [
  { kode: "beras", label: "Beras" },
  { kode: "cabai_rawit_merah", label: "Cabai Rawit Merah" },
  { kode: "cabai_merah_keriting", label: "Cabai Merah Keriting" },
  { kode: "bawang_merah", label: "Bawang Merah" },
  { kode: "minyak_goreng", label: "Minyak Goreng" },
];

const PENYEBAB_LABEL = {
  cuaca_gagal_panen: "Cuaca Ekstrem / Gagal Panen",
  gangguan_distribusi: "Gangguan Distribusi",
  penimbunan_spekulasi: "Penimbunan / Spekulasi Pasar",
  kenaikan_biaya_input: "Kenaikan Biaya Input Produksi",
  lonjakan_permintaan_musiman: "Lonjakan Permintaan Musiman",
  kebijakan_pemerintah: "Perubahan Kebijakan",
  faktor_global: "Faktor Harga Global",
};

const CITIES = [
  { kode: "3273", nama: "Kota Bandung", provinsi: "Jawa Barat", x: 17, y: 56 },
  { kode: "3209", nama: "Kab. Cirebon", provinsi: "Jawa Barat", x: 30, y: 34 },
  { kode: "3206", nama: "Kab. Tasikmalaya", provinsi: "Jawa Barat", x: 22, y: 68 },
  { kode: "3275", nama: "Kota Bekasi", provinsi: "Jawa Barat", x: 9, y: 28 },
  { kode: "3374", nama: "Kota Semarang", provinsi: "Jawa Tengah", x: 46, y: 24 },
  { kode: "3301", nama: "Kab. Cilacap", provinsi: "Jawa Tengah", x: 37, y: 71 },
  { kode: "3302", nama: "Kab. Banyumas", provinsi: "Jawa Tengah", x: 33, y: 62 },
  { kode: "3372", nama: "Kota Surakarta (Solo)", provinsi: "Jawa Tengah", x: 52, y: 55 },
  { kode: "3310", nama: "Kab. Klaten", provinsi: "Jawa Tengah", x: 49, y: 49 },
  { kode: "3578", nama: "Kota Surabaya", provinsi: "Jawa Timur", x: 78, y: 29 },
  { kode: "3510", nama: "Kab. Banyuwangi", provinsi: "Jawa Timur", x: 96, y: 61 },
  { kode: "3509", nama: "Kab. Jember", provinsi: "Jawa Timur", x: 86, y: 63 },
  { kode: "3573", nama: "Kota Malang", provinsi: "Jawa Timur", x: 74, y: 55 },
];

// Beberapa kombinasi kota x komoditas dikurasi manual untuk menunjukkan
// variasi kondisi nyata; sisanya dibangkitkan deterministik agar tampilan
// tetap konsisten setiap kali dimuat ulang.
const KURASI = {
  "3301|cabai_rawit_merah": {
    persentase_perubahan: 15.4, arah: "naik", confidence: 0.82, tier_data: "solid",
    penyebab: "cuaca_gagal_panen",
    penyebab_detail: "Curah hujan tinggi di sentra produksi menyebabkan gagal panen parsial pada tanaman cabai.",
    rekomendasi: { target: "distributor", aksi: "Cari alternatif pasokan dari sentra produksi di luar wilayah terdampak sebelum harga naik lebih lanjut.", urgensi: "tinggi" },
    sumber_berita: [{ judul: "Hujan penyebab utama gagal panen cabai di sentra produksi", tanggal_terbit: "2026-07-10" }],
  },
  "3573|bawang_merah": {
    persentase_perubahan: -6.2, arah: "turun", confidence: 0.35, tier_data: "estimasi",
    penyebab: "lonjakan_permintaan_musiman",
    penyebab_detail: "Indikasi awal penurunan permintaan pasca periode konsumsi tinggi, namun sinyal masih lemah.",
    rekomendasi: null,
    sumber_berita: [{ judul: "Harga bawang merah mulai melandai di sejumlah pasar", tanggal_terbit: "2026-07-08" }],
  },
  "3509|cabai_merah_keriting": {
    persentase_perubahan: 12.1, arah: "naik", confidence: 0.74, tier_data: "solid",
    penyebab: "gangguan_distribusi",
    penyebab_detail: "Masa transisi sentra panen antar wilayah menyebabkan celah pasokan sementara ke pasar besar.",
    rekomendasi: { target: "distributor", aksi: "Percepat re-routing pasokan dari wilayah yang sedang panen untuk menutup celah distribusi.", urgensi: "tinggi" },
    sumber_berita: [{ judul: "Transisi sentra panen pengaruhi pasokan cabai antar wilayah", tanggal_terbit: "2026-07-06" }],
  },
  "3310|minyak_goreng": {
    persentase_perubahan: 4.8, arah: "naik", confidence: 0.6, tier_data: "solid",
    penyebab: "faktor_global",
    penyebab_detail: "Fluktuasi harga CPO dunia turut memengaruhi harga minyak goreng kemasan curah.",
    rekomendasi: { target: "pedagang", aksi: "Pertimbangkan diversifikasi pemasok untuk menjaga margin di tengah fluktuasi harga bahan baku impor.", urgensi: "sedang" },
    sumber_berita: [{ judul: "Harga CPO dunia bergerak naik, minyak goreng ikut terdampak", tanggal_terbit: "2026-07-05" }],
  },
  "3209|beras": {
    persentase_perubahan: 0.6, arah: "stabil", confidence: 0.7, tier_data: "solid",
    penyebab: null, penyebab_detail: null, rekomendasi: null,
    sumber_berita: [],
  },
  "3275|cabai_rawit_merah": {
    persentase_perubahan: 8.3, arah: "naik", confidence: 0.55, tier_data: "solid",
    penyebab: "lonjakan_permintaan_musiman",
    penyebab_detail: "Permintaan meningkat menjelang periode hari besar, sementara pasokan relatif tetap.",
    rekomendasi: { target: "pedagang", aksi: "Tambah stok bertahap menjelang periode permintaan tinggi untuk hindari kehabisan pasokan.", urgensi: "sedang" },
    sumber_berita: [{ judul: "Permintaan cabai meningkat jelang hari besar", tanggal_terbit: "2026-07-09" }],
  },
  "3372|beras": {
    persentase_perubahan: 3.2, arah: "naik", confidence: 0.71, tier_data: "solid",
    penyebab: "kebijakan_pemerintah",
    penyebab_detail: "Penyesuaian skema distribusi beras SPHP berdampak pada harga eceran sementara.",
    rekomendasi: { target: "distributor", aksi: "Koordinasikan jadwal penyaluran dengan program SPHP setempat untuk stabilkan harga.", urgensi: "sedang" },
    sumber_berita: [{ judul: "Penyesuaian skema SPHP pengaruhi harga beras eceran", tanggal_terbit: "2026-07-07" }],
  },
  "3302|cabai_rawit_merah": {
    persentase_perubahan: 17.9, arah: "naik", confidence: 0.88, tier_data: "solid",
    penyebab: "cuaca_gagal_panen",
    penyebab_detail: "Tingkat kegagalan panen akibat hujan dan angin dilaporkan tinggi di wilayah ini pada periode berjalan.",
    rekomendasi: { target: "distributor", aksi: "Prioritaskan alokasi pasokan cadangan ke wilayah ini mengingat tingkat dampak yang tinggi.", urgensi: "tinggi" },
    sumber_berita: [
      { judul: "Petani laporkan kegagalan panen signifikan akibat cuaca", tanggal_terbit: "2026-07-11" },
      { judul: "Harga cabai di sejumlah pasar tradisional melonjak", tanggal_terbit: "2026-07-12" },
    ],
  },
};

function seededRandom(seed) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  return function () {
    h = Math.imul(h ^ (h >>> 15), h | 1);
    h ^= h + Math.imul(h ^ (h >>> 7), h | 61);
    return ((h ^ (h >>> 14)) >>> 0) / 4294967296;
  };
}

const PENYEBAB_KEYS = Object.keys(PENYEBAB_LABEL);

function generateRecord(kodeWilayah, kodeKomoditas) {
  const key = `${kodeWilayah}|${kodeKomoditas}`;
  if (KURASI[key]) return KURASI[key];

  const rnd = seededRandom(key);
  const roll = rnd();
  const persen = Math.round((rnd() * 22 - 8) * 10) / 10;
  const arah = persen > 2 ? "naik" : persen < -2 ? "turun" : "stabil";
  const confidence = Math.round((0.4 + rnd() * 0.55) * 100) / 100;
  const tier = confidence >= 0.55 ? "solid" : "estimasi";
  const adaSinyal = roll > 0.3;
  const penyebab = adaSinyal ? PENYEBAB_KEYS[Math.floor(rnd() * PENYEBAB_KEYS.length)] : null;
  const rekomendasiAda = penyebab && confidence >= 0.5;

  return {
    persentase_perubahan: persen,
    arah,
    confidence,
    tier_data: tier,
    penyebab,
    penyebab_detail: penyebab
      ? "Sinyal dari pemberitaan mengindikasikan kategori penyebab ini sebagai faktor dominan pada periode berjalan."
      : null,
    rekomendasi: rekomendasiAda
      ? {
          target: rnd() > 0.5 ? "distributor" : "pedagang",
          aksi: rnd() > 0.5
            ? "Pantau perkembangan pasokan pada pekan berjalan dan siapkan alternatif sumber bila tren berlanjut."
            : "Sesuaikan stok secara bertahap mengikuti tren harga pada pekan berjalan.",
          urgensi: Math.abs(persen) > 10 ? "tinggi" : "sedang",
        }
      : null,
    sumber_berita: adaSinyal
      ? [{ judul: "Pemberitaan terkait pergerakan harga di wilayah ini", tanggal_terbit: "2026-07-0" + (1 + Math.floor(rnd() * 9)) }]
      : [],
  };
}

/* ------------------------------------------------------------------ */
/* Util tampilan                                                       */
/* ------------------------------------------------------------------ */

function colorForPersen(p) {
  if (p >= 10) return { fill: "#B84B28", ring: "rgba(184,75,40,0.28)" };      // naik tinggi — rust
  if (p >= 3) return { fill: "#C99A3A", ring: "rgba(201,154,58,0.28)" };      // naik ringan — amber
  if (p <= -3) return { fill: "#4B6B4F", ring: "rgba(75,107,79,0.28)" };      // turun — moss
  return { fill: "#8C7F63", ring: "rgba(140,127,99,0.28)" };                  // stabil — rope
}

function fmtPersen(p) {
  const s = p > 0 ? "+" : "";
  return `${s}${p.toFixed(1)}%`;
}

const ARROW = { naik: TrendingUp, turun: TrendingDown, stabil: Minus };

/* ------------------------------------------------------------------ */
/* Komponen utama                                                       */
/* ------------------------------------------------------------------ */

export default function PetaHargaPangan() {
  const [komoditas, setKomoditas] = useState(KOMODITAS[1].kode);
  const [selectedKota, setSelectedKota] = useState(null);

  const data = useMemo(() => {
    const map = {};
    for (const c of CITIES) map[c.kode] = generateRecord(c.kode, komoditas);
    return map;
  }, [komoditas]);

  const selected = selectedKota
    ? { ...CITIES.find((c) => c.kode === selectedKota), ...data[selectedKota] }
    : null;

  const komoditasLabel = KOMODITAS.find((k) => k.kode === komoditas)?.label ?? "";

  return (
    <div className="min-h-screen w-full font-body" style={{ background: "#EFE7D3", color: "#241B12" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@500;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        .font-display { font-family: 'Roboto Slab', serif; }
        .font-body { font-family: 'Inter', sans-serif; }
        .font-mono { font-family: 'IBM Plex Mono', monospace; }
        .paper-texture {
          background-image: radial-gradient(circle at 1px 1px, rgba(36,27,18,0.06) 1px, transparent 0);
          background-size: 18px 18px;
        }
        .stamp-marker { transition: transform 160ms ease, box-shadow 160ms ease; }
        .stamp-marker:hover, .stamp-marker:focus-visible { transform: scale(1.14); }
        .card-perforated {
          border-top: 2px dashed #A9977A;
        }
        @media (prefers-reduced-motion: reduce) {
          .stamp-marker { transition: none; }
        }
      `}</style>

      {/* Header */}
      <header className="border-b" style={{ borderColor: "#C9BE9E", background: "#1E3140" }}>
        <div className="max-w-6xl mx-auto px-5 py-5 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <MapPin size={20} color="#E8DEC1" strokeWidth={2.2} />
            <h1 className="font-display text-xl md:text-2xl tracking-tight" style={{ color: "#F3ECDA" }}>
              Pos Pantau Pangan
            </h1>
          </div>
          <p className="text-sm md:text-[15px]" style={{ color: "#C7BFA4" }}>
            Prediksi dini &amp; rekomendasi aksi harga pangan — Jawa Barat, Jawa Tengah, Jawa Timur
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6 md:py-8">
        {/* Filter komoditas */}
        <div className="mb-5">
          <p className="text-xs uppercase tracking-wider mb-2 font-mono" style={{ color: "#7A6E52" }}>
            Pilih komoditas
          </p>
          <div className="flex flex-wrap gap-2">
            {KOMODITAS.map((k) => {
              const active = k.kode === komoditas;
              return (
                <button
                  key={k.kode}
                  onClick={() => { setKomoditas(k.kode); setSelectedKota(null); }}
                  className="px-3.5 py-1.5 rounded-full text-sm font-medium border transition-colors"
                  style={
                    active
                      ? { background: "#1E3140", color: "#F3ECDA", borderColor: "#1E3140" }
                      : { background: "transparent", color: "#3A2F1E", borderColor: "#B9AD8B" }
                  }
                >
                  {k.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-5">
          {/* Peta */}
          <section
            className="rounded-lg border relative overflow-hidden paper-texture"
            style={{ borderColor: "#C9BE9E", background: "#F4EEDD", minHeight: "480px" }}
          >
            {/* Pita provinsi */}
            <div className="absolute inset-0 flex text-center pointer-events-none">
              {[
                ["JAWA BARAT", "rgba(30,49,64,0.05)"],
                ["JAWA TENGAH", "rgba(30,49,64,0.09)"],
                ["JAWA TIMUR", "rgba(30,49,64,0.05)"],
              ].map(([label, bg], i) => (
                <div key={label} className="flex-1 h-full relative" style={{ background: bg }}>
                  <span
                    className="absolute top-3 left-1/2 -translate-x-1/2 text-[11px] font-mono tracking-widest"
                    style={{ color: "#8C7F63" }}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </div>

            {/* Markers */}
            <div className="absolute inset-0">
              {CITIES.map((c) => {
                const rec = data[c.kode];
                const color = colorForPersen(rec.persentase_perubahan);
                const isSelected = selectedKota === c.kode;
                return (
                  <button
                    key={c.kode}
                    onClick={() => setSelectedKota(c.kode)}
                    className="stamp-marker absolute rounded-full flex items-center justify-center font-mono text-[11px] font-medium focus:outline-none"
                    style={{
                      left: `${c.x}%`,
                      top: `${c.y}%`,
                      transform: "translate(-50%, -50%)",
                      width: 46,
                      height: 46,
                      background: color.fill,
                      color: "#FBF6E9",
                      boxShadow: isSelected
                        ? `0 0 0 5px ${color.ring}, 0 0 0 2px #241B12`
                        : `0 0 0 5px ${color.ring}`,
                    }}
                    aria-label={`${c.nama}: ${fmtPersen(rec.persentase_perubahan)}`}
                    title={c.nama}
                  >
                    {fmtPersen(rec.persentase_perubahan).replace("%", "")}
                  </button>
                );
              })}
            </div>

            {/* Legenda */}
            <div
              className="absolute bottom-3 left-3 right-3 md:right-auto rounded-md border px-3 py-2 flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] font-mono"
              style={{ background: "rgba(244,238,221,0.92)", borderColor: "#C9BE9E", color: "#3A2F1E" }}
            >
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: "#B84B28" }} /> Naik tinggi (≥10%)</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: "#C99A3A" }} /> Naik ringan</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: "#8C7F63" }} /> Stabil</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: "#4B6B4F" }} /> Turun</span>
            </div>
          </section>

          {/* Panel detail */}
          <section
            className="rounded-lg border p-5 h-fit lg:sticky lg:top-6"
            style={{ borderColor: "#C9BE9E", background: "#FBF6E9" }}
          >
            {!selected ? (
              <div className="flex flex-col items-center text-center gap-2 py-10">
                <Info size={22} color="#9A8C6B" />
                <p className="text-sm" style={{ color: "#7A6E52" }}>
                  Pilih satu titik pada peta untuk melihat detail prediksi {komoditasLabel.toLowerCase()}.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-mono" style={{ color: "#9A8C6B" }}>{selected.kode} · {selected.provinsi}</p>
                    <h2 className="font-display text-lg leading-snug">{selected.nama}</h2>
                    <p className="text-sm" style={{ color: "#7A6E52" }}>{komoditasLabel}</p>
                  </div>
                  <button
                    onClick={() => setSelectedKota(null)}
                    className="p-1 rounded-full hover:bg-black/5 focus:outline-none"
                    aria-label="Tutup detail"
                  >
                    <X size={16} color="#7A6E52" />
                  </button>
                </div>

                {/* Angka utama */}
                <div className="flex items-end gap-2">
                  {(() => {
                    const Arrow = ARROW[selected.arah];
                    const color = colorForPersen(selected.persentase_perubahan).fill;
                    return <Arrow size={26} color={color} strokeWidth={2.4} />;
                  })()}
                  <span className="font-mono text-3xl font-medium" style={{ color: colorForPersen(selected.persentase_perubahan).fill }}>
                    {fmtPersen(selected.persentase_perubahan)}
                  </span>
                </div>

                {/* Badge confidence */}
                <div>
                  {selected.tier_data === "solid" ? (
                    <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-full" style={{ background: "#1E3140", color: "#F3ECDA" }}>
                      DATA SOLID · confidence {Math.round(selected.confidence * 100)}%
                    </span>
                  ) : (
                    <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-full border border-dashed" style={{ borderColor: "#C99A3A", color: "#8C6E1F" }}>
                      ESTIMASI · confidence {Math.round(selected.confidence * 100)}%
                    </span>
                  )}
                </div>

                <div className="card-perforated pt-4 flex flex-col gap-3">
                  {/* Penyebab */}
                  <div>
                    <p className="text-[11px] uppercase tracking-wider font-mono mb-1" style={{ color: "#9A8C6B" }}>Penyebab</p>
                    {selected.penyebab ? (
                      <>
                        <p className="text-sm font-medium">{PENYEBAB_LABEL[selected.penyebab]}</p>
                        <p className="text-sm mt-0.5" style={{ color: "#5B5140" }}>{selected.penyebab_detail}</p>
                      </>
                    ) : (
                      <p className="text-sm" style={{ color: "#9A8C6B" }}>Belum ada sinyal pemberitaan signifikan pada periode berjalan; prediksi murni dari tren historis.</p>
                    )}
                  </div>

                  {/* Rekomendasi */}
                  <div>
                    <p className="text-[11px] uppercase tracking-wider font-mono mb-1" style={{ color: "#9A8C6B" }}>Rekomendasi Aksi</p>
                    {selected.rekomendasi ? (
                      <div className="rounded-md p-3" style={{ background: "#EFE7D3" }}>
                        <span
                          className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-full mb-1.5"
                          style={{ background: selected.rekomendasi.urgensi === "tinggi" ? "#B84B28" : "#C99A3A", color: "#FBF6E9" }}
                        >
                          Untuk {selected.rekomendasi.target} · urgensi {selected.rekomendasi.urgensi}
                        </span>
                        <p className="text-sm">{selected.rekomendasi.aksi}</p>
                      </div>
                    ) : (
                      <p className="text-sm" style={{ color: "#9A8C6B" }}>
                        Belum cukup data untuk memberikan rekomendasi yang dapat diandalkan pada titik ini.
                      </p>
                    )}
                  </div>

                  {/* Sumber berita */}
                  {selected.sumber_berita.length > 0 && (
                    <div>
                      <p className="text-[11px] uppercase tracking-wider font-mono mb-1.5" style={{ color: "#9A8C6B" }}>Sumber Pemberitaan</p>
                      <ul className="flex flex-col gap-1.5">
                        {selected.sumber_berita.map((s, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-sm">
                            <Newspaper size={14} className="mt-0.5 shrink-0" color="#7A6E52" />
                            <span style={{ color: "#3A2F1E" }}>{s.judul}
                              <span className="font-mono text-xs ml-1.5" style={{ color: "#9A8C6B" }}>· {s.tanggal_terbit}</span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>

        <p className="text-xs mt-5 flex items-center gap-1.5" style={{ color: "#9A8C6B" }}>
          <ArrowUpRight size={13} />
          Peta skematik, tidak menggambarkan skala geografis sesungguhnya · Cakupan MVP: 3 provinsi, 13 kota/kabupaten, 5 komoditas prioritas
        </p>
      </main>
    </div>
  );
}
