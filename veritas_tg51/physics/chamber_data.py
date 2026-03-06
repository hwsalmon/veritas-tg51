"""
chamber_data.py — Tabulated and parametric kQ data for ion chambers.

Sources:
  Photon kQ:    TG-51 (1999) Table I — Almond et al., Med. Phys. 26(9):1847–1870
  Electron kQ:  WGTG51 Report 385 (2024) — Muir et al., Med. Phys. 51:5840–5857
                  Table 4 (k_Qecal, cylindrical)
                  Table 5 (k'_Q power-fit params, cylindrical)
  A12 specs:    Standard Imaging Exradin brochure (1180-30)
                  r_cav = 0.305 cm, wall = C-552, volume = 0.64 cc

All interpolation is linear in %dd(10)_x for photons.
k'_Q for electrons uses the power-law fit:  k'_Q = a0 + b0 * R50^c0
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Exradin A12 physical specifications
# ---------------------------------------------------------------------------

A12_SPECS = {
    "manufacturer": "Standard Imaging",
    "model": "Exradin A12",
    "volume_cc": 0.64,
    "r_cav_cm": 0.305,          # cavity radius
    "wall_material": "C-552",
    "wall_thickness_gcm2": 0.088,
    "collector_length_mm": 21.6,
    "recommended_bias_v": 300,
    "is_waterproof": True,
    # EPOM shifts (Report 374 Table 1 & 2)
    "epom_photon_mm": 1.4,       # upstream shift for PDI in photon beams
    "epom_electron_mm": 1.1,     # upstream shift for PDI in electron beams
}

# ---------------------------------------------------------------------------
# Photon kQ data — TG-51 (1999) Table I
# Chambers listed with %dd(10)_x breakpoints: [58.0, 63.0, 66.0, 71.0, 81.0, 93.0]
# ---------------------------------------------------------------------------

PHOTON_KQ_PDDX_BREAKPOINTS = np.array([58.0, 63.0, 66.0, 71.0, 81.0, 93.0])

# Dict key: chamber model string (lowercase, spaces allowed)
# Value: kQ at each breakpoint above
PHOTON_KQ_TABLE: dict[str, np.ndarray] = {
    # Exradin
    "exradin a12":    np.array([1.000, 0.999, 0.996, 0.990, 0.972, 0.948]),
    "exradin a1":     np.array([0.999, 0.998, 0.996, 0.990, 0.972, 0.948]),
    "exradin a1sl":   np.array([0.999, 0.998, 0.996, 0.990, 0.972, 0.948]),
    # Capintec
    "capintec pr-05": np.array([0.999, 0.997, 0.995, 0.990, 0.972, 0.948]),
    "capintec pr-05p":np.array([0.999, 0.997, 0.995, 0.990, 0.972, 0.948]),
    "capintec pr-06c":np.array([1.000, 0.998, 0.994, 0.987, 0.968, 0.944]),
    # NE
    "ne2505":         np.array([1.000, 0.998, 0.995, 0.988, 0.972, 0.951]),
    "ne2505/3a":      np.array([1.000, 0.998, 0.995, 0.988, 0.972, 0.951]),
    "ne2561":         np.array([1.000, 0.998, 0.995, 0.989, 0.974, 0.953]),
    "ne2571":         np.array([1.000, 0.998, 0.995, 0.988, 0.972, 0.951]),
    "ne2577":         np.array([1.000, 0.998, 0.995, 0.988, 0.972, 0.951]),
    "ne2581":         np.array([1.000, 0.994, 0.988, 0.979, 0.960, 0.937]),
    # PTW
    "ptw n30001":     np.array([1.000, 0.996, 0.992, 0.984, 0.967, 0.945]),
    "ptw n30002":     np.array([1.000, 0.997, 0.994, 0.987, 0.970, 0.948]),
    "ptw n30004":     np.array([1.000, 0.998, 0.995, 0.988, 0.973, 0.952]),
    "ptw n31003":     np.array([1.000, 0.996, 0.992, 0.984, 0.967, 0.946]),
    # Wellhofer / IBA
    "wellhofer ic-10":np.array([1.000, 0.999, 0.996, 0.989, 0.971, 0.946]),
    "wellhofer ic-5": np.array([1.000, 0.999, 0.996, 0.989, 0.971, 0.946]),
}


# Aliases: normalise common variant spellings to canonical table keys
_PHOTON_KQ_ALIASES: dict[str, str] = {
    # Standard Imaging / Exradin A12
    "standard imaging a12":  "exradin a12",
    "si a12":                "exradin a12",
    "a12":                   "exradin a12",
    "exradin a-12":          "exradin a12",
    # Exradin A1
    "a1":                    "exradin a1",
    "exradin a-1":           "exradin a1",
    # Exradin A1SL
    "a1sl":                  "exradin a1sl",
    "exradin a-1sl":         "exradin a1sl",
    # PTW
    "ptw 30001":             "ptw n30001",
    "ptw 30002":             "ptw n30002",
    "ptw 30004":             "ptw n30004",
    "ptw 31003":             "ptw n31003",
    # NE
    "ne 2571":               "ne2571",
    "ne 2561":               "ne2561",
    "ne 2505":               "ne2505",
    "ne 2581":               "ne2581",
}


def get_photon_kq(chamber_model: str, pdd10x: float) -> float:
    """
    Interpolate k_Q for a photon beam from TG-51 (1999) Table I.

    Parameters
    ----------
    chamber_model : str
        Chamber model name (case-insensitive). Must be a key in PHOTON_KQ_TABLE.
    pdd10x : float
        %dd(10)_x — the photon beam quality specifier (%).

    Returns
    -------
    float
        k_Q value.

    Raises
    ------
    ValueError
        If chamber model not found or pdd10x is out of range.

    References
    ----------
    TG-51 (1999) Table I, Eq. (2): N_D,w^Q = k_Q * N_D,w^60Co
    """
    key = chamber_model.strip().lower()
    key = _PHOTON_KQ_ALIASES.get(key, key)
    if key not in PHOTON_KQ_TABLE:
        raise ValueError(
            f"Chamber '{chamber_model}' not in photon kQ table. "
            f"Available: {list(PHOTON_KQ_TABLE.keys())}"
        )
    if pdd10x < 55.0 or pdd10x > 95.0:
        raise ValueError(f"%dd(10)_x = {pdd10x:.2f}% is outside valid range 55–95%.")

    kq_values = PHOTON_KQ_TABLE[key]
    kq = float(np.interp(pdd10x, PHOTON_KQ_PDDX_BREAKPOINTS, kq_values))
    return kq


# ---------------------------------------------------------------------------
# Electron kQ data — WGTG51 Report 385 (2024)
# Cylindrical chambers, central axis at d_ref (no gradient correction)
# ---------------------------------------------------------------------------

# k_Qecal for cylindrical chambers — Table 4 of 2024 Addendum
# Chamber positioned with central axis at d_ref (no EPOM shift for reference dosimetry)
ELECTRON_KQECAL_CYL: dict[str, float] = {
    "exradin a12":  0.907,
    "exradin a19":  0.904,
    "exradin a18":  0.914,
    "exradin a1sl": 0.914,
    "ne2571":       0.903,
    "ptw 30013":    0.901,
    "iba fc65g":    0.904,
}

# k'_Q power-law fit for cylindrical chambers — Table 5 of 2024 Addendum
# Form: k'_Q(cyl) = a0 + b0 * R50^c0   [valid 1.70 cm <= R50 <= 8.70 cm]
# Columns: a0, b0, c0, RMSD(%)
ELECTRON_KQ_PRIME_CYL_PARAMS: dict[str, tuple[float, float, float]] = {
    "exradin a12":  (0.965, 0.119, 0.607),
    "exradin a19":  (0.957, 0.119, 0.505),
    "exradin a18":  (0.352, 0.711, 0.046),
    "exradin a1sl": (0.205, 0.854, 0.036),
    "ne2571":       (0.977, 0.117, 0.817),
    "ptw 30013":    (0.978, 0.112, 0.816),
    "iba fc65g":    (0.971, 0.113, 0.680),
}

# k_Qecal for parallel-plate chambers — Table 6 of 2024 Addendum
ELECTRON_KQECAL_PP: dict[str, float] = {
    "ptw roos":         0.898,
    "ptw markus":       0.898,
    "ptw adv. markus":  0.899,
    "iba nacp-02":      0.892,
    "iba ppc40":        0.900,
    "iba ppc05":        0.890,
    "exradin a10":      0.923,
    "exradin a11":      0.906,
    "exradin p11":      0.883,
    "exradin p11tw":    0.879,
}

# k'_Q exponential fit for parallel-plate chambers — Table 7 of 2024 Addendum
# Form: k'_Q(pp) = a1 + b1 * exp(-R50/c1)   [valid 1.70 cm <= R50 <= 8.70 cm]
ELECTRON_KQ_PRIME_PP_PARAMS: dict[str, tuple[float, float, float]] = {
    "ptw roos":        (0.984, 0.134, 3.511),
    "ptw markus":      (0.984, 0.826, 0.10),
    "ptw adv. markus": (0.986, 0.135, 3.349),
    "iba nacp-02":     (0.985, 0.135, 3.398),
    "iba ppc40":       (0.985, 0.130, 3.510),
    "iba ppc05":       (0.982, 0.104, 4.248),
    "exradin a10":     (0.991, 0.113, 2.927),
    "exradin a11":     (0.992, 0.114, 2.864),
    "exradin p11":     (0.989, 0.177, 2.687),
    "exradin p11tw":   (0.990, 0.165, 2.720),
}

R50_MIN_CM = 1.70
R50_MAX_CM = 8.70


def get_electron_kq(chamber_model: str, r50_cm: float,
                    chamber_type: str = "cylindrical") -> dict[str, float]:
    """
    Compute k_Q = k'_Q * k_Qecal for an electron beam using the 2024 WGTG51-e
    Addendum formalism (WGTG51 Report 385).

    For cylindrical chambers: k'_Q = a0 + b0 * R50^c0  [Table 5, Eq. 7]
    For parallel-plate chambers: k'_Q = a1 + b1 * exp(-R50/c1)  [Table 7, Eq. 8]

    Note: Gradient correction P_gr^Q is NOT applied separately — it is included
    implicitly in the Monte Carlo calculated k_Q factors provided here.

    Parameters
    ----------
    chamber_model : str
        Chamber model (case-insensitive).
    r50_cm : float
        R_50 — beam quality specifier (cm). Valid range: 1.70–8.70 cm (4–22 MeV).
    chamber_type : str
        "cylindrical" or "parallel_plate".

    Returns
    -------
    dict with keys: k_qecal, k_q_prime, k_q

    References
    ----------
    WGTG51 Report 385 (2024) Sec. 5.2, Eq. (4):
        D_w^Q = M * k_Q * N_D,w^60Co = M * k'_Q * k_Qecal * N_D,w^60Co
    Table 4: k_Qecal (cylindrical, central axis at d_ref)
    Table 5: k'_Q power-fit params (cylindrical)
    Table 6: k_Qecal (parallel-plate)
    Table 7: k'_Q exponential-fit params (parallel-plate)
    """
    key = chamber_model.strip().lower()
    key = _PHOTON_KQ_ALIASES.get(key, key)

    if not (R50_MIN_CM <= r50_cm <= R50_MAX_CM):
        raise ValueError(
            f"R_50 = {r50_cm:.3f} cm is outside valid range "
            f"{R50_MIN_CM}–{R50_MAX_CM} cm for 2024 Addendum kQ data."
        )

    if chamber_type == "cylindrical":
        if key not in ELECTRON_KQECAL_CYL:
            raise ValueError(
                f"Cylindrical chamber '{chamber_model}' not in 2024 Addendum Table 4. "
                f"Available: {list(ELECTRON_KQECAL_CYL.keys())}"
            )
        k_qecal = ELECTRON_KQECAL_CYL[key]
        a0, b0, c0 = ELECTRON_KQ_PRIME_CYL_PARAMS[key]
        k_q_prime = a0 + b0 * (r50_cm ** -c0)   # Report 385 Eq. 7: R50^(-c0)

    elif chamber_type == "parallel_plate":
        if key not in ELECTRON_KQECAL_PP:
            raise ValueError(
                f"Parallel-plate chamber '{chamber_model}' not in 2024 Addendum Table 6. "
                f"Available: {list(ELECTRON_KQECAL_PP.keys())}"
            )
        k_qecal = ELECTRON_KQECAL_PP[key]
        a1, b1, c1 = ELECTRON_KQ_PRIME_PP_PARAMS[key]
        k_q_prime = a1 + b1 * np.exp(-r50_cm / c1)

    else:
        raise ValueError(f"chamber_type must be 'cylindrical' or 'parallel_plate', got {chamber_type!r}")

    k_q = k_q_prime * k_qecal

    return {
        "k_qecal": k_qecal,
        "k_q_prime": k_q_prime,
        "k_q": k_q,
    }


# ---------------------------------------------------------------------------
# FFF P_rp published values
# Key: (chamber_model_lower, linac_model_substr_lower, energy_mv)
# Value: (p_rp, uncertainty)
# Source: peer-reviewed 2024 data (Exradin A12, PTW 30013; Versa HD & TrueBeam)
# ---------------------------------------------------------------------------

_FFF_PRP_TABLE: list[tuple[str, str, float, float, float]] = [
    # (chamber_key, linac_substr, energy_mv, p_rp, uncertainty)
    ("exradin a12",  "versa",     6.0,  1.003, 0.0005),
    ("exradin a12",  "versa",     10.0, 1.005, 0.0005),
    ("exradin a12",  "truebeam",  6.0,  1.002, 0.0005),
    ("exradin a12",  "truebeam",  10.0, 1.005, 0.0005),
    ("ptw 30013",    "versa",     6.0,  1.003, 0.0005),
    ("ptw 30013",    "versa",     10.0, 1.005, 0.0005),
    ("ptw 30013",    "truebeam",  6.0,  1.003, 0.0005),
    ("ptw 30013",    "truebeam",  10.0, 1.006, 0.0005),
]

# Chamber aliases for P_rp lookup (maps variant names to canonical key)
_PRP_CHAMBER_ALIASES: dict[str, str] = {
    "standard imaging a12": "exradin a12",
    "si a12": "exradin a12",
    "a12": "exradin a12",
    "ptw30013": "ptw 30013",
    "ptw n30013": "ptw 30013",
}


# Typical published P_rp values by energy alone (conservative averages across linacs)
# Used as fallback when chamber/linac combination not in table
_FFF_PRP_ENERGY_DEFAULTS: dict[int, tuple[float, float]] = {
    6:  (1.003, 0.0005),
    10: (1.005, 0.0005),
}


def get_fff_prp(
    chamber_model: str,
    linac_model: str,
    energy_mv: float,
) -> tuple[float, float, str]:
    """
    Return (p_rp, uncertainty, source) for a FFF beam from published data.

    Tries an exact chamber+linac match first, then falls back to energy-based
    typical published values.

    Parameters
    ----------
    chamber_model : str   Ion chamber model (case-insensitive)
    linac_model   : str   Linac model string (case-insensitive, substring match)
    energy_mv     : float Nominal energy in MV (6 or 10 for FFF)

    Returns
    -------
    tuple (p_rp, uncertainty, source_label)

    References
    ----------
    Published 2024 peer-reviewed data for Elekta Versa HD and Varian TrueBeam.
    """
    ck = chamber_model.strip().lower()
    ck = _PRP_CHAMBER_ALIASES.get(ck, ck)
    lk = linac_model.strip().lower()
    e  = int(round(energy_mv))

    for (c_key, l_substr, e_mv, prp, unc) in _FFF_PRP_TABLE:
        if ck == c_key and l_substr in lk and int(e_mv) == e:
            return prp, unc, "published (chamber + linac specific)"

    # Fall back to energy-based typical value
    if e in _FFF_PRP_ENERGY_DEFAULTS:
        prp, unc = _FFF_PRP_ENERGY_DEFAULTS[e]
        return prp, unc, "published typical (energy-based)"

    return 1.000, 0.001, "no published data — measure site-specifically"


def list_photon_chambers() -> list[str]:
    return sorted(PHOTON_KQ_TABLE.keys())


def list_electron_chambers(chamber_type: str = "cylindrical") -> list[str]:
    if chamber_type == "cylindrical":
        return sorted(ELECTRON_KQECAL_CYL.keys())
    return sorted(ELECTRON_KQECAL_PP.keys())
