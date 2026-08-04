# ZFIC — Zuhri Financial Integrity Core

Toolkit analitis untuk deteksi anomali harga (bubble detection), skoring
risiko entitas (ARS), agregasi indikator sosial-ekonomi (NSV), indeks
gabungan (FII), dan audit log yang tidak bisa diubah diam-diam
(hash-chained). Disediakan sebagai REST API (Flask) yang bisa dijalankan
lewat Docker tanpa perlu install Python sama sekali.

## ⚠️ Baca dulu sebelum pakai — batasan jujur

Software ini adalah **alat bantu analitis**, bukan mesin "deteksi
korupsi otomatis yang pasti benar". Beberapa hal yang perlu Anda tahu:

1. **Tidak mengeksekusi apa pun secara nyata.** Endpoint `/pipeline/run`
   hanya menghasilkan *rekomendasi* terstruktur (mis. `flag_for_review`,
   `notify_regulator_24h`). Software ini **tidak** membekukan aset,
   tidak mengirim notifikasi ke regulator, dan tidak terhubung ke sistem
   finansial riil manapun — itu semua di luar cakupan kode ini dan
   sengaja tidak diasumsikan ada otorisasi untuk itu.
2. **Hasilnya sekuat data yang Anda masukkan.** Skoring ARS dan FII
   butuh data historis berlabel insiden (siapa terbukti terlibat
   fraud/korupsi, kapan, sumbernya apa) untuk dikalibrasi. Tanpa itu,
   angka yang keluar hanya angka — bukan bukti. Lihat bagian
   [Data yang Wajib Anda Sediakan Sendiri](#data-yang-wajib-anda-sediakan-sendiri).
3. **Presisi 61 digit pada `/precision/constants` tidak membuat hasil
   analisis lebih akurat.** Itu hanya konstanta matematika standar (π,
   golden ratio) yang dihitung ulang untuk keperluan referensi. Akurasi
   hasil ditentukan oleh kualitas data input, bukan oleh presisi
   konstanta.
4. **Jangan jadikan output software ini sebagai satu-satunya dasar
   tuduhan terhadap orang/entitas.** Gunakan sebagai alat bantu
   penyaringan awal (screening) yang hasilnya tetap perlu diverifikasi
   manusia sebelum ada tindakan apa pun.

---

## Struktur Project

```
zfic/
├── backend/                      # package inti (Python)
│   ├── precision_core.py      # konstanta matematis (referensi)
│   ├── bubble_detection.py    # deteksi anomali harga
│   ├── ars_scoring.py         # Agentic Risk Score (Firth logistic regression)
│   ├── fii_nsv.py             # Financial Integrity Index & Net Societal Value
│   ├── audit_alert.py         # audit log hash-chained + klasifikasi severity
│   ├── pipeline_orchestrator.py  # menyambungkan semua modul untuk 1 entitas
│   └── app.py                 # REST API (Flask)
|	|__ regulator_integration.py
|	|__ asset_freeze_gateway.py
|	|__ dashboard_koruptor.py
├── examples/
│   └── demo_synthetic.py      # demo end-to-end dengan data SINTETIS
├── templates_data/            # template CSV kosong + panduan isi data riil
│   ├── entitas_template.csv
│   ├── insiden_template.csv
│   ├── fakta_fitur_template.csv
│   ├── labeling_rule.md
│   ├── kpk_national_trend_2004_2025.csv   # data KONTEKS (bukan kalibrasi)
│   ├── cpi_context_2025.csv               # data KONTEKS (bukan kalibrasi)
│   ├── nsv_negative_indicators_example_k3.csv  # contoh domain K3
│   └── README.md              # penjelasan tiap file di folder ini
|
|___templates
|	|__ dashboard_koruptor.html
|
├── tools/
│   └── build_training_table.py  # gabungkan data Anda -> siap kalibrasi
├── tests/
│   └── test_core.py
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md                  # file ini
```

---

## Cara Tercepat: Jalankan dengan Docker (disarankan untuk pemula)

Anda hanya butuh [Docker](https://www.docker.com/products/docker-desktop/)
terinstal — tidak perlu install Python atau library apa pun secara manual.

```bash
# Dari dalam folder zfic/
docker compose up --build
```

Tunggu sampai muncul log `Listening at: http://0.0.0.0:8080`. API sudah
jalan di `http://localhost:8080`.

Cek dengan:
```bash
curl http://localhost:8080/health
# {"service": "zfic-v3", "status": "ok"}
```

Audit log tersimpan di Docker volume `zfic_audit_data`, jadi tetap ada
walau container di-restart.

Untuk menghentikan: `Ctrl+C`, lalu `docker compose down` (data audit log
tetap tersimpan; tambahkan `-v` kalau memang mau menghapusnya).

---

## Cara Alternatif: Jalankan Tanpa Docker (Python langsung)

Butuh Python 3.10+.

```bash
cd zfic
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
pip install gunicorn             # untuk menjalankan server produksi
```

Jalankan server:
```bash
python -m zfic.app
# atau untuk produksi:
gunicorn --bind 0.0.0.0:8080 zfic.app:app
```

---

## Langkah 1: Coba Dulu dengan Data Sintetis (Tanpa Data Riil)

Sebelum masukkan data riil, jalankan demo untuk memastikan semuanya
berfungsi:

```bash
python examples/demo_synthetic.py
```

Ini akan mencetak hasil tiap tahap pipeline (bubble detection → ARS →
NSV → FII) memakai data acak yang dibuat program itu sendiri — bukan
data sungguhan. Tujuannya murni memverifikasi kode berjalan tanpa error
matematis.

---

## Langkah 2: Endpoint API

| Method | Path | Fungsi |
|---|---|---|
| GET | `/health` | Cek server hidup |
| GET | `/precision/constants` | Lihat konstanta π/φ 61 digit (referensi) |
| GET | `/context/national-trend` | Data KONTEKS: tren kasus KPK per tahun (agregat nasional) |
| GET | `/context/cpi` | Data KONTEKS: skor CPI per negara |
| POST | `/pipeline/run` | Jalankan pipeline lengkap untuk 1 entitas |
| GET | `/audit/verify` | Verifikasi audit log belum dimanipulasi |

Contoh `/pipeline/run` pakai data sintetis (ganti dengan data riil Anda
setelah membaca Langkah 3):

```bash
curl -X POST http://localhost:8080/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "ENT001",
    "prices": [100, 101, 99, 102, ... minimal 252 angka harga historis],
    "B_P": [0.1, -0.2, ... sama panjang dengan prices],
    "B_Q": [0.05, 0.1, ... sama panjang dengan prices],
    "ars_features": {"A": 7.5, "R": 3.0, "B": 6.0, "M": 4.0},
    "ars_weights": [-3.4, 0.16, 0.03, 0.21, 0.04],
    "fii_weights": {"w1": 0.4, "w2": 0.4, "w3": 0.2},
    "fii_threshold": 0.35,
    "nsv": {
      "indicators": [68.0, 0.71],
      "indicator_bounds": [[0, 100], [0, 1]],
      "negative_indicators": [0.39, 7.2],
      "negative_thresholds": [0.35, 6.0],
      "lam": 0.5
    }
  }'
```

**Catatan penting:** `prices`, `B_P`, `B_Q` butuh **minimal ~252 titik
data** (kira-kira 1 tahun data harian) karena perhitungan volatilitas
baseline (`vol_baseline_window`) defaultnya 252 hari. Kalau datanya
lebih pendek, hasil `anomali` akan kosong (NaN) dan pipeline gagal.

Alih-alih `ars_weights` + `fii_weights` langsung, Anda juga bisa kirim
`incident_history` dan `fraud_calibration_data` supaya server
menghitung bobotnya sendiri dari data historis Anda (lihat Langkah 3).

---

## Langkah 3: Isi Data Riil (Kalibrasi ARS/FII)

Skoring ARS dan FII **tidak bisa dikalibrasi tanpa data historis
berlabel insiden per-entitas**. Ini bukan kekurangan software — memang
begitu sifat metodenya (mirip semua model klasifikasi: butuh contoh
"ini insiden" dan "ini bukan insiden" untuk belajar polanya).

### 3.1. Isi tiga template ini di `templates_data/`

1. **`entitas_template.csv`** — daftar entitas yang Anda analisis.
2. **`insiden_template.csv`** — insiden per entitas, **wajib** ada
   kolom sumber & bukti yang bisa diverifikasi (nomor putusan
   pengadilan, link laporan resmi, dsb).
3. **`fakta_fitur_template.csv`** — fitur A/R/B/M (skala 0–10) + label
   (1 = ada insiden terverifikasi, 0 = tidak) per entitas per periode.

Baca **`templates_data/labeling_rule.md`** dulu untuk menentukan aturan
label yang eksplisit — jangan asal isi 1/0.

### 3.2. Ubah jadi tabel siap-kalibrasi

```bash
python tools/build_training_table.py \
  --fakta-fitur templates_data/fakta_fitur_template.csv \
  --insiden templates_data/insiden_template.csv \
  --out-json build/training_table.json
```

Script ini akan memperingatkan Anda kalau datanya terlalu sedikit (< 20
observasi) atau tidak ada satu pun label=1 — perhatikan peringatan itu,
jangan diabaikan.

### 3.3. Pakai hasilnya di `/pipeline/run`

Isi `build/training_table.json` ke field `incident_history` pada body
request (ganti bagian `ars_weights` di contoh Langkah 2 dengan ini):

```json
"incident_history": {
  "A": [...], "R": [...], "B": [...], "M": [...],
  "incident_label": [...]
}
```

Server akan menjalankan `firth_logistic_regression` otomatis dan
memakai hasilnya.

Untuk `fii_weights`, pola yang sama berlaku lewat field
`fraud_calibration_data` (lihat docstring `optimize_fii_weights` di
`zfic/fii_nsv.py` untuk struktur field yang dibutuhkan).

---

## Data Konteks: KPK & CPI

Folder `templates_data/` sudah berisi dua dataset yang Anda kumpulkan:
- `kpk_national_trend_2004_2025.csv` — jumlah kasus KPK per tahun.
- `cpi_context_2025.csv` — skor Corruption Perceptions Index per negara.

Keduanya ditampilkan lewat `/context/national-trend` dan `/context/cpi`
sebagai **info latar/dashboard saja**. Keduanya **tidak** dipakai
otomatis untuk kalibrasi ARS/FII karena levelnya nasional/negara, bukan
per-entitas — detail alasannya ada di `templates_data/README.md`.

---

## Audit Log

Setiap hasil `/pipeline/run` otomatis dicatat ke audit log berformat
JSONL dengan **hash-chaining** (setiap entri menyimpan hash entri
sebelumnya). Kalau ada entri yang diubah setelah ditulis, rantai hash
akan terputus dan terdeteksi lewat:

```bash
curl http://localhost:8080/audit/verify
```

Path file log diatur lewat environment variable `ZFIC_AUDIT_LOG_PATH`
(default `/data/audit.jsonl` di dalam container Docker, yang otomatis
disimpan ke volume `zfic_audit_data`).

---

## Testing

```bash
pip install -e .[dev]
pytest tests/ -v
```

---

## Data yang Wajib Anda Sediakan Sendiri

Ringkasan dari semua bagian di atas — jangan mulai dengan berharap
software ini "otomatis tahu" siapa yang korupsi:

| Kebutuhan | Kenapa wajib Anda sediakan | Contoh sumber |
|---|---|---|
| Harga historis entitas (≥252 titik) | Input `compute_regret`/`compute_anomali` | Data pasar/bursa resmi |
| Data insiden berlabel per-entitas | Kalibrasi ARS (Firth regression) & FII (F1-optimization) | Putusan pengadilan, LHP BPK, KPK/ACLC (lihat `templates_data/README.md`) |
| Ambang batas indikator NSV yang relevan ke domain Anda | `compute_nsv` butuh `negative_thresholds` yang terdokumentasi sumbernya | Regulasi resmi sesuai domain (bukan asal comot angka) |
| (Opsional) Data harga opsi | `bubble_Q_put_call_parity`, `risk_neutral_density_breeden_litzenberger` | Bursa derivatif (mis. NSE, CBOE) |

Tanpa data-data ini, yang bisa Anda jalankan hanyalah demo dengan data
sintetis (`examples/demo_synthetic.py`) — yang memang tujuannya cuma
membuktikan kode jalan, bukan memberi hasil yang bisa dipakai untuk
keputusan sungguhan.
