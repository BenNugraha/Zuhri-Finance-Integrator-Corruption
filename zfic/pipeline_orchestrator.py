"""
ZFIC V3 - Orkestrator Pipeline
=================================
Menyambungkan compute_nsv() -> nsv_deficit_norm yang dibutuhkan
optimize_fii_weights() dan evaluate_and_log(), dan menjalankan seluruh
modul secara berurutan untuk SATU entitas.

Alur: Bubble Detection -> ARS -> NSV -> FII -> Audit/Alert
"""

import numpy as np
from .bubble_detection import compute_anomali
from .ars_scoring import compute_ars
from .fii_nsv import compute_nsv, _fii_score
from .audit_alert import evaluate_and_log, AuditLog

def nsv_to_deficit_norm(nsv_value: float, nsv_min: float = -1.0, nsv_max: float = 1.0) -> float:
    normalized_nsv = np.clip((nsv_value - nsv_min) / (nsv_max - nsv_min), 0, 1)
    return float(1.0 - normalized_nsv)

def run_zfic_pipeline_single_entity(
    entity_id: str,
    prices, B_P, B_Q, regret, epsilon_crit,
    ars_features: dict,
    ars_weights: np.ndarray,
    nsv_inputs: dict,
    fii_weights: dict,
    fii_threshold: float,
    audit_log: AuditLog,
) -> dict:
    # 1. Bubble
    anomali_series = compute_anomali(prices, B_P, B_Q, regret, epsilon_crit)
    anomali_latest = float(anomali_series.dropna().iloc[-1])
    anomali_norm = float(np.clip(anomali_latest, 0, 1))

    # 2. ARS
    A = np.array([ars_features["A"]])
    R = np.array([ars_features["R"]])
    B = np.array([ars_features["B"]])
    M = np.array([ars_features["M"]])
    ars_raw = compute_ars(A, R, B, M, ars_weights)[0]
    ars_norm = float(1.0 / (1.0 + np.exp(-ars_raw)))

    # 3. NSV
    nsv_result = compute_nsv(**nsv_inputs)
    nsv_deficit_norm = nsv_to_deficit_norm(nsv_result["nsv"])

    # 4. FII
    w1, w2, w3 = fii_weights["w1"], fii_weights["w2"], fii_weights["w3"]
    fii_score = _fii_score(anomali_norm, ars_norm, nsv_deficit_norm, w1, w2, w3)

    # 5. Audit
    breakdown = {
        "anomali_norm": anomali_norm,
        "ars_norm": ars_norm,
        "ars_raw_logit": float(ars_raw),
        "nsv_value": nsv_result["nsv"],
        "nsv_deficit_norm": nsv_deficit_norm,
        "weights": fii_weights,
    }
    alert_result = evaluate_and_log(
        entity_id=entity_id,
        fii_score=float(fii_score),
        threshold=fii_threshold,
        score_breakdown=breakdown,
        audit_log=audit_log,
    )

    return {
        "entity_id": entity_id,
        "fii_score": float(fii_score),
        "severity": alert_result["classification"]["severity"],
        "recommended_actions": alert_result["classification"]["recommended_actions"],
        "audit_entry_hash": alert_result["audit_entry_hash"],
        "breakdown": breakdown,
    }