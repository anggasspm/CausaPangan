import React, { useMemo, useState, useEffect } from "react";
import {
  MapPin,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  Filter,
  ChevronRight,
  FileText,
  ExternalLink,
  X
} from "lucide-react";

import { MapContainer, TileLayer, Marker, ZoomControl } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Memperbaiki masalah path ikon bawaan Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

/* ------------------------------------------------------------------ */
/* Konfigurasi API                                                    */
/* ------------------------------------------------------------------ */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Data Acuan Lokasi & Kategori                                       */
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
  { kode: "3273", nama: "Kota Bandung", provinsi: "Jawa Barat", lat: -6.9175, lng: 107.6191 },
  { kode: "3209", nama: "Kab. Cirebon", provinsi: "Jawa Barat", lat: -6.7320, lng: 108.5523 },
  { kode: "3206", nama: "Kab. Tasikmalaya", provinsi: "Jawa Barat", lat: -7.3195, lng: 108.2040 },
  { kode: "3275", nama: "Kota Bekasi", provinsi: "Jawa Barat", lat: -6.2383, lng: 106.9756 },
  { kode: "3374", nama: "Kota Semarang", provinsi: "Jawa Tengah", lat: -6.9666, lng: 110.4166 },
  { kode: "3301", nama: "Kab. Cilacap", provinsi: "Jawa Tengah", lat: -7.7300, lng: 109.0160 },
  { kode: "3302", nama: "Kab. Banyumas", provinsi: "Jawa Tengah", lat: -7.5145, lng: 109.2965 },
  { kode: "3372", nama: "Kota Surakarta", provinsi: "Jawa Tengah", lat: -7.5666, lng: 110.8283 },
  { kode: "3310", nama: "Kab. Klaten", provinsi: "Jawa Tengah", lat: -7.7056, lng: 110.6014 },
  { kode: "3578", nama: "Kota Surabaya", provinsi: "Jawa Timur", lat: -7.2504, lng: 112.7688 },
  { kode: "3510", nama: "Kab. Banyuwangi", provinsi: "Jawa Timur", lat: -8.2192, lng: 114.3692 },
  { kode: "3509", nama: "Kab. Jember", provinsi: "Jawa Timur", lat: -8.1725, lng: 113.7000 },
  { kode: "3573", nama: "Kota Malang", provinsi: "Jawa Timur", lat: -7.9797, lng: 112.6304 },
];

/* ------------------------------------------------------------------ */
/* Visual Config - Tampilan Resmi/Formal                              */
/* ------------------------------------------------------------------ */
function colorInfo(p) {
  if (p >= 10) return { bg: "bg-red-600", border: "border-red-600", text: "text-red-700", icon: TrendingUp };
  if (p >= 3) return { bg: "bg-amber-500", border: "border-amber-500", text: "text-amber-700", icon: TrendingUp };
  if (p <= -3) return { bg: "bg-emerald-600", border: "border-emerald-600", text: "text-emerald-700", icon: TrendingDown };
  return { bg: "bg-gray-500", border: "border-gray-500", text: "text-gray-700", icon: Minus };
}

function fmtPersen(p) {
  return `${p > 0 ? "+" : ""}${p.toFixed(1)}%`;
}

// Marker Peta Bulat Dinamis
function createCustomMarker(rec, isSelected) {
  const info = colorInfo(rec.persentase_perubahan);
  const val = fmtPersen(rec.persentase_perubahan).replace("%", "");
  
  const html = `
    <div class="flex items-center justify-center font-bold text-xs text-white shadow-md transition-all duration-200 rounded-full cursor-pointer
      ${info.bg} ${isSelected ? `ring-2 ring-offset-2 ring-gray-800 scale-125 z-50` : 'border-2 border-white hover:scale-110'}" 
      style="width: 44px; height: 44px; font-family: 'Inter', sans-serif;">
      ${val}
    </div>
  `;

  return L.divIcon({
    html: html,
    className: "",
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
}

/* ------------------------------------------------------------------ */
/* Main Component                                                     */
/* ------------------------------------------------------------------ */
export default function PetaHargaPangan() {
  const [komoditas, setKomoditas] = useState(KOMODITAS[1].kode);
  const [selectedKota, setSelectedKota] = useState(null);

  // State API
  const [ringkasan, setRingkasan] = useState([]);
  const [loadingRingkasan, setLoadingRingkasan] = useState(true);
  const [errorRingkasan, setErrorRingkasan] = useState(null);

  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [errorDetail, setErrorDetail] = useState(null);

  // Fetch API (Ringkasan Peta)
  useEffect(() => {
    let cancelled = false;
    setLoadingRingkasan(true);
    setErrorRingkasan(null);

    fetch(`${API_BASE_URL}/api/v1/prediksi/ringkasan`)
      .then((res) => {
        if (!res.ok) throw new Error(`Gagal memuat data peta (${res.status})`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setRingkasan(json);
      })
      .catch((err) => {
        if (!cancelled) setErrorRingkasan(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingRingkasan(false);
      });

    return () => { cancelled = true; };
  }, []);

  // Filter Ringkasan berdasarkan Komoditas
  const dataPeta = useMemo(() => {
    const map = {};
    for (const item of ringkasan) {
      if (item.kode_komoditas === komoditas) {
        map[item.kode_wilayah] = item;
      }
    }
    return map;
  }, [ringkasan, komoditas]);

  // Fetch API (Detail Kota)
  useEffect(() => {
    if (!selectedKota) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    setErrorDetail(null);

    fetch(`${API_BASE_URL}/api/v1/prediksi?kota=${selectedKota}&komoditas=${komoditas}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Gagal memuat detail (${res.status})`);
        return res.json();
      })
      .then((json) => {
        const record = Array.isArray(json) ? json[0] : json;
        if (!cancelled) setDetail(record ?? null);
      })
      .catch((err) => {
        if (!cancelled) setErrorDetail(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });

    return () => { cancelled = true; };
  }, [selectedKota, komoditas]);

  const selected = detail
    ? { ...CITIES.find((c) => c.kode === detail.kode_wilayah), ...detail }
    : null;
    
  const komoditasLabel = KOMODITAS.find((k) => k.kode === komoditas)?.label ?? "";
  const mapCenter = [-7.4, 110.5];

  return (
    <div className="min-h-screen w-full font-sans bg-gray-50 text-gray-900">
      
      {/* HEADER */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Sistem Peringatan Dini Pangan</h1>
            <p className="text-sm text-gray-500 mt-0.5">Pemantauan & Prediksi Harga Komoditas Strategis</p>
          </div>
          <div className="flex items-center gap-2 text-xs font-medium text-gray-600 bg-gray-100 px-3 py-1.5 rounded-md border border-gray-200">
             <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
             Status: Aktif
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        
        {/* TABS KOMODITAS */}
        <div className="mb-6 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <Filter size={16} className="text-gray-400" />
            <span className="text-sm font-semibold text-gray-700">Filter Komoditas</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {KOMODITAS.map((k) => {
              const active = k.kode === komoditas;
              return (
                <button
                  key={k.kode}
                  onClick={() => { setKomoditas(k.kode); setSelectedKota(null); }}
                  className={`px-4 py-2 text-sm font-medium transition-colors rounded-t-md border-b-2 ${
                    active
                      ? "text-blue-700 border-blue-600 bg-blue-50/50"
                      : "text-gray-600 border-transparent hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  {k.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          
          {/* KOLOM KIRI: PETA */}
          <section className="lg:col-span-2 bg-white border-2 border-gray-300 rounded-2xl shadow-sm relative z-0 overflow-hidden">
            <div className="p-3 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
              <h2 className="text-sm font-semibold text-gray-800">Peta Distribusi & Prediksi</h2>
            </div>
            
            {loadingRingkasan && (
              <div className="absolute top-12 left-0 right-0 z-[1000] p-3 text-xs text-center text-blue-700 bg-blue-50/90 border-b border-blue-100 backdrop-blur-sm">
                Mengambil data terbaru dari server...
              </div>
            )}
            
            {errorRingkasan && (
              <div className="absolute top-12 left-0 right-0 z-[1000] p-3 text-xs text-center text-red-700 bg-red-50/90 border-b border-red-100 backdrop-blur-sm">
                Gagal memuat data: {errorRingkasan}
              </div>
            )}
            
            <div style={{ height: "600px", width: "100%" }}>
              <MapContainer 
                center={mapCenter} 
                zoom={7} 
                zoomControl={false}
                style={{ height: "100%", width: "100%", zIndex: 0 }} 
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <ZoomControl position="bottomright" />

                {CITIES.map((c) => {
                  const rec = dataPeta[c.kode];
                  if (!rec) return null; // Sembunyikan marker jika API belum merender kota ini
                  const isSelected = selectedKota === c.kode;
                  return (
                    <Marker 
                      key={c.kode} 
                      position={[c.lat, c.lng]} 
                      icon={createCustomMarker(rec, isSelected)}
                      eventHandlers={{ click: () => setSelectedKota(c.kode) }}
                    />
                  );
                })}
              </MapContainer>
            </div>

            {/* Legenda Bawah Peta */}
            <div className="p-3 border-t border-gray-200 bg-gray-50 flex flex-wrap gap-4 text-xs text-gray-600">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-red-600 rounded-sm" /> Naik ≥10%</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-amber-500 rounded-sm" /> Naik Ringan</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-gray-500 rounded-sm" /> Stabil</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-emerald-600 rounded-sm" /> Turun</span>
            </div>
          </section>

          {/* KOLOM KANAN: PANEL DETAIL */}
          <section className="bg-white border-2 border-gray-300 rounded-2xl shadow-sm flex flex-col h-[600px] overflow-hidden lg:sticky lg:top-6">
            <div className="p-3 border-b border-gray-200 bg-gray-50 flex justify-between items-center shrink-0">
              <h2 className="text-sm font-semibold text-gray-800">Detail Wilayah</h2>
            </div>

            {loadingDetail ? (
              <div className="flex flex-col items-center justify-center text-center p-8 h-full text-gray-500">
                <p className="text-sm font-medium animate-pulse">Menganalisis data wilayah...</p>
              </div>
            ) : errorDetail ? (
              <div className="flex flex-col items-center justify-center text-center p-8 h-full text-red-500">
                <AlertCircle size={32} className="mb-3" />
                <p className="text-sm font-medium">{errorDetail}</p>
              </div>
            ) : !selected ? (
              <div className="flex flex-col items-center justify-center text-center p-8 h-full text-gray-500">
                <MapPin size={32} className="text-gray-300 mb-3" />
                <p className="text-sm">Pilih wilayah pada peta untuk menampilkan analisis.</p>
              </div>
            ) : (
              <div className="flex flex-col h-full overflow-y-auto custom-scrollbar p-5">
                
                {/* Header Kota */}
                <div className="mb-6 flex justify-between items-start">
                  <div>
                    <div className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                      {selected.kode} <ChevronRight size={12} /> {selected.provinsi}
                    </div>
                    <h3 className="text-xl font-bold text-gray-900">{selected.nama}</h3>
                    <p className="text-sm text-gray-600 mt-1">{komoditasLabel}</p>
                  </div>
                  <button onClick={() => setSelectedKota(null)} className="text-gray-400 hover:text-gray-600">
                    <X size={20} />
                  </button>
                </div>

                {/* Harga Panel */}
                <div className="border border-gray-200 rounded-md p-4 mb-6">
                  <p className="text-xs text-gray-500 uppercase font-semibold mb-2">Prediksi Perubahan</p>
                  <div className="flex justify-between items-end">
                    <div className={`flex items-center gap-2 ${colorInfo(selected.persentase_perubahan).text}`}>
                      {React.createElement(colorInfo(selected.persentase_perubahan).icon, { size: 24 })}
                      <span className="text-2xl font-bold">{fmtPersen(selected.persentase_perubahan)}</span>
                    </div>
                    <div className="text-right">
                      {selected.tier_data === "solid" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-50 text-green-700 text-xs font-medium border border-green-200 rounded">
                          <CheckCircle size={12} /> Data Solid
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200 rounded">
                          <AlertCircle size={12} /> Estimasi
                        </span>
                      )}
                      <div className="text-[11px] text-gray-500 mt-1">Conf: {Math.round(selected.confidence * 100)}%</div>
                    </div>
                  </div>
                </div>

                {/* Penyebab & Rekomendasi */}
                <div className="space-y-6">
                  <div>
                    <h4 className="text-xs text-gray-500 uppercase font-semibold mb-2 border-b border-gray-100 pb-1">Faktor Penyebab</h4>
                    {selected.penyebab ? (
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{PENYEBAB_LABEL[selected.penyebab]}</p>
                        <p className="text-sm text-gray-600 mt-1 leading-relaxed">{selected.penyebab_detail}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">Tidak terdeteksi anomali pada periode berjalan.</p>
                    )}
                  </div>

                  <div>
                    <h4 className="text-xs text-gray-500 uppercase font-semibold mb-2 border-b border-gray-100 pb-1">Tindakan Disarankan</h4>
                    {selected.rekomendasi ? (
                      <div className={`p-3 rounded border-l-4 bg-gray-50 ${selected.rekomendasi.urgensi === 'tinggi' ? 'border-red-500' : 'border-amber-500'}`}>
                        <div className="flex gap-2 mb-1">
                           <span className="text-[10px] font-semibold text-gray-600 uppercase bg-gray-200 px-1.5 py-0.5 rounded">
                             Untuk: {selected.rekomendasi.target}
                           </span>
                        </div>
                        <p className="text-sm text-gray-800 leading-relaxed">{selected.rekomendasi.aksi}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">Data belum mencukupi untuk rekomendasi aksi.</p>
                    )}
                  </div>

                  {/* Sumber Berita */}
                  {selected.sumber_berita && selected.sumber_berita.length > 0 && (
                    <div>
                      <h4 className="text-xs text-gray-500 uppercase font-semibold mb-2 border-b border-gray-100 pb-1">Referensi Berita</h4>
                      <div className="space-y-3">
                        {selected.sumber_berita.map((s, i) => (
                          <div key={i} className="flex gap-2 group">
                            <FileText size={14} className="text-gray-400 mt-0.5 shrink-0" />
                            <div>
                              <a href={s.url || "#"} className="text-sm text-blue-600 group-hover:underline line-clamp-2 leading-snug">
                                {s.judul} <ExternalLink size={10} className="inline opacity-0 group-hover:opacity-100" />
                              </a>
                              <p className="text-[11px] text-gray-500 mt-0.5">{s.sumber_media} • {new Date(s.tanggal_terbit).toLocaleDateString("id-ID")}</p>
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