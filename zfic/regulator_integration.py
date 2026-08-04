"""
ZFIC V3 - Modul Regulator Integration
==========================================
Mengirim notifikasi ke regulator (KPK) dengan bukti audit trail.
Mendukung: Email terenkripsi (SMTP) dan HTTP API (jika tersedia).
"""

import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
from .audit_alert import AuditLog

class RegulatorNotifier:
    """
    Mengirim notifikasi ke regulator berdasarkan alert dari ZFIC.
    Support email (SMTP) dan HTTP API.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()

    def _validate_config(self):
        if "smtp" in self.config:
            required = ["host", "port", "username", "password", "from_email", "to_emails"]
            for key in required:
                if key not in self.config["smtp"]:
                    raise ValueError(f"SMTP config missing: {key}")
        elif "api" in self.config:
            if "url" not in self.config["api"]:
                raise ValueError("API config missing: url")
            if "api_key" not in self.config["api"]:
                raise ValueError("API config missing: api_key")
        else:
            raise ValueError("Config must contain either 'smtp' or 'api' section")

    def notify(self, entity_id: str, severity: str, fii_score: float,
               threshold: float, audit_log: AuditLog, score_breakdown: Dict[str, Any]) -> bool:
        """
        Kirim notifikasi ke regulator.
        """
        report = self._build_report(entity_id, severity, fii_score, threshold,
                                    audit_log, score_breakdown)

        if "smtp" in self.config:
            return self._send_email(report)
        elif "api" in self.config:
            return self._send_api(report)
        return False

    def _build_report(self, entity_id: str, severity: str, fii_score: float,
                      threshold: float, audit_log: AuditLog,
                      score_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """Bangun laporan terstruktur untuk regulator."""
        return {
            "timestamp": datetime.now().isoformat(),
            "entity_id": entity_id,
            "severity": severity,
            "fii_score": fii_score,
            "threshold": threshold,
            "score_breakdown": score_breakdown,
            "audit_hash": audit_log._last_hash if audit_log else "N/A",
            "note": "Laporan ini dihasilkan secara otomatis oleh ZFIC v3. "
                    "Silakan verifikasi sebelum mengambil tindakan."
        }

    def _send_email(self, report: Dict[str, Any]) -> bool:
        """Kirim notifikasi via SMTP."""
        try:
            smtp_config = self.config["smtp"]
            subject = f"[ZFIC] ALERT: {report['severity']} - {report['entity_id']}"
            body = json.dumps(report, indent=2)

            msg = MIMEMultipart()
            msg["From"] = smtp_config["from_email"]
            msg["To"] = ", ".join(smtp_config["to_emails"])
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
                server.starttls(context=context)
                server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def _send_api(self, report: Dict[str, Any]) -> bool:
        """Kirim notifikasi via HTTP API."""
        try:
            import requests
            api_config = self.config["api"]
            response = requests.post(
                api_config["url"],
                headers={
                    "Authorization": f"Bearer {api_config['api_key']}",
                    "Content-Type": "application/json"
                },
                json=report,
                timeout=10
            )
            return response.status_code in (200, 201, 202)
        except Exception as e:
            print(f"Failed to send API request: {e}")
            return False