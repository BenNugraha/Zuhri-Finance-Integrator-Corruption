"""
ZFIC V3 - Modul 2: Agentic Risk Score (ARS)
=============================================
ARS = w_A*A + w_R*R + w_B*B + w_M*M, semua fitur diskalakan [0,10].

Bobot w diestimasi via Firth penalized logistic regression -- BUKAN
regresi logistik biasa, karena insiden (label y=1) pada data
korupsi/kegagalan sistemik itu rare event (class imbalance parah).
Regresi logistik standar (MLE) bias & tidak stabil pada kasus ini
(separasi sempurna / near-separation, standard error meledak).

Firth regression memperbaiki ini dengan penalized likelihood:
    L*(beta) = L(beta) * |I(beta)|^(1/2)
di mana I(beta) adalah Fisher information matrix. Ini setara dengan
menambah Jeffreys-invariant prior pada MLE biasa, dan terbukti secara
matematis mengurangi bias orde-O(1/n) pada estimator (Firth, 1993).

Implementasi manual di bawah mengikuti algoritma iteratif dari
Heinze & Schemper (2002), "A solution to the problem of separation
in logistic regression", Statistics in Medicine.
"""

import numpy as np

# ---------------------------------------------------------------------------
# 1. Firth Logistic Regression (Rare-event correction)
# ---------------------------------------------------------------------------
def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))

def firth_logistic_regression(X, y, max_iter=100, tol=1e-8, ridge=1e-8):
    n, p = X.shape
    beta = np.zeros(p)
    converged = False
    for it in range(max_iter):
        eta = X @ beta
        pi = _sigmoid(eta)
        W = np.clip(pi * (1 - pi), 1e-10, None)
        WX = X * W[:, None]
        XtWX = X.T @ WX + ridge * np.eye(p)
        XtWX_inv = np.linalg.inv(XtWX)
        sqrtW = np.sqrt(W)
        M = (X * sqrtW[:, None]) @ XtWX_inv @ (X * sqrtW[:, None]).T
        h = np.clip(np.diag(M), 0, 1 - 1e-10)
        U_star = X.T @ (y - pi + h * (0.5 - pi))
        delta = XtWX_inv @ U_star
        step = 1.0
        while np.max(np.abs(step * delta)) > 5.0 and step > 1e-3:
            step *= 0.5
        beta_new = beta + step * delta
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            converged = True
            break
        beta = beta_new
    eta = X @ beta
    pi = _sigmoid(eta)
    W = np.clip(pi * (1 - pi), 1e-10, None)
    XtWX = (X * W[:, None]).T @ X + ridge * np.eye(p)
    cov = np.linalg.inv(XtWX)
    se = np.sqrt(np.diag(cov))
    return {"beta": beta, "se": se, "converged": converged, "n_iter": it + 1}

# ---------------------------------------------------------------------------
# 2. Scaling Utilities
# ---------------------------------------------------------------------------
def scale_component(raw_values: np.ndarray, method: str = "minmax") -> np.ndarray:
    if method == "minmax":
        lo, hi = raw_values.min(), raw_values.max()
        if hi == lo: return np.zeros_like(raw_values)
        return 10.0 * (raw_values - lo) / (hi - lo)
    raise ValueError(f"Metode scaling '{method}' belum diimplementasi.")

def scale_logit_to_0_10(logit_values: np.ndarray, logit_min: float, logit_max: float) -> np.ndarray:
    if logit_max == logit_min:
        return np.full_like(logit_values, 5.0)
    return 10.0 * (logit_values - logit_min) / (logit_max - logit_min)

# ---------------------------------------------------------------------------
# 3. ARS Computation
# ---------------------------------------------------------------------------
def compute_ars(A: np.ndarray, R: np.ndarray, B: np.ndarray, M: np.ndarray,
                weights: np.ndarray, logit_min: float = None, logit_max: float = None) -> np.ndarray:
    X = np.column_stack([np.ones(len(A)), A, R, B, M])
    logit = X @ weights
    if logit_min is not None and logit_max is not None:
        return scale_logit_to_0_10(logit, logit_min, logit_max)
    else:
        print("⚠️ Peringatan: logit_min/max tidak diberikan. Mengembalikan logit mentah.")
        return logit