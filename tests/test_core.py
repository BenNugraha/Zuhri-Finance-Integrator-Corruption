"""
Test dasar (bukan komprehensif) untuk memastikan modul inti ZFIC
tidak rusak setelah perubahan. Jalankan: pytest tests/ (dari root project).
"""

import sys
import os

# Tambahkan root proyek ke sys.path agar modul di folder backend/ bisa ditemukan
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd
import pytest

# Impor modul dari folder backend (bukan zfic)
from backend.precision_core import get_pi_eff, get_phi, format_precision_digits
from backend.bubble_detection import compute_regret, compute_anomali
from backend.ars_scoring import firth_logistic_regression, compute_ars, scale_component
from backend.fii_nsv import compute_nsv, _fii_score
from backend.audit_alert import classify_severity, AuditLog


def test_precision_constants():
    pi_str = format_precision_digits(get_pi_eff())
    phi_str = format_precision_digits(get_phi())
    assert pi_str.startswith("3.14159265358979")
    assert phi_str.startswith("1.61803398874989")


def test_compute_regret_and_anomali_shapes():
    rng = np.random.default_rng(0)
    n = 300
    prices = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.018, n))))
    regret = compute_regret(prices)
    assert len(regret) == n
    B_P = pd.Series(rng.normal(0, 2, n))
    B_Q = pd.Series(rng.normal(0, 1, n))
    epsilon_crit = float(np.nanpercentile(regret, 95))
    anomali = compute_anomali(prices, B_P, B_Q, regret, epsilon_crit)
    assert len(anomali) == n
    assert anomali.dropna().shape[0] > 0


def test_firth_logistic_regression_converges():
    rng = np.random.default_rng(1)
    n = 300
    A = rng.uniform(0, 10, n)
    R = rng.uniform(0, 10, n)
    B = rng.uniform(0, 10, n)
    M = rng.uniform(0, 10, n)
    logit = -3 + 0.1 * A + 0.05 * R + 0.1 * B
    y = rng.binomial(1, 1 / (1 + np.exp(-logit)))
    X = np.column_stack([np.ones(n), A, R, B, M])
    result = firth_logistic_regression(X, y)
    assert result["converged"]
    assert len(result["beta"]) == 5


def test_compute_ars_and_scale_component():
    A = scale_component(np.array([1.0, 5.0, 10.0]))
    assert A.min() == 0.0
    assert A.max() == 10.0
    ars = compute_ars(np.array([5.0]), np.array([5.0]), np.array([5.0]),
                       np.array([5.0]), np.array([0.0, 0.1, 0.1, 0.1, 0.1]))
    assert ars.shape == (1,)


def test_compute_nsv_basic():
    result = compute_nsv(
        indicators=np.array([50.0, 0.5]),
        indicator_bounds=[(0, 100), (0, 1)],
        negative_indicators=np.array([0.3]),
        negative_thresholds=np.array([0.35]),
        lam=1.0,
    )
    assert -1.0 <= result["nsv"] <= 1.0
    assert result["dampak_negatif"] == 0.0  # 0.3 < threshold 0.35 -> tidak ada dampak


def test_classify_severity_tiers():
    normal = classify_severity(0.5, threshold=1.0)
    assert normal["severity"] == "NORMAL"
    warning = classify_severity(0.85, threshold=1.0)
    assert warning["severity"] == "WARNING_ELEVATED"
    code_red = classify_severity(1.2, threshold=1.0)
    assert code_red["severity"] == "CODE_RED"
    critical = classify_severity(1.6, threshold=1.0)
    assert critical["severity"] == "CODE_RED_CRITICAL"


def test_classify_severity_rejects_nonpositive_threshold():
    with pytest.raises(ValueError):
        classify_severity(1.0, threshold=0)


def test_audit_log_append_and_verify(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    audit_log = AuditLog(str(log_path))
    audit_log.append({"entity_id": "ENT001", "fii_score": 0.5})
    audit_log.append({"entity_id": "ENT002", "fii_score": 0.9})
    verification = audit_log.verify_chain()
    assert verification["valid"] is True
    assert verification["n_entries"] == 2


def test_audit_log_detects_tampering(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    audit_log = AuditLog(str(log_path))
    audit_log.append({"entity_id": "ENT001", "fii_score": 0.5})

    # Manipulasi manual isi file (simulasi tampering)
    content = log_path.read_text()
    tampered = content.replace('"fii_score": 0.5', '"fii_score": 0.1')
    log_path.write_text(tampered)

    verification = audit_log.verify_chain()
    assert verification["valid"] is False
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])