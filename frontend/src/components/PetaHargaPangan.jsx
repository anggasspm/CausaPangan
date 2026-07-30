import React, { useMemo, useState, useEffect } from "react";
import {
  MapPin,
  TrendingUp,
  TrendingDown,
  Minus,
  Newspaper,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Package,
  ChevronRight,
  Lightbulb,
  ArrowUpRight,
  X
} from "lucide-react";

import { MapContainer, TileLayer, Marker, ZoomControl, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

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

// Data lokasi telah dikonversi dari x, y menjadi koordinat asli (lat, lng)
const CITIES = [
  { kode: "3273", nama: "Kota Bandung", provinsi: "Jawa Barat", lat: -6.9175, lng: 107.6191 },
  { kode: "3209", nama: "Kab. Cirebon", provinsi: "Jawa Barat", lat: -6.7320, lng: 108.5523 },
  { kode: "3206", nama: "Kab. Tasikmalaya", provinsi: "Jawa Barat", lat: -7.3195, lng: 108.2040 },
  { kode: "3275", nama: "Kota Bekasi", provinsi: "Jawa Barat", lat: -6.2383, lng: 106.9756 },
  { kode: "3374", nama: "Kota Semarang", provinsi: "Jawa Tengah", lat: -6.9666, lng: 110.4166 },
  { kode: "3301", nama: "Kab. Cilacap", provinsi: "Jawa Tengah", lat: -7.7300, lng: 109.0160 },
  { kode: "3302", nama: "Kab. Banyumas", provinsi: "Jawa Tengah", lat: -7.5145, lng: 109.2965 },
  { kode: "3372", nama: "Kota Surakarta (Solo)", provinsi: "Jawa Tengah", lat: -7.5666, lng: 110.8283 },
  { kode: "3310", nama: "Kab. Klaten", provinsi: "Jawa Tengah", lat: -7.7056, lng: 110.6014 },
  { kode: "3578", nama: "Kota Surabaya", provinsi: "Jawa Timur", lat: -7.2504, lng: 112.7688 },
  { kode: "3510", nama: "Kab. Banyuwangi", provinsi: "Jawa Timur", lat: -8.2192, lng: 114.3692 },
  { kode: "3509", nama: "Kab. Jember", provinsi: "Jawa Timur", lat: -8.1725, lng: 113.7000 },
  { kode: "3573", nama: "Kota Malang", provinsi: "Jawa Timur", lat: -7.9797, lng: 112.6304 },
];

const KURASI = {
  "3301|cabai_rawit_merah": {
    persentase_perubahan: 15.4, arah: "naik", confidence: 0.82, tier_data: "solid",
    penyebab: "cuaca_gagal_panen", penyebab_detail: "Curah hujan tinggi di sentra produksi menyebabkan gagal panen parsial pada tanaman cabai.",
    rekomendasi: { target: "distributor", aksi: "Cari alternatif pasokan dari sentra produksi di luar wilayah terdampak sebelum harga naik lebih lanjut.", urgensi: "tinggi" },
    sumber_berita: [{ judul: "Hujan penyebab utama gagal panen cabai di sentra produksi", tanggal_terbit: "2026-07-10" }],
  },
  "3573|bawang_merah": {
    persentase_perubahan: -6.2, arah: "turun", confidence: 0.35, tier_data: "estimasi",
    penyebab: "lonjakan_permintaan_musiman", penyebab_detail: "Indikasi awal penurunan permintaan pasca periode konsumsi tinggi, namun sinyal masih lemah.",
    rekomendasi: null,
    sumber_berita: [{ judul: "Harga bawang merah mulai melandai di sejumlah pasar", tanggal_terbit: "2026-07-08" }],
  },
  "3209|beras": {
    persentase_perubahan: 0.6, arah: "stabil", confidence: 0.7, tier_data: "solid",
    penyebab: null, penyebab_detail: null, rekomendasi: null, sumber_berita: [],
  }
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
    persentase_perubahan: persen, arah, confidence, tier_data: tier, penyebab,
    penyebab_detail: penyebab ? "Sinyal dari pemberitaan mengindikasikan kategori penyebab ini sebagai faktor dominan pada periode berjalan." : null,
    rekomendasi: rekomendasiAda ? {
      target: rnd() > 0.5 ? "distributor" : "pedagang",
      aksi: rnd() > 0.5 ? "Pantau perkembangan pasokan pada pekan berjalan dan siapkan alternatif sumber bila tren berlanjut." : "Sesuaikan stok secara bertahap mengikuti tren harga pada pekan berjalan.",
      urgensi: Math.abs(persen) > 10 ? "tinggi" : "sedang",
    } : null,
    sumber_berita: adaSinyal ? [{ judul: "Pemberitaan terkait pergerakan harga di wilayah ini", tanggal_terbit: "2026-07-0" + (1 + Math.floor(rnd() * 9)) }] : [],
  };
}

function colorInfo(p) {
  if (p >= 10) return { bg: "bg-red-600", text: "text-red-600", ring: "ring-red-200", light: "bg-red-50", icon: TrendingUp };
  if (p >= 3) return { bg: "bg-orange-500", text: "text-orange-600", ring: "ring-orange-200", light: "bg-orange-50", icon: TrendingUp };
  if (p <= -3) return { bg: "bg-emerald-600", text: "text-emerald-600", ring: "ring-emerald-200", light: "bg-emerald-50", icon: TrendingDown };
  return { bg: "bg-slate-500", text: "text-slate-600", ring: "ring-slate-200", light: "bg-slate-100", icon: Minus };
}

function fmtPersen(p) {
  return `${p > 0 ? "+" : ""}${p.toFixed(1)}%`;
}

// Komponen pembuat custom HTML icon untuk Leaflet
function createCustomMarker(rec, isSelected) {
  const info = colorInfo(rec.persentase_perubahan);
  const val = fmtPersen(rec.persentase_perubahan).replace("%", "");
  
  // Karena Leaflet merender diluar React DOM Tree standar, kita sisipkan string HTML yang akan distyling oleh Tailwind
  const html = `
    <div class="flex items-center justify-center font-bold text-xs rounded-full text-white shadow-lg transition-transform duration-200 
      ${info.bg} ${isSelected ? `ring-4 ${info.ring} scale-125 z-50` : 'hover:scale-110 ring-2 ring-white'}" 
      style="width: 44px; height: 44px; font-family: 'Inter', sans-serif;">
      ${val}
    </div>
  `;

  return L.divIcon({
    html: html,
    className: "", // Kosongkan agar Leaflet tidak memberi latar transparan defaultnya
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
}

/* ------------------------------------------------------------------ */
/* Komponen Utama                                                     */
/* ------------------------------------------------------------------ */

export default function PetaHargaPangan() {
  const [komoditas, setKomoditas] = useState(KOMODITAS[1].kode);
  const [selectedKota, setSelectedKota] = useState(null);
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/batas_wilayah.geojson")
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch((err) => console.error("Gagal memuat GeoJSON batas wilayah:", err));
  }, []);

  const data = useMemo(() => {
    const map = {};
    for (const c of CITIES) map[c.kode] = generateRecord(c.kode, komoditas);
    return map;
  }, [komoditas]);

  const selected = selectedKota ? { ...CITIES.find((c) => c.kode === selectedKota), ...data[selectedKota] } : null;
  const komoditasLabel = KOMODITAS.find((k) => k.kode === komoditas)?.label ?? "";

  // Koordinat pusat peta (Tengah-tengah Pulau Jawa)
  const mapCenter = [-7.4, 110.5];

  return (
    <div className="min-h-screen w-full font-sans bg-slate-50 text-slate-900">
      {/* HEADER MODERN */}
      <header className="bg-gradient-to-r from-slate-900 to-indigo-950 shadow-lg text-white">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <Activity size={28} className="text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Sistem Peringatan Dini Pangan</h1>
              <p className="text-sm text-slate-300 mt-1 flex items-center gap-1">
                <MapPin size={14} /> Wilayah Pantauan: Jawa Barat, Jawa Tengah, Jawa Timur
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm backdrop-blur-sm">
             <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
             Model AI Aktif
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* FILTER KOMODITAS */}
        <div className="mb-6">
          <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Package size={16} /> Pilih Komoditas
          </p>
          <div className="flex flex-wrap gap-3">
            {KOMODITAS.map((k) => {
              const active = k.kode === komoditas;
              return (
                <button
                  key={k.kode}
                  onClick={() => { setKomoditas(k.kode); setSelectedKota(null); }}
                  className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border ${
                    active
                      ? "bg-indigo-600 text-white border-indigo-600 shadow-md transform scale-105"
                      : "bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:bg-indigo-50 shadow-sm"
                  }`}
                >
                  {k.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-6">
          {/* PETA ASLI LEAFLET */}
          <section className="bg-white rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden flex flex-col h-[600px] lg:h-auto min-h-[600px] z-0">
            {/* Header Judul Peta - Z-index tinggi agar di atas peta */}
            <div className="absolute top-0 left-0 right-0 z-[400] p-4 border-b border-slate-100 bg-white/90 backdrop-blur-md">
              <h2 className="text-sm font-semibold text-slate-700">Peta Prediksi Perubahan Harga (Live)</h2>
            </div>
            
            {/* WRAPPER KETAT UNTUK PETA (Memberikan ruang untuk header) */}
            <div className="w-full h-full relative pt-[53px]">
              <MapContainer 
                center={mapCenter} 
                zoom={7} 
                zoomControl={false}
                // Hapus style di sini karena sudah ditangani oleh .leaflet-container di CSS
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                
                <ZoomControl position="bottomright" />

                {geoData && (
                  <GeoJSON 
                    data={geoData} 
                    style={{
                      color: "#6366f1",
                      weight: 2,
                      opacity: 0.4,
                      fillColor: "#e0e7ff",
                      fillOpacity: 0.1,
                      dashArray: "6, 6"
                    }} 
                  />
                )}

                {/* Render Markers */}
                {CITIES.map((c) => {
                  const rec = data[c.kode];
                  const isSelected = selectedKota === c.kode;
                  return (
                    <Marker 
                      key={c.kode} 
                      position={[c.lat, c.lng]} 
                      icon={createCustomMarker(rec, isSelected)}
                      eventHandlers={{
                        click: () => setSelectedKota(c.kode)
                      }}
                    />
                  );
                })}
              </MapContainer>
            </div>

            {/* Legenda Mengapung - Z-index tinggi agar di atas peta */}
            <div className="absolute bottom-4 left-4 z-[400] bg-white/90 backdrop-blur-md rounded-xl border border-slate-200 shadow-sm p-3 flex flex-col md:flex-row flex-wrap gap-4 text-xs font-medium text-slate-600">
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-600" /> Naik Tinggi (≥10%)</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-orange-500" /> Naik Ringan</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-slate-500" /> Stabil</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-600" /> Turun</span>
            </div>
          </section>

          {/* PANEL DETAIL (UX Baru) */}
          <section className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col lg:sticky lg:top-6 h-[500px] lg:h-[700px] overflow-hidden">
            {!selected ? (
              <div className="flex flex-col items-center justify-center text-center p-12 h-full">
                <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                  <MapPin size={32} className="text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-700">Pilih Titik Lokasi</h3>
                <p className="text-slate-500 text-sm mt-2 max-w-[250px]">
                  Klik salah satu titik kota pada peta untuk melihat prediksi dan rekomendasi aksi AI.
                </p>
              </div>
            ) : (
              <div className="flex flex-col h-full divide-y divide-slate-100 overflow-y-auto custom-scrollbar">
                
                {/* Header Kartu */}
                <div className="p-6 pb-5 shrink-0">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 mb-1.5 uppercase tracking-wide">
                        {selected.provinsi} <ChevronRight size={14} />
                      </div>
                      <h2 className="text-2xl font-bold text-slate-900">{selected.nama}</h2>
                      <p className="text-slate-500 font-medium mt-1">{komoditasLabel}</p>
                    </div>
                    <button onClick={() => setSelectedKota(null)} className="p-2 bg-slate-100 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
                      <X size={18} />
                    </button>
                  </div>

                  {/* Highlight Harga */}
                  <div className={`p-4 rounded-xl flex items-center justify-between ${colorInfo(selected.persentase_perubahan).light} border border-white`}>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase">Prediksi Perubahan</p>
                      <div className={`flex items-center gap-2 mt-1 ${colorInfo(selected.persentase_perubahan).text}`}>
                        {React.createElement(colorInfo(selected.persentase_perubahan).icon, { size: 28, strokeWidth: 2.5 })}
                        <span className="text-3xl font-black">{fmtPersen(selected.persentase_perubahan)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      {selected.tier_data === "solid" ? (
                        <div className="flex flex-col items-end">
                          <span className="flex items-center gap-1 px-2.5 py-1 bg-indigo-100 text-indigo-700 text-[11px] font-bold rounded-md">
                            <CheckCircle2 size={12} /> DATA SOLID
                          </span>
                          <span className="text-xs text-slate-500 mt-1 font-medium">Conf: {Math.round(selected.confidence * 100)}%</span>
                        </div>
                      ) : (
                        <div className="flex flex-col items-end">
                          <span className="flex items-center gap-1 px-2.5 py-1 bg-amber-100 text-amber-700 text-[11px] font-bold rounded-md border border-amber-200">
                            <AlertTriangle size={12} /> ESTIMASI
                          </span>
                          <span className="text-xs text-slate-500 mt-1 font-medium">Conf: {Math.round(selected.confidence * 100)}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Konten Scrollable Bawah */}
                <div className="p-6 flex flex-col gap-6 bg-slate-50/50 flex-1">
                  
                  {/* Penyebab */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <Activity size={14} /> Analisis Penyebab
                    </h4>
                    {selected.penyebab ? (
                      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                        <p className="font-semibold text-slate-800">{PENYEBAB_LABEL[selected.penyebab]}</p>
                        <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{selected.penyebab_detail}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 italic bg-slate-100 p-3 rounded-lg">Prediksi murni dari tren historis. Belum ada sinyal pemberitaan signifikan.</p>
                    )}
                  </div>

                  {/* Rekomendasi */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <Lightbulb size={14} /> Rekomendasi Aksi
                    </h4>
                    {selected.rekomendasi ? (
                      <div className={`p-4 rounded-xl border-l-4 shadow-sm bg-white ${selected.rekomendasi.urgensi === 'tinggi' ? 'border-red-500' : 'border-orange-400'}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${selected.rekomendasi.urgensi === 'tinggi' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                            Urgensi {selected.rekomendasi.urgensi}
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase bg-indigo-100 text-indigo-700">
                            Untuk {selected.rekomendasi.target}
                          </span>
                        </div>
                        <p className="text-sm text-slate-700 font-medium leading-relaxed">{selected.rekomendasi.aksi}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 italic bg-slate-100 p-3 rounded-lg">Belum cukup data untuk menyusun rekomendasi aksi.</p>
                    )}
                  </div>

                  {/* Sumber Berita */}
                  {selected.sumber_berita.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Newspaper size={14} /> Referensi Berita
                      </h4>
                      <div className="flex flex-col gap-2 pb-4">
                        {selected.sumber_berita.map((s, i) => (
                          <div key={i} className="flex items-start gap-2 bg-white p-3 rounded-lg border border-slate-100 hover:border-slate-300 transition-colors">
                            <ArrowUpRight size={14} className="mt-0.5 shrink-0 text-indigo-400" />
                            <div>
                              <p className="text-sm text-slate-700 font-medium line-clamp-2 leading-tight">{s.judul}</p>
                              <p className="text-[11px] text-slate-400 mt-1">{s.tanggal_terbit}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}