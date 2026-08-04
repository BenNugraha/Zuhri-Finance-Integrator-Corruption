"""
ZFIC - Tool: Bangun Tabel Training dari Skema entitas/insiden/fakta_fitur
============================================================================
Menjembatani skema data (entitas.csv + insiden.csv + fakta_fitur.csv,
lihat templates_data/) menjadi X (fitur A/R/B/M) dan y_true (label) yang
siap dilempar langsung ke:

  - zfic.ars_scoring.firth_logistic_regression(X, y_true)
  - zfic.fii_nsv.optimize_fii_weights(anomali_norm, ars_norm,
                                       nsv_deficit_norm, y_true)

Cara pakai (dari root project):

    python tools/build_training_table.py \
        --fakta-fitur templates_data/fakta_fitur_template.csv \
        --out-json build/training_table.json

File fakta_fitur.csv HARUS punya kolom: entity_id, periode, A, R, B, M, label
(lihat templates_data/labeling_rule.md untuk cara menentukan label).

Kalau Anda belum punya fakta_fitur.csv siap pakai dan baru punya
entitas.csv + insiden.csv terpisah, gunakan --entitas dan --insiden
supaya script ini menghitung jumlah_insiden per entitas-periode untuk
Anda (agregasi sederhana -- Anda tetap perlu menentukan sendiri
kolom A/R/B/M dan aturan label, karena itu keputusan domain, bukan
sesuatu yang bisa diturunkan otomatis dari jumlah insiden saja).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict


def load_fakta_fitur(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required_cols = {"entity_id", "periode", "A", "R", "B", "M", "label"}
    if rows and not required_cols.issubset(rows[0].keys()):
        missing = required_cols - set(rows[0].keys())
        raise ValueError(f"Kolom wajib hilang di fakta_fitur.csv: {sorted(missing)}")
    return rows


def build_xy(rows: list) -> dict:
    A, R, B, M, y = [], [], [], [], []
    entity_ids = []
    for row in rows:
        try:
            A.append(float(row["A"]))
            R.append(float(row["R"]))
            B.append(float(row["B"]))
            M.append(float(row["M"]))
            y.append(int(row["label"]))
            entity_ids.append(row["entity_id"])
        except (ValueError, KeyError) as e:
            print(f"[SKIP] Baris tidak valid, dilewati: {row} ({e})", file=sys.stderr)
    return {
        "entity_id": entity_ids,
        "A": A, "R": R, "B": B, "M": M,
        "incident_label": y,
    }


def summarize_insiden_per_entitas(insiden_path: str) -> dict:
    """
    Agregasi jumlah insiden per entity_id dari insiden.csv -- HANYA
    sebagai bantuan eksplorasi data, bukan pengganti kolom A/R/B/M/label
    di fakta_fitur.csv (yang harus Anda tentukan sendiri berdasarkan
    aturan pelabelan di labeling_rule.md).
    """
    counts = defaultdict(int)
    with open(insiden_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("label", "").strip() == "1":
                counts[row["entity_id"]] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fakta-fitur", required=True,
                         help="Path ke fakta_fitur.csv (kolom: entity_id,periode,A,R,B,M,label)")
    parser.add_argument("--insiden", default=None,
                         help="Opsional: path ke insiden.csv, untuk cetak ringkasan jumlah insiden per entitas")
    parser.add_argument("--out-json", required=True,
                         help="Path output JSON siap pakai untuk ars_weights/fraud_calibration_data")
    args = parser.parse_args()

    rows = load_fakta_fitur(args.fakta_fitur)
    if not rows:
        print("Peringatan: fakta_fitur.csv kosong (hanya header atau tidak ada baris).",
              file=sys.stderr)

    xy = build_xy(rows)

    n = len(xy["incident_label"])
    n_pos = sum(xy["incident_label"])
    print(f"Total observasi: {n}, label=1: {n_pos}, label=0: {n - n_pos}")
    if n_pos == 0:
        print("PERINGATAN: tidak ada observasi berlabel 1 (insiden). "
              "firth_logistic_regression tetap bisa dijalankan secara "
              "matematis, tapi hasilnya tidak bermakna tanpa contoh "
              "positif -- model tidak punya apa pun untuk dipelajari "
              "sebagai pola insiden.", file=sys.stderr)
    if n < 20:
        print(f"PERINGATAN: hanya {n} observasi. Estimasi Firth regression "
              "dan optimisasi bobot FII akan sangat tidak stabil pada "
              "sampel sekecil ini -- anggap hasilnya eksploratif, "
              "bukan final.", file=sys.stderr)

    import os
    os.makedirs(os.path.dirname(args.out_json) or ".", exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(xy, f, indent=2, ensure_ascii=False)
    print(f"Tabel training ditulis ke: {args.out_json}")
    print("Struktur JSON ini bisa langsung dipakai sebagai nilai field "
          "'incident_history' pada body POST /pipeline/run.")

    if args.insiden:
        print("\nRingkasan jumlah insiden berlabel per entitas (dari insiden.csv):")
        for entity_id, count in summarize_insiden_per_entitas(args.insiden).items():
            print(f"  {entity_id}: {count}")


if __name__ == "__main__":
    main()
