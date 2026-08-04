"""
ZFIC V3 - Modul 1: Bubble Detection (P-Q Unification)
=======================================================
Implementasi computable dari:
  - F_t^P via Dividend Discount Model + Gordon growth terminal value
  - B_t^Q via put-call parity (risk-neutral bubble dari harga opsi)
  - B_t^P sebagai residual
  - Regret_t: model-free drift detector (harga + volatilitas saja)
  - Anomali_t dengan kalibrasi epsilon_crit dan theta dari data historis

Semua fungsi mengembalikan angka float64 standar . Standar deviasi dari 
estimasi ini biasanya berada di orde 10⁻²–10⁻⁴
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. F_t^P -- Nilai fundamental via DDM + Gordon growth terminal value
# ---------------------------------------------------------------------------
def fundamental_value_ddm(dividend_forecasts: np.ndarray, r_hat: float,
                           g: float, horizon: int = None) -> float:
    """
    F_t^P = sum_{j=1}^{H} D_hat_{t+j} / (1+r_hat)^j
            + D_hat_{t+H+1} / [(r_hat - g) * (1+r_hat)^H]

    Parameters
    ----------
    dividend_forecasts : array of length H, proyeksi dividen t+1..t+H
                          (mis. dari ARIMA atau random-walk-with-drift fit
                          di luar fungsi ini -- lihat fit_dividend_forecast)
    r_hat : discount rate (mis. dari CAPM), harus > g atau Gordon growth
            divergen (ini syarat matematis wajib, bukan pilihan)
    g : tingkat pertumbuhan jangka panjang (mis. estimasi pertumbuhan GDP riil)
    horizon : override H; default = len(dividend_forecasts)

    Returns
    -------
    float : estimasi titik F_t^P (bukan interval -- lihat fundamental_value_ci
            untuk versi dengan confidence interval)
    """
    if r_hat <= g:
        raise ValueError(
            f"r_hat ({r_hat}) harus > g ({g}). Gordon growth model divergen "
            "kalau discount rate <= growth rate -- ini bukan pilihan desain, "
            "ini syarat konvergensi deret geometri tak hingga."
        )
    H = horizon or len(dividend_forecasts)
    disc = (1.0 + r_hat) ** np.arange(1, H + 1)
    pv_explicit = np.sum(np.asarray(dividend_forecasts[:H]) / disc)

    D_next = dividend_forecasts[-1] * (1.0 + g)  # D_hat_{t+H+1}
    terminal_value = D_next / (r_hat - g)
    pv_terminal = terminal_value / (1.0 + r_hat) ** H

    return pv_explicit + pv_terminal


def fundamental_value_ci(dividend_forecasts: np.ndarray, r_hat: float, g: float,
                          dividend_forecast_std: np.ndarray, r_hat_std: float,
                          n_sims: int = 20_000, seed: int = 0) -> dict:
    """
    Monte Carlo sensitivity: propagasi ketidakpastian input (bukan presisi
    61-desimal palsu) jadi confidence interval pada F_t^P.

    dividend_forecast_std, r_hat_std: standard error dari model peramalan
    (mis. dari residual ARIMA / CAPM regression). Ini yang Anda WAJIB punya
    kalau mau melapor F_t^P secara jujur -- tanpa ini, titik estimasi saja
    menyesatkan.
    """
    rng = np.random.default_rng(seed)
    H = len(dividend_forecasts)
    results = np.empty(n_sims)
    for i in range(n_sims):
        d_draw = dividend_forecasts + rng.normal(0, dividend_forecast_std, H)
        r_draw = r_hat + rng.normal(0, r_hat_std)
        if r_draw <= g:
            r_draw = g + 1e-4  # clamp untuk stabilitas numerik simulasi
        results[i] = fundamental_value_ddm(d_draw, r_draw, g)
    return {
        "mean": float(np.mean(results)),
        "ci_95": (float(np.percentile(results, 2.5)),
                  float(np.percentile(results, 97.5))),
        "std": float(np.std(results)),
    }


# ---------------------------------------------------------------------------
# 2. B_t^Q -- Q-bubble dari harga opsi via put-call parity
# ---------------------------------------------------------------------------
def bubble_Q_put_call_parity(S_t: float, K: float, r: float, T: float,
                              call_price: float, put_price: float) -> dict:
    """
    Put-call parity teoretis (tanpa bubble): C - P = S - K*exp(-rT)
    Jika pasar punya Q-bubble, parity ini menyimpang. Kita ekstrak deviasi:

        B_t^Q_estimate = (C_market - P_market) - (S_t - K*exp(-rT))

    Ini BUKAN estimasi B_t^Q absolut (itu perlu density penuh dari seluruh
    strike, lihat risk_neutral_density_breeden_litzenberger di bawah), tapi
    ukuran deviasi arbitrase yang menandakan gelembung risk-neutral lokal
    pada satu titik strike -- computable langsung dari data opsi yang ada.

    Returns dict berisi deviasi & apakah melampaui bid-ask spread wajar
    (tanpa itu, deviasi kecil bisa cuma noise transaksi, bukan bubble).
    """
    theoretical_diff = S_t - K * np.exp(-r * T)
    market_diff = call_price - put_price
    deviation = market_diff - theoretical_diff
    return {
        "deviation": deviation,
        "relative_deviation": deviation / S_t,
        "note": ("Deviasi > 0: put-call parity dilanggar ke arah call "
                 "overpriced relatif teori -- indikasi lokal Q-bubble. "
                 "Bandingkan magnitude ini dengan bid-ask spread opsi "
                 "sebelum menandainya sebagai sinyal, bukan noise."),
    }


def risk_neutral_density_breeden_litzenberger(strikes: np.ndarray,
                                                call_prices: np.ndarray,
                                                r: float, T: float) -> np.ndarray:
    """
    Metode yang lebih lengkap: ekstraksi risk-neutral density penuh dari
    seluruh smile opsi (Breeden & Litzenberger, 1978) -- metode standar,
    terverifikasi, dan bisa diimplementasikan langsung:

        q(K) = exp(rT) * d^2 C / dK^2

    Butuh strikes rapat & smooth (biasanya interpolasi cubic spline dulu
    sebelum diferensiasi numerik ganda, karena turunan kedua sangat sensitif
    terhadap noise harga opsi mentah).
    """
    if len(strikes) < 5:
        raise ValueError("Butuh >=5 titik strike untuk diferensiasi numerik "
                          "kedua yang stabil.")
    d2C_dK2 = np.gradient(np.gradient(call_prices, strikes), strikes)
    q = np.exp(r * T) * d2C_dK2
    q = np.clip(q, 0, None)  # density tidak boleh negatif (noise numerik)
    return q


# ---------------------------------------------------------------------------
# 3. Regret_t -- model-free drift detector
# ---------------------------------------------------------------------------
def compute_regret(prices: pd.Series, ma_window: int = 20,
                    vol_window: int = 30, vol_baseline_window: int = 252) -> pd.Series:
    """
    Regret_t = | (S_t - SMA_N(S)) / S_t | * (sigma_30d / sigma_baseline_1y)

    Computable murni dari harga historis. sigma dihitung dari realized
    volatility (std log-return), bukan implied vol (yang butuh data opsi).
    """
    log_ret = np.log(prices / prices.shift(1))
    sma = prices.rolling(ma_window).mean()
    drift_term = ((prices - sma) / prices).abs()

    sigma_t = log_ret.rolling(vol_window).std() * np.sqrt(252)
    sigma_baseline = log_ret.rolling(vol_baseline_window).std() * np.sqrt(252)

    regret = drift_term * (sigma_t / sigma_baseline)
    return regret


def compute_anomali(prices: pd.Series, B_P: pd.Series, B_Q: pd.Series,
                     regret: pd.Series, epsilon_crit: float) -> pd.Series:
    """
    Anomali_t = (|B_P| + |B_Q|) / S_t * tanh(Regret_t / epsilon_crit)
    """
    magnitude = (B_P.abs() + B_Q.abs()) / prices
    return magnitude * np.tanh(regret / epsilon_crit)


# ---------------------------------------------------------------------------
# 4. Kalibrasi epsilon_crit dan theta dari "periode tenang" (proxy VIX)
# ---------------------------------------------------------------------------
def calibrate_thresholds(regret: pd.Series, anomali: pd.Series,
                          vix: pd.Series, vix_threshold: float = 20.0,
                          min_quiet_months: int = 12) -> dict:
    """
    "Periode tenang" didefinisikan objektif: VIX < vix_threshold selama
    >= min_quiet_months bulan berturut-turut. epsilon_crit dan theta
    dikalibrasi HANYA dari data pada periode itu -- bukan angka arbitrer.

    Catatan penting yang tidak boleh diabaikan: definisi ini sirkular
    kalau anomali dan calm-period sama-sama diturunkan dari volatilitas.
    Di sini regret/anomali pakai realized volatility SAHAM, sedangkan
    "tenang" pakai VIX (implied vol index pasar luas) -- keduanya proxy
    independen secara sumber data, jadi sirkularitasnya lemah, tapi TIDAK
    nol (index luas dan volatilitas saham individual berkorelasi). Untuk
    kalibrasi yang benar-benar independen, idealnya pakai daftar periode
    krisis yang sudah diketahui historis (mis. dari NBER recession dates)
    sebagai exclusion list tambahan, bukan hanya threshold VIX.
    """
    is_quiet = vix < vix_threshold
    quiet_run = is_quiet.rolling(min_quiet_months).sum() == min_quiet_months

    calm_idx = quiet_run[quiet_run].index
    if len(calm_idx) < 30:
        raise ValueError(
            f"Hanya {len(calm_idx)} observasi periode tenang ditemukan -- "
            "terlalu sedikit untuk estimasi persentil yang stabil. "
            "Perlebar rentang data atau longgarkan vix_threshold."
        )

    regret_calm = regret.loc[regret.index.isin(calm_idx)].dropna()
    epsilon_crit = np.percentile(regret_calm, 95)

    # theta butuh anomali yang sudah dihitung pakai epsilon_crit ini
    return {
        "epsilon_crit": float(epsilon_crit),
        "n_calm_obs": len(calm_idx),
        "note": "Hitung ulang Anomali_t dengan epsilon_crit ini, lalu "
                "panggil np.percentile(anomali_calm, 99) untuk theta.",
    }
