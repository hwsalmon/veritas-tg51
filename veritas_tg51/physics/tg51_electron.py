"""
tg51_electron.py — Electron beam TG-51 calculation engine.

Implements the 2024 WGTG51-e Addendum formalism (WGTG51 Report 385).

Key differences from 1999 TG-51:
  - No measured gradient correction P_gr^Q for cylindrical chambers.
    Gradient correction is included implicitly in MC-calculated k_Q factors.
  - Cylindrical chamber positioned with CENTRAL AXIS at d_ref (no EPOM shift
    for the reference dosimetry measurement itself).
  - EPOM shift is applied ONLY during PDI scanning to accurately find I_50 → R_50.
  - Updated k_Q = k'_Q * k_Qecal with new Monte Carlo-based data.
  - Cylindrical chambers can be used for ALL electron energies (4–22 MeV).

Calculation flow (Worksheet B equivalent, 2024 Addendum):
  1. R_50 from depth-ionization curve (I_50 converted via Eq. 3)
  2. Reference depth d_ref = 0.6*R_50 - 0.1 cm
  3. k_Qecal and k'_Q from Tables 4 & 5 (cylindrical) or 6 & 7 (PP)
  4. Environmental / measurement corrections
  5. Corrected reading M
  6. D_w^Q = M * k_Q * N_D,w^60Co   (k_Q = k'_Q * k_Qecal)
  7. Dose at d_max (optional)

References
----------
Almond PR et al. TG-51 (1999). Med. Phys. 26(9):1847–1870.
Muir BR et al. WGTG51 Report 385 (2024). Med. Phys. 51:5840–5857.
Muir BR et al. WGTG51 Report 374 (2022). Med. Phys. 49(9):6739–6764.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .chamber_data import get_electron_kq
from .corrections import (
    CorrectedReading,
    p_ion_pulsed,
    p_pol,
    p_tp,
)


# ---------------------------------------------------------------------------
# Beam quality helpers
# ---------------------------------------------------------------------------

def i50_to_r50(i50_cm: float) -> float:
    """
    Convert I_50 (depth of 50% ionization on depth-ionization curve) to R_50
    (depth of 50% absorbed dose on depth-dose curve).

    Parameters
    ----------
    i50_cm : float
        I_50 measured from depth-ionization curve, cm.
        For cylindrical chambers: shift depth-ionization curve upstream by
        EPOM (1.1 mm for A12) BEFORE finding I_50.

    Returns
    -------
    float
        R_50 in cm.

    Notes
    -----
    Valid range: 1.70 cm ≤ R_50 ≤ 8.70 cm (approximately 4–22 MeV).

    References
    ----------
    TG-51 (1999) Eqs. (16) and (17):
      R_50 = 1.029*I_50 - 0.06 cm   for 2 ≤ I_50 ≤ 10 cm
      R_50 = 1.059*I_50 - 0.37 cm   for I_50 > 10 cm
    WGTG51 Report 385 (2024) Eq. (3) — same formula, confirmed accurate.
    """
    if i50_cm < 1.7:
        raise ValueError(
            f"I_50 = {i50_cm:.3f} cm gives R_50 below 1.70 cm. "
            "The 2024 Addendum is not valid below ~4 MeV (R_50 < 1.70 cm)."
        )
    if i50_cm <= 10.0:
        r50 = 1.029 * i50_cm - 0.06
    else:
        r50 = 1.059 * i50_cm - 0.37
    return r50


def compute_d_ref(r50_cm: float) -> float:
    """
    Compute the electron beam reference depth for calibration.

    Parameters
    ----------
    r50_cm : float
        R_50 in cm.

    Returns
    -------
    float
        d_ref in cm (water equivalent).

    References
    ----------
    TG-51 (1999) Eq. (18): d_ref = 0.6*R_50 - 0.1 cm
    WGTG51 Report 385 (2024) Eq. (2): same formula.
    """
    return 0.6 * r50_cm - 0.1


# ---------------------------------------------------------------------------
# Main electron calibration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ElectronCalibrationInput:
    """
    All inputs required for a TG-51 electron beam calibration
    per the 2024 WGTG51-e Addendum formalism.
    """

    # Equipment
    chamber_model: str               # e.g. "Exradin A12"
    chamber_type: Literal["cylindrical", "parallel_plate"] = "cylindrical"
    n_dw_gy_per_c: float = 0.0       # N_D,w^60Co, Gy/C
    p_elec: float = 1.000            # Electrometer calibration factor

    # Environmental
    temperature_c: float = 22.0
    pressure_kpa: float = 101.33

    # Beam quality
    energy_mev: float = 9.0          # Nominal electron energy, MeV
    i50_cm: float = 0.0              # I_50 from depth-ionization curve (EPOM-corrected), cm

    # Raw readings at d_ref (nC or rdg)
    # IMPORTANT: For cylindrical chambers, the chamber CENTRAL AXIS is at d_ref.
    # Do NOT apply EPOM shift to the reference measurement position.
    m_raw_pos: float = 0.0           # M+_raw (positive bias)
    m_raw_neg: float = 0.0           # M-_raw (negative bias)
    calibration_polarity: Literal["pos", "neg"] = "pos"

    # Two-voltage ion recombination
    v_high: float = 300.0
    v_low: float = 150.0
    m_raw_high: float = 0.0
    m_raw_low: float = 0.0

    # Leakage correction (Report 374 §4.4.1) — leave at 0.0 to skip
    m_leak: float = 0.0

    # Jaffé plot override: if set, skip two-voltage P_ion and use this value directly
    p_ion_override: Optional[float] = None

    # Monitor units used for measurement
    monitor_units: float = 200.0

    # Setup
    ssd_cm: float = 100.0            # Source-to-surface distance, cm

    # Clinical PDD for d_max conversion (optional)
    # Use the clinical PDD curve (as used by TPS), not the depth-ionization curve
    clinical_pdd_at_dref_pct: Optional[float] = None  # %dd at d_ref


@dataclass
class ElectronCalibrationResult:
    """All intermediate and final results for a 2024-Addendum electron calibration."""

    # Beam quality
    r50_cm: float = 0.0
    d_ref_cm: float = 0.0

    # kQ components
    k_qecal: float = 0.0
    k_q_prime: float = 0.0
    k_q: float = 0.0

    # Corrections
    p_tp: float = 0.0
    p_pol: float = 0.0
    m_raw_ref: float = 0.0
    p_ion: float = 0.0
    p_elec: float = 1.000

    # Corrected reading
    m_corrected: float = 0.0

    # Dose results
    dose_dref_gy: float = 0.0
    dose_dref_cgy_per_mu: float = 0.0
    dose_dmax_cgy_per_mu: Optional[float] = None

    # Supporting
    n_dw_gy_per_c: float = 0.0
    monitor_units: float = 200.0

    p_leak: float = 1.000

    warnings: list[str] = field(default_factory=list)


def calculate_electron(inp: ElectronCalibrationInput) -> ElectronCalibrationResult:
    """
    Execute the full TG-51 electron beam calibration per the 2024 WGTG51-e Addendum.

    Parameters
    ----------
    inp : ElectronCalibrationInput
        All required measurement inputs.

    Returns
    -------
    ElectronCalibrationResult
        All intermediate correction factors and final dose result.

    Notes
    -----
    This function implements the SIMPLIFIED formalism of the 2024 Addendum where:
    - No measured gradient correction P_gr^Q is used (it is included in k_Q).
    - Cylindrical chambers are placed with their central axis at d_ref.
    - Results are expected to be ~1–2% higher than 1999 TG-51 for low energies.

    References
    ----------
    WGTG51 Report 385 (2024) Sec. 5.2, Eq. (4):
        D_w^Q = M * k_Q * N_D,w^60Co = M * k'_Q * k_Qecal * N_D,w^60Co
    """
    result = ElectronCalibrationResult()
    result.n_dw_gy_per_c = inp.n_dw_gy_per_c
    result.p_elec = inp.p_elec
    result.monitor_units = inp.monitor_units

    # --- Step 4: Beam quality R_50 and d_ref ---
    result.r50_cm = i50_to_r50(inp.i50_cm)
    result.d_ref_cm = compute_d_ref(result.r50_cm)

    # --- Step 5: k_Q = k'_Q * k_Qecal [2024 Addendum Eq. 4] ---
    kq_data = get_electron_kq(inp.chamber_model, result.r50_cm, inp.chamber_type)
    result.k_qecal = kq_data["k_qecal"]
    result.k_q_prime = kq_data["k_q_prime"]
    result.k_q = kq_data["k_q"]

    # --- Step 6: Temperature–pressure correction [TG-51 Eq. 10] ---
    result.p_tp = p_tp(inp.temperature_c, inp.pressure_kpa)

    # --- Step 7: Polarity correction [TG-51 Eq. 9] ---
    result.p_pol, result.m_raw_ref = p_pol(
        inp.m_raw_pos, inp.m_raw_neg, inp.calibration_polarity
    )

    # Electron beam polarity can be up to 2% — always measure
    pol_dev = abs(result.p_pol - 1.0)
    if pol_dev > 0.020:
        result.warnings.append(
            f"P_pol = {result.p_pol:.4f} (deviation {pol_dev*100:.2f}%) exceeds 2% in "
            "electron beam. The chamber may not meet reference-class specifications "
            "(2024 Addendum Appendix A, Table A1). Investigate."
        )
    elif pol_dev > 0.005:
        result.warnings.append(
            f"P_pol = {result.p_pol:.4f} (deviation {pol_dev*100:.2f}%) is notable in "
            "electron beam. Always measure polarity correction (never assume unity)."
        )

    # --- Step 8: Ion recombination [TG-51 Eq. 12] ---
    if inp.p_ion_override is not None:
        result.p_ion = float(inp.p_ion_override)
        result.warnings.append(
            f"P_ion = {result.p_ion:.4f} set from Jaffé plot (user override)."
        )
    else:
        result.p_ion = p_ion_pulsed(
            inp.v_high, inp.v_low, inp.m_raw_high, inp.m_raw_low
        )

    # --- Step 9: Corrected reading M [TG-51 Eq. 8 / 2024 Addendum Eq. 9] ---
    p_leak = 1.0
    if inp.m_leak != 0.0 and result.m_raw_ref != 0.0:
        p_leak = 1.0 - inp.m_leak / result.m_raw_ref
        if abs(p_leak - 1.0) > 0.001:
            result.warnings.append(
                f"P_leak = {p_leak:.4f}: leakage is "
                f"{abs(p_leak - 1.0) * 100:.2f}% of signal. "
                "Investigate leakage source if > 0.1% (Report 374 §4.4.1)."
            )
    result.p_leak = p_leak

    reading = CorrectedReading(
        m_raw=abs(result.m_raw_ref),   # always positive magnitude for dose calc
        p_ion=result.p_ion,
        p_tp=result.p_tp,
        p_elec=inp.p_elec,
        p_pol=result.p_pol,
        p_leak=p_leak,
    )
    result.m_corrected = reading.m_corrected

    # --- Step 10: Dose at d_ref [2024 Addendum Eq. 4] ---
    # D_w^Q = M * k_Q * N_D,w^60Co
    dose_dref_gy_total = result.m_corrected * result.k_q * inp.n_dw_gy_per_c
    result.dose_dref_gy = dose_dref_gy_total
    result.dose_dref_cgy_per_mu = (dose_dref_gy_total * 100.0) / inp.monitor_units

    # --- Step 11: Dose at d_max (optional) ---
    # Use clinical PDD curve as used by TPS (not depth-ionization curve)
    # D(d_max)/MU = D(d_ref)/MU / (%dd(d_ref)/100)
    if inp.clinical_pdd_at_dref_pct is not None and inp.clinical_pdd_at_dref_pct > 0:
        result.dose_dmax_cgy_per_mu = (
            result.dose_dref_cgy_per_mu / (inp.clinical_pdd_at_dref_pct / 100.0)
        )

    return result
