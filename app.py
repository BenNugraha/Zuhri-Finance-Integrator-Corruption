"""
ZFIC V3 - REST API (Flask) dengan Ocean Depths Theme
Full app with proper import for zfic package
"""

import os
import sys
import csv
import json
import io
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime


# ============================================================
# IMPORT MODUL DARI ZFIC (bukan backend)
# ============================================================
from zfic.ars_scoring import firth_logistic_regression
from zfic.fii_nsv import optimize_fii_weights
from zfic.bubble_detection import compute_regret
from zfic.audit_alert import AuditLog
from zfic.pipeline_orchestrator import run_zfic_pipeline_single_entity
from zfic.precision_core import get_pi_eff, get_phi, format_precision_digits

# ============================================================
# FLASK APP SETUP
# ============================================================
app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, 'frontend', 'templates'),
    static_folder=os.path.join(ROOT_DIR, 'frontend', 'static')
)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = os.path.join(ROOT_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================
# CONFIG
# ============================================================
AUDIT_LOG_PATH = os.environ.get("ZFIC_AUDIT_LOG_PATH", "/data/audit.jsonl")
CONTEXT_DATA_DIR = os.environ.get(
    "ZFIC_CONTEXT_DATA_DIR",
    os.path.join(ROOT_DIR, "templates_data"),
)

# ============================================================
# HELPERS
# ============================================================
def _get_audit_log() -> AuditLog:
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    return AuditLog(AUDIT_LOG_PATH)

def _read_csv_as_records(filename: str) -> list:
    path = os.path.join(CONTEXT_DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _validate_csv_columns(df, required_cols):
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return False, f"Kolom yang hilang: {missing}"
    return True, "OK"

# ============================================================
# ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "zfic-v3"})

@app.route("/precision/constants", methods=["GET"])
def precision_constants():
    return jsonify({
        "pi_eff_61digits": format_precision_digits(get_pi_eff()),
        "phi_61digits": format_precision_digits(get_phi()),
        "note": "Konstanta matematis standar dengan presisi 61 digit. Presisi ini tidak membuat hasil analisis lebih akurat; akurasi ditentukan oleh kualitas data input.",
    })

@app.route("/context/national-trend", methods=["GET"])
def context_national_trend():
    records = _read_csv_as_records("kpk_national_trend_2004_2025.csv")
    return jsonify({
        "records": records,
        "note": "Agregat nasional per tahun. BUKAN label per‑entitas.",
    })

@app.route("/context/cpi", methods=["GET"])
def context_cpi():
    records = _read_csv_as_records("cpi_context_2025.csv")
    return jsonify({
        "records": records,
        "note": "Skor CPI per negara (persepsi). Info latar saja.",
    })

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Tidak ada file yang diupload"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nama file kosong"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Hanya file CSV yang diizinkan"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)

        required = ['price']
        ok, msg = _validate_csv_columns(df, required)
        if not ok:
            return jsonify({"error": msg}), 400

        if 'B_P' not in df.columns:
            df['B_P'] = 0
        if 'B_Q' not in df.columns:
            df['B_Q'] = 0

        prices = df['price'].tolist()
        B_P = df['B_P'].tolist()
        B_Q = df['B_Q'].tolist()

        if len(prices) < 252:
            return jsonify({
                "error": f"Data hanya {len(prices)} titik. Minimal 252 titik (1 tahun data harian).",
                "hint": "Untuk demo dengan data pendek, gunakan tombol 'Jalankan Analisis'"
            }), 400

        payload = {
            "entity_id": file.filename.replace('.csv', ''),
            "prices": prices,
            "B_P": B_P,
            "B_Q": B_Q,
            "ars_features": {"A": 3, "R": 2, "B": 4, "M": 1},
            "ars_weights": [0.0, 0.1, 0.1, 0.1, 0.1],
            "fii_weights": {"w1": 0.4, "w2": 0.3, "w3": 0.3},
            "fii_threshold": 0.65,
            "nsv": {
                "indicators": [65, 0.7],
                "indicator_bounds": [[0, 100], [0, 1]],
                "negative_indicators": [0.2],
                "negative_thresholds": [0.3],
                "lam": 0.5
            }
        }

        audit_log = _get_audit_log()
        prices_series = pd.Series(prices)
        B_P_series = pd.Series(B_P)
        B_Q_series = pd.Series(B_Q)
        regret = compute_regret(prices_series)
        epsilon_crit = float(np.nanpercentile(regret.dropna(), 95))

        result = run_zfic_pipeline_single_entity(
            entity_id=payload["entity_id"],
            prices=prices_series,
            B_P=B_P_series,
            B_Q=B_Q_series,
            regret=regret,
            epsilon_crit=epsilon_crit,
            ars_features=payload["ars_features"],
            ars_weights=np.array(payload["ars_weights"]),
            nsv_inputs={
                "indicators": np.array(payload["nsv"]["indicators"]),
                "indicator_bounds": [tuple(b) for b in payload["nsv"]["indicator_bounds"]],
                "negative_indicators": np.array(payload["nsv"]["negative_indicators"]),
                "negative_thresholds": np.array(payload["nsv"]["negative_thresholds"]),
                "lam": payload["nsv"]["lam"],
            },
            fii_weights=payload["fii_weights"],
            fii_threshold=payload["fii_threshold"],
            audit_log=audit_log,
        )

        return jsonify({
            "status": "success",
            "entity_id": payload["entity_id"],
            "result": result,
            "data_points": len(prices),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"error": f"Kesalahan internal: {str(e)}"}), 500

@app.route("/pipeline/run", methods=["POST"])
def pipeline_run():
    cfg = request.get_json(force=True)
    if cfg is None:
        return jsonify({"error": "Body request harus JSON valid."}), 400

    required = ["entity_id", "prices", "B_P", "B_Q", "ars_features", "nsv"]
    missing = [k for k in required if k not in cfg]
    if missing:
        return jsonify({"error": f"Field wajib hilang: {missing}"}), 400

    if len(cfg["prices"]) < 252:
        return jsonify({
            "error": f"Data harga hanya {len(cfg['prices'])} titik. Minimal 252 titik.",
            "hint": "Ini karena kebutuhan baseline volatilitas 1 tahun."
        }), 400

    if not isinstance(cfg.get("prices"), list) or len(cfg["prices"]) < 2:
        return jsonify({"error": "prices harus list dengan minimal 2 elemen."}), 400

    try:
        prices = pd.Series(cfg["prices"])
        B_P = pd.Series(cfg["B_P"])
        B_Q = pd.Series(cfg["B_Q"])
        regret = compute_regret(prices)
        epsilon_crit = float(np.nanpercentile(regret.dropna(), cfg.get("epsilon_percentile", 95)))

        if "ars_weights" in cfg:
            ars_weights = np.array(cfg["ars_weights"])
        elif "incident_history" in cfg:
            hist = cfg["incident_history"]
            X = np.column_stack([
                np.ones(len(hist["A"])),
                hist["A"], hist["R"], hist["B"], hist["M"]
            ])
            y = np.array(hist["incident_label"])
            ars_weights = firth_logistic_regression(X, y)["beta"]
        else:
            return jsonify({"error": "Butuh 'ars_weights' atau 'incident_history'."}), 400

        if "fii_weights" in cfg and "fii_threshold" in cfg:
            fii_weights = cfg["fii_weights"]
            fii_threshold = cfg["fii_threshold"]
        elif "fraud_calibration_data" in cfg:
            fd = cfg["fraud_calibration_data"]
            opt = optimize_fii_weights(
                np.array(fd["anomali_norm"]),
                np.array(fd["ars_norm"]),
                np.array(fd["nsv_deficit_norm"]),
                np.array(fd["y_true"]),
                n_grid=cfg.get("fii_grid_size", 11),
            )
            fii_weights = opt["weights"]
            fii_threshold = opt["threshold_tau"]
        else:
            return jsonify({"error": "Butuh 'fii_weights'+'fii_threshold' atau 'fraud_calibration_data'."}), 400

        audit_log = _get_audit_log()

        result = run_zfic_pipeline_single_entity(
            entity_id=cfg["entity_id"],
            prices=prices,
            B_P=B_P,
            B_Q=B_Q,
            regret=regret,
            epsilon_crit=epsilon_crit,
            ars_features=cfg["ars_features"],
            ars_weights=ars_weights,
            nsv_inputs={
                "indicators": np.array(cfg["nsv"]["indicators"]),
                "indicator_bounds": [tuple(b) for b in cfg["nsv"]["indicator_bounds"]],
                "negative_indicators": np.array(cfg["nsv"]["negative_indicators"]),
                "negative_thresholds": np.array(cfg["nsv"]["negative_thresholds"]),
                "lam": cfg["nsv"].get("lam", 0.5),
            },
            fii_weights=fii_weights,
            fii_threshold=fii_threshold,
            audit_log=audit_log,
        )

        if result["severity"] in ("CODE_RED", "CODE_RED_CRITICAL"):
            result["executable_actions"] = [
                {
                    "action": "freeze_suspicious_assets",
                    "entity_id": cfg["entity_id"],
                    "audit_hash": result["audit_entry_hash"],
                    "reason": f"FII score {result['fii_score']:.4f} melewati threshold.",
                },
                {
                    "action": "notify_regulator",
                    "regulator": "KPK",
                    "entity_id": cfg["entity_id"],
                    "audit_hash": result["audit_entry_hash"],
                },
            ]
        else:
            result["executable_actions"] = []

        return jsonify(result)

    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Input tidak valid: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Kesalahan internal: {str(e)}"}), 500

@app.route("/audit/verify", methods=["GET"])
def audit_verify():
    audit_log = _get_audit_log()
    verification = audit_log.verify_chain()
    status_code = 200 if verification.get("valid", False) else 409
    return jsonify(verification), status_code

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    print(f"🚀 ZFIC V3 API berjalan di http://0.0.0.0:{port}")
    print(f"📁 Template: {app.template_folder}")
    print(f"📁 Upload: {app.config['UPLOAD_FOLDER']}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)