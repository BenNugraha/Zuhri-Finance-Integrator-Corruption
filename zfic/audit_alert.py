"""
ZFIC V3 - Modul Audit & Alert (Kill-Switch Protocol)
========================================================
Melengkapi poin #5 rencana aksi ZFIC asli:
  "Aktifkan kill-switch otomatis jika FII melewati threshold"
  + protokol restorasi: locking aset, audit otomatis, notifikasi
    regulator dengan bukti audit trail.

Desain: append-only log dengan hash-chaining (tiap entri menyertakan
hash entri sebelumnya) -- ini pola standar tamper-evident logging
(dipakai di certificate transparency logs, blockchain sederhana, dsb).
Kalau ada entri yang diubah setelah ditulis, hash chain akan terputus
dan bisa dideteksi -- ini yang membuatnya cocok untuk "bukti audit
trail" ke regulator, bukan klaim kosong.
"""

import hashlib
import json
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Severity Tiers dengan ABSOLUTE FLOOR (perbaikan)
# ---------------------------------------------------------------------------
SEVERITY_TIERS = [
    (1.5, 0.9, "CODE_RED_CRITICAL", ["freeze_suspicious_assets", "mandatory_audit", "notify_regulator_immediate"]),
    (1.0, 0.85, "CODE_RED", ["mandatory_audit", "notify_regulator_24h"]),
    (0.8, 0.6, "WARNING_ELEVATED", ["flag_for_review", "increase_monitoring_frequency"]),
    (0.0, 0.0, "NORMAL", []),
]

def classify_severity(fii_score: float, threshold: float) -> dict:
    if threshold <= 0:
        raise ValueError("threshold harus > 0.")
    ratio = fii_score / threshold
    for lower_bound_ratio, lower_bound_abs, label, actions in SEVERITY_TIERS:
        if ratio >= lower_bound_ratio and fii_score >= lower_bound_abs:
            return {"ratio": ratio, "severity": label, "recommended_actions": actions}
    return {"ratio": ratio, "severity": "NORMAL", "recommended_actions": []}

# ---------------------------------------------------------------------------
# Audit Log (Hash-chained)
# ---------------------------------------------------------------------------
class AuditLog:
    GENESIS_HASH = "0" * 64
    def __init__(self, log_path: str):
        self.log_path = log_path
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
                if not lines: return self.GENESIS_HASH
                return json.loads(lines[-1])["entry_hash"]
        except FileNotFoundError: return self.GENESIS_HASH

    def append(self, record: dict) -> dict:
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "prev_hash": self._last_hash,
            "record": record,
        }
        entry_str = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
        entry["entry_hash"] = entry_hash
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        self._last_hash = entry_hash
        return entry

    def verify_chain(self) -> dict:
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {"valid": True, "n_entries": 0, "note": "Log belum ada."}
        prev_hash = self.GENESIS_HASH
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:  # <-- PERBAIKAN
                return {"valid": False, "broken_at_line": i, "reason": "JSON tidak valid — file corrupt"}
            claimed_hash = entry.pop("entry_hash")
            recomputed = hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()
            if recomputed != claimed_hash:
                return {"valid": False, "broken_at_line": i, "reason": "entry_hash tidak cocok"}
            if entry["prev_hash"] != prev_hash:
                return {"valid": False, "broken_at_line": i, "reason": "prev_hash tidak cocok"}
            prev_hash = claimed_hash
        return {"valid": True, "n_entries": len(lines)}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def format_notification(entity_id: str, classification: dict, audit_entry_hash: str, score_breakdown: dict) -> dict:
    return {
        "entity": entity_id,
        "severity": classification["severity"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audit_hash": audit_entry_hash,
        "actions": classification["recommended_actions"],
        "score_breakdown": score_breakdown,
    }

def evaluate_and_log(entity_id: str, fii_score: float, threshold: float,
                      score_breakdown: dict, audit_log: AuditLog) -> dict:
    # <-- PERBAIKAN: Validasi score_breakdown
    if not score_breakdown or not isinstance(score_breakdown, dict):
        raise ValueError("score_breakdown WAJIB disertakan sebagai dict.")

    classification = classify_severity(fii_score, threshold)
    record = {
        "entity_id": entity_id,
        "fii_score": fii_score,
        "threshold": threshold,
        "severity": classification["severity"],
        "ratio_to_threshold": classification["ratio"],
        "recommended_actions": classification["recommended_actions"],
        "score_breakdown": score_breakdown,
    }
    logged_entry = audit_log.append(record)
    return {
        "classification": classification,
        "audit_entry_hash": logged_entry["entry_hash"],
        "record": record,
    }