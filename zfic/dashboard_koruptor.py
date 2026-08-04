"""
ZFIC V3 - Modul Dashboard Koruptor Watch
==================================================
Halaman monitoring real-time untuk entitas berisiko tinggi.
Menampilkan FII score, severity, dan rekomendasi aksi.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from flask import render_template, Blueprint, jsonify
from .audit_alert import AuditLog

dashboard = Blueprint("dashboard", __name__, template_folder="templates")

class KoruptorWatch:
    """
    Dashboard untuk memantau entitas berisiko.
    """

    def __init__(self, audit_log: AuditLog):
        self.audit_log = audit_log
        self.threshold = 0.8  # default threshold untuk display

    def get_high_risk_entities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ambil entitas berisiko tinggi dari audit log.
        """
        try:
            with open(self.audit_log.log_path, "r") as f:
                lines = f.readlines()[-limit:]
        except FileNotFoundError:
            return []

        entities = []
        for line in lines:
            try:
                entry = json.loads(line)
                record = entry.get("record", {})
                if record.get("severity") in ("CODE_RED", "CODE_RED_CRITICAL", "WARNING_ELEVATED"):
                    entities.append({
                        "entity_id": record.get("entity_id", "Unknown"),
                        "severity": record.get("severity", "NORMAL"),
                        "fii_score": record.get("fii_score", 0.0),
                        "timestamp": entry.get("timestamp_utc", ""),
                        "audit_hash": entry.get("entry_hash", "")
                    })
            except json.JSONDecodeError:
                continue
        return entities[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """
        Ringkasan status keseluruhan.
        """
        high_risk = self.get_high_risk_entities(limit=100)
        return {
            "total_high_risk": len(high_risk),
            "code_red_critical": sum(1 for e in high_risk if e["severity"] == "CODE_RED_CRITICAL"),
            "code_red": sum(1 for e in high_risk if e["severity"] == "CODE_RED"),
            "warning": sum(1 for e in high_risk if e["severity"] == "WARNING_ELEVATED"),
            "last_updated": datetime.now().isoformat()
        }


@dashboard.route("/")
def dashboard_home():
    """Halaman utama dashboard."""
    audit_log = AuditLog(os.environ.get("ZFIC_AUDIT_LOG_PATH", "/data/audit.jsonl"))
    watch = KoruptorWatch(audit_log)
    summary = watch.get_summary()
    entities = watch.get_high_risk_entities(limit=20)
    return render_template("dashboard_koruptor.html", summary=summary, entities=entities)


@dashboard.route("/api/entities")
def api_entities():
    """API endpoint untuk data entitas berisiko (JSON)."""
    audit_log = AuditLog(os.environ.get("ZFIC_AUDIT_LOG_PATH", "/data/audit.jsonl"))
    watch = KoruptorWatch(audit_log)
    return jsonify({
        "summary": watch.get_summary(),
        "entities": watch.get_high_risk_entities(limit=50)
    })