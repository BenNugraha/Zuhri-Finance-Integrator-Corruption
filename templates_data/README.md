# Panduan Isi Folder `templates_data/`

## Template yang WAJIB diisi dengan data riil Anda (untuk kalibrasi ARS/FII)

| File | Isi | Dipakai untuk |
|---|---|---|
| `entitas_template.csv` | Daftar entitas yang dianalisis | Identitas & metadata entitas |
| `insiden_template.csv` | Insiden/kasus per entitas, dengan bukti & sumber terverifikasi | Dasar pelabelan |
| `fakta_fitur_template.csv` | Fitur A/R/B/M + label per entitas per periode | Input langsung ke `firth_logistic_regression` & `optimize_fii_weights` (lewat `tools/build_training_table.py`) |
| `labeling_rule.md` | Aturan eksplisit kapan label=1 vs label=0 | Dokumentasi metodologi, WAJIB diisi sebelum kalibrasi |

Ganti isi contoh (baris `ENT001`, `ENT002`, dst) dengan data riil Anda.
Jangan hapus header kolomnya -- `tools/build_training_table.py` membaca
berdasarkan nama kolom.

## Data konteks (BUKAN untuk kalibrasi langsung)

| File | Isi | Kenapa bukan untuk kalibrasi |
|---|---|---|
| `kpk_national_trend_2004_2025.csv` | Jumlah kasus KPK per tahun, agregat nasional | Level nasional/tahunan, bukan per-entitas -- tidak bisa jadi `y_true` untuk `firth_logistic_regression`/`optimize_fii_weights` |
| `cpi_context_2025.csv` | Skor Corruption Perceptions Index per negara | Berbasis persepsi/survei ahli (bukan pengukuran langsung), dan level negara bukan entitas |

Kedua file ini disajikan lewat endpoint `/context/national-trend` dan
`/context/cpi` sebagai info latar/dashboard saja -- **tidak** dibaca
otomatis oleh `/pipeline/run`.

## Contoh domain lain (bukan untuk financial integrity)

| File | Isi | Catatan |
|---|---|---|
| `nsv_negative_indicators_example_k3.csv` | Nilai Ambang Batas (NAB) K3: kebisingan, radiasi UV, medan magnet (Permenaker RI) | Ini domain **keselamatan kerja**, bukan indikator sosial-ekonomi untuk NSV finansial (yang aslinya dicontohkan dengan Gini ratio, emisi CO2, pengangguran). Fungsi `compute_nsv` di `fii_nsv.py` memang generik dan bisa menerima array indikator apa pun -- tapi kalau tujuan Anda memang deteksi risiko K3 (bukan korupsi keuangan), pakai file ini sebagai contoh format `negative_indicators`/`negative_thresholds`. Kalau tujuan Anda financial integrity, cari indikator yang relevan ke domain itu dan dokumentasikan sumbernya seperti format file ini.
