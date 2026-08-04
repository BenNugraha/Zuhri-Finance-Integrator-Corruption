"""
ZFIC - Modul Precision Core
==============================
"""

import mpmath

# Presisi kerja mpmath: minta beberapa digit ekstra sebagai buffer
# supaya digit ke-61 tetap akurat setelah pembulatan.
_DIGITS = 61
mpmath.mp.dps = _DIGITS + 10


def get_pi_eff() -> mpmath.mpf:
    """Konstanta pi standar, dihitung ulang oleh mpmath (bukan disalin manual)."""
    return +mpmath.pi


def get_phi() -> mpmath.mpf:
    """Golden ratio: (1 + sqrt(5)) / 2, dihitung ulang oleh mpmath."""
    return (1 + mpmath.sqrt(5)) / 2


def format_precision_digits(value: mpmath.mpf, digits: int = _DIGITS) -> str:
    """Format nilai mpmath menjadi string dengan jumlah digit signifikan tertentu."""
    return mpmath.nstr(value, digits, strip_zeros=False)
