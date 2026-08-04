// Health check
fetch('/health')
    .then(res => res.json())
    .then(data => {
        document.getElementById('health-status').innerText = `✅ ${data.status} (service: ${data.service})`;
    })
    .catch(() => {
        document.getElementById('health-status').innerText = '❌ Server tidak responsif';
    });

// Konstanta
fetch('/precision/constants')
    .then(res => res.json())
    .then(data => {
        document.getElementById('constants').innerHTML = 
            `π_eff = ${data.pi_eff_61digits}\nΦ     = ${data.phi_61digits}`;
    });

// Pipeline dummy
document.getElementById('run-pipeline').addEventListener('click', function() {
    const payload = {
        "entity_id": "DEMO-001",
        "prices": [100, 102, 101, 105, 108, 107, 110, 115, 120, 118],
        "B_P": [0, 0, 0, 1, 2, 1, 0, 1, 2, 3],
        "B_Q": [0, 0, 0, 0, 1, 0, 1, 0, 0, 1],
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
    };

    const box = document.getElementById('result-box');
    box.innerText = '⏳ Memproses...';

    fetch('/pipeline/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        box.innerText = JSON.stringify(data, null, 2);
    })
    .catch(err => {
        box.innerText = '❌ Error: ' + err.message;
    });
});

// Audit verify
document.getElementById('verify-audit').addEventListener('click', function() {
    const box = document.getElementById('audit-result');
    box.innerText = '⏳ Memeriksa integritas...';

    fetch('/audit/verify')
        .then(res => res.json())
        .then(data => {
            box.innerText = JSON.stringify(data, null, 2);
        })
        .catch(err => {
            box.innerText = '❌ Error: ' + err.message;
        });
});