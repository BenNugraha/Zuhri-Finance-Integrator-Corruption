# Aturan Pelabelan (Labeling Rule) untuk ARS/FII

Aturan ini WAJIB didefinisikan eksplisit dan didokumentasikan sebelum
kalibrasi, supaya audit trail bisa menjelaskan *kenapa* suatu entitas
diberi label 1 atau 0 -- bukan angka tanpa dasar.

## Definisi label

- **`label = 1`** jika entitas punya minimal satu insiden pada
  `insiden_template.csv` dalam window observasi yang:
  - berstatus **terverifikasi** (mis. putusan pengadilan berkekuatan
    hukum tetap / inkracht, atau temuan resmi BPK/KPK/ACLC dengan
    tindak lanjut), DAN
  - jenis insidennya termasuk kategori yang relevan untuk model Anda
    (mis. `mark_up_pengadaan`, `fraud_aset`, `suap`) -- definisikan
    daftar kategori ini secara eksplisit, jangan biarkan implisit.
- **`label = 0`** jika tidak ada insiden yang memenuhi kriteria di atas
  dalam window observasi yang sama.

## Window waktu

Tentukan salah satu: bulanan / kuartalan / tahunan. Window harus SAMA
untuk semua entitas supaya perbandingan adil (bukan entitas A diukur
per-bulan sementara entitas B per-tahun).

## Yang HARUS didokumentasikan per baris insiden

- Sumber (`sumber`): nama lembaga/dokumen resmi.
- Bukti (`bukti`): nomor putusan, link laporan, atau referensi yang
  bisa diverifikasi ulang oleh pihak ketiga.
- Status verifikasi: apakah sudah inkracht/final, atau masih dugaan.
  **Jangan** memberi label=1 untuk insiden yang masih tahap dugaan/
  penyelidikan awal tanpa putusan/temuan final -- ini akan mencemari
  kalibrasi dengan false positive.

## Peringatan

Kalau jumlah label=1 sangat sedikit dibanding label=0 (rare event,
umum terjadi pada data insiden korupsi), `firth_logistic_regression`
di `ars_scoring.py` memang didesain untuk kasus ini -- tapi tetap
butuh jumlah observasi yang cukup (idealnya puluhan kejadian label=1
minimal) supaya estimasi bobot tidak terlalu tidak stabil.
