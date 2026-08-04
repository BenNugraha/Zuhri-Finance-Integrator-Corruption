# 🌊 ZFIC — Zuhri Financial Integrity Core

**ZFIC** adalah toolkit analitis untuk deteksi anomali harga, skoring risiko entitas (ARS), agregasi indikator sosial-ekonomi (NSV), indeks integritas gabungan (FII), dan audit log tamper-evident. Dibangun dengan presisi 61 digit sebagai jangkar deterministik.

> "Memberantas korupsi melalui analisis berbasis bukti, bukan opini."

---

## 📸 Tampilan Aplikasi

![ZFIC Dashboard](docs/ZFIC-screen-page.png)

*Dashboard utama ZFIC dengan tema Ocean Depths — menampilkan status sistem, konstanta fundamental, analisis entitas, audit log, dan data konteks.*

---

## 🚀 Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Bubble Detection** | Deteksi gelembung harga berbasis dekomposisi P-Q dan regret-covariance drift. |
| **Agentic Risk Score (ARS)** | Skor risiko entitas dengan Firth logistic regression (rare-event bias correction). |
| **Net Societal Value (NSV)** | Agregasi indikator sosial-ekonomi dengan normalisasi min-max dan penalti dampak negatif. |
| **Financial Integrity Index (FII)** | Indeks gabungan dari anomali, ARS, dan NSV — dioptimasi dengan grid search + stratified K-fold untuk maksimalkan F1-score. |
| **Audit Log** | Append‑only, hash-chained, tamper-evident — bukti digital tahan manipulasi. |
| **REST API** | Endpoint untuk pipeline, konteks, dan verifikasi audit. |
| **Dashboard Interaktif** | Tema Ocean Depths, dengan tombol analisis sintetis dan data KPK/CPI. |

---

## 🛠️ Teknologi

- **Python 3.10+** dengan Flask, NumPy, Pandas, Scikit-learn
- **Presisi 61 digit** menggunakan `mpmath` untuk konstanta π_eff dan Φ
- **Docker** & **Docker Compose** untuk containerisasi
- **Pytest** untuk unit test

---

## 📁 Struktur Proyek
