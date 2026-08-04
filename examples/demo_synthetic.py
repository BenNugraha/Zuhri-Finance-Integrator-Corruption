"""
ZFIC - Demo integrasi end-to-end dengan data SINTETIS.
Menunjukkan alur: Bubble Detection -> ARS -> NSV -> FII gabungan.

INI DEMO DENGAN DATA SINTETIS. Untuk pakai data riil, isi
templates_data/ (lihat templates_data/README.md) lalu gunakan
tools/build_training_table.py dan panggil endpoint /pipeline/run,
atau import langsung modul-modul di package `zfic`.

Jalankan dari root project:
    pip install -e .
    python examples/demo_synthetic.py
"""

import numpy as np
import pandas as pd

from zfic.bubble_detection import (compute_regret, compute_anomali,
                                    calibrate_thresholds)
from zfic.ars_scoring import firth_logistic_regression, compute_ars, scale_component
from zfic.fii_nsv import compute_nsv, optimize_fii_weights

rng = np.random.default_rng(42)

print("=" * 70)
print("1. BUBBLE DETECTION")
print("=" * 70)

n_days = 800
prices = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.018, n_days))))
vix = pd.Series(15 + 10 * np.abs(rng.normal(0, 1, n_days)))  # synthetic VIX-like

regret = compute_regret(prices)

try:
    calib = calibrate_thresholds(regret, None, vix, vix_threshold=20, min_quiet_months=20)
    epsilon_crit = calib["epsilon_crit"]
    print(f"epsilon_crit dikalibrasi dari {calib['n_calm_obs']} observasi tenang: "
          f"{epsilon_crit:.4f}")
except ValueError as e:
    print(f"Kalibrasi gagal ({e}); pakai fallback epsilon_crit dari seluruh data.")
    epsilon_crit = float(np.nanpercentile(regret, 95))

B_P_synth = pd.Series(rng.normal(0, 2, n_days))
B_Q_synth = pd.Series(rng.normal(0, 1, n_days))
anomali = compute_anomali(prices, B_P_synth, B_Q_synth, regret, epsilon_crit)
theta = float(np.nanpercentile(anomali, 99))
print(f"theta (99th pct anomali periode ini): {theta:.5f}")
print(f"Jumlah observasi ter-flag (anomali > theta): {(anomali > theta).sum()}")

print()
print("=" * 70)
print("2. ARS -- Firth logistic regression")
print("=" * 70)

n_entities = 500
A_raw = rng.uniform(0, 1, n_entities)
R_raw = rng.uniform(0, 1, n_entities)
B_raw = rng.lognormal(2, 1.5, n_entities)
M_raw = rng.poisson(3, n_entities).astype(float)

A = scale_component(A_raw)
R = scale_component(R_raw)
B = scale_component(np.log1p(B_raw))
M = scale_component(np.log1p(M_raw))

true_incident_logit = -3.5 + 0.15 * A + 0.1 * R + 0.2 * B + 0.05 * M
p_incident = 1 / (1 + np.exp(-true_incident_logit))
incidents = rng.binomial(1, p_incident)
print(f"Rate insiden historis (SINTETIS): {incidents.mean():.3f} "
      f"({incidents.sum()}/{n_entities})")

X_design = np.column_stack([np.ones(n_entities), A, R, B, M])
firth_result = firth_logistic_regression(X_design, incidents)
print(f"Bobot ARS (Firth) [intercept, w_A, w_R, w_B, w_M]: "
      f"{np.round(firth_result['beta'], 4)}")
print(f"Converged: {firth_result['converged']} in {firth_result['n_iter']} iterasi")

ars_scores = compute_ars(A, R, B, M, firth_result["beta"])
ars_norm = scale_component(ars_scores) / 10.0  # normalisasi [0,1] untuk FII
print(f"ARS range: [{ars_scores.min():.2f}, {ars_scores.max():.2f}]")
print(f"Entitas dengan ARS >= persentil-90 (kandidat mandatory Layer-2 controls): "
      f"{(ars_scores >= np.percentile(ars_scores, 90)).sum()}")

print()
print("=" * 70)
print("3. NSV")
print("=" * 70)

nsv_result = compute_nsv(
    indicators=np.array([68.0, 0.71]),
    indicator_bounds=[(0, 100), (0, 1)],
    negative_indicators=np.array([0.39, 7.2]),
    negative_thresholds=np.array([0.35, 6.0]),
    lam=0.5,
)
print(f"NSV (SINTETIS, indikator contoh): {nsv_result}")

print()
print("=" * 70)
print("4. FII -- optimisasi bobot via F1-score cross-validated")
print("=" * 70)

anomali_sample = np.clip(anomali.dropna().sample(n_entities, random_state=1).values, 0, 1)
nsv_deficit_synth = np.clip(1 - rng.beta(3, 3, n_entities), 0, 1)

fii_out = optimize_fii_weights(
    anomali_norm=anomali_sample,
    ars_norm=ars_norm,
    nsv_deficit_norm=nsv_deficit_synth,
    y_true=incidents,
    n_grid=11,
    n_folds=5,
)
print(f"Bobot FII teroptimasi: {fii_out['weights']}")
print(f"Threshold klasifikasi: {fii_out['threshold_tau']:.4f}")
print(f"CV F1-score: {fii_out['cv_f1_score']:.4f}")

print()
print("=" * 70)
print("CATATAN: seluruh angka di atas dari DATA SINTETIS untuk verifikasi")
print("bahwa pipeline berjalan tanpa error matematis. Hasil pada data riil")
print("akan sangat bergantung pada kualitas label insiden historis Anda --")
print("lihat templates_data/README.md dan labeling_rule.md sebelum pakai")
print("data riil untuk keputusan sungguhan.")
print("=" * 70)
