"""
ZFIC V3 - Modul 3: FII (Financial Integrity Index) & NSV
===========================================================
FII dipakai sebagai alat DETEKSI FRAUD (bukan trading -- dua tujuan itu
butuh label ground-truth berbeda dan akan menghasilkan bobot yang beda,
lihat catatan di compute_fii). Objektif: maksimalkan F1-score via grid
search + cross-validation pada data historis berlabel insiden.

NSV: agregasi indikator terukur dengan DampakNegatif eksplisit.
"""

import numpy as np
from itertools import product
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold  # <-- PERBAIKAN UTAMA

# ---------------------------------------------------------------------------
# NSV
# ---------------------------------------------------------------------------
def compute_nsv(indicators: np.ndarray, indicator_bounds: list,
                 negative_indicators: np.ndarray, negative_thresholds: np.ndarray,
                 lam: float = 1.0) -> dict:
    indicators = np.asarray(indicators, dtype=float)
    K = len(indicators)
    normalized = np.empty(K)
    for k, (lo, hi) in enumerate(indicator_bounds):
        if hi == lo:
            raise ValueError(f"Indikator ke-{k}: min==max, tidak bisa dinormalisasi.")
        normalized[k] = (indicators[k] - lo) / (hi - lo)
    aggregate_positive = normalized.mean()
    neg = np.asarray(negative_indicators, dtype=float)
    thr = np.asarray(negative_thresholds, dtype=float)
    dampak_negatif = np.mean(np.maximum(0, neg - thr))
    nsv = aggregate_positive - lam * dampak_negatif
    return {"nsv": float(nsv), "aggregate_positive": float(aggregate_positive), "dampak_negatif": float(dampak_negatif)}

# ---------------------------------------------------------------------------
# FII Optimisasi (Grid Search + Stratified K-Fold)
# ---------------------------------------------------------------------------
def _fii_score(anomali_norm, ars_norm, nsv_deficit_norm, w1, w2, w3):
    return w1 * anomali_norm + w2 * ars_norm + w3 * (1 - nsv_deficit_norm)

def optimize_fii_weights(anomali_norm: np.ndarray, ars_norm: np.ndarray,
                          nsv_deficit_norm: np.ndarray, y_true: np.ndarray,
                          n_grid: int = 21, n_folds: int = 5, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    # <-- PERBAIKAN: StratifiedKFold
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)

    grid_1d = np.linspace(0, 1, n_grid)
    weight_combos = [(w1, w2, 1 - w1 - w2)
                      for w1, w2 in product(grid_1d, grid_1d)
                      if w1 + w2 <= 1.0]
    best_f1, best_w, best_tau = -1, None, None
    for w1, w2, w3 in weight_combos:
        fii = _fii_score(anomali_norm, ars_norm, nsv_deficit_norm, w1, w2, w3)
        tau_candidates = np.quantile(fii, np.linspace(0.5, 0.99, 15))
        for tau in tau_candidates:
            fold_f1s = []
            for train_idx, test_idx in skf.split(fii, y_true):  # <-- PERBAIKAN
                y_pred = (fii[test_idx] >= tau).astype(int)
                if y_pred.sum() == 0 and y_true[test_idx].sum() == 0:
                    fold_f1s.append(1.0)
                else:
                    fold_f1s.append(f1_score(y_true[test_idx], y_pred, zero_division=0))
            mean_f1 = np.mean(fold_f1s)
            if mean_f1 > best_f1:
                best_f1, best_w, best_tau = mean_f1, (w1, w2, w3), tau
    return {"weights": {"w1": best_w[0], "w2": best_w[1], "w3": best_w[2]},
            "threshold_tau": float(best_tau), "cv_f1_score": float(best_f1)}