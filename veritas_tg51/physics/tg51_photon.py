"""
tg51_photon.py — Photon beam TG-51 calculation engine.

Implements the complete Worksheet A calculation flow from the 1999 TG-51 protocol,
with updates from:
  - WGTG51-X Addendum (2014) for photon beam dosimetry / FFF beams
  - WGTG51 Report 374 (2022) practical guidance

Calculation flow:
  1. Beam quality specifier %dd(10)_x
  2. kQ from Table I (interpolated)
  3. Environmental / measurement corrections: P_TP, P_pol, P_ion, P_elec, [P_rp]
  4. Corrected reading M
  5. Dose at 10 cm: D_w = M * k_Q * N_D,w^60Co  [Eq. 3]
  6. Dose at d_max (optional)

References
----------
Almond PR et al. AAPM's TG-51 protocol. Med. Phys. 1999;26(9):1847–1870.
McEwen MR et al. Addendum to TG-51 (photon). Med. Phys. 2014;41:041501.
Muir BR et al. AAPM WGTG51 Report 374. Med. Phys. 2022;49(9):6739–6764.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .chamber_data import get_photon_kq
from .corrections import (
    CorrectedReading,
    p_ion_continuous,
    p_ion_pulsed,
    p_pol,
    p_tp,
)


# ---------------------------------------------------------------------------
# Beam quality specifier
# ---------------------------------------------------------------------------

def compute_pdd10x(
    pdd10_open: float,
    is_fff: bool = False,
) -> tuple[float, str]:
    """
    Determine %dd(10)_x — the photon beam quality specifier per the 2014 TG-51 Addendum.

    Per McEwen et al. (2014) Sec. 2.2–2.3, physical lead foil measurements are not
    required for standard flattened beams.  The algebraic correction (Eq. 15 of the
    1999 protocol) is applied when %dd(10) >= 75%, and introduces negligible additional
    uncertainty compared to the foil method.  For FFF beams, no electron-contamination
    correction is needed at all.

    Conditional logic
    -----------------
    1. FFF beam (any energy):
           %dd(10)_x = %dd(10)                                  (addendum Sec. 2.3)
    2. Flattened beam, %dd(10) < 75%:
           %dd(10)_x = %dd(10)    (negligible contamination)
    3. Flattened beam, %dd(10) >= 75%:
           %dd(10)_x = 1.267 × %dd(10) − 20.0                  (TG-51 1999 Eq. 15)

    Parameters
    ----------
    pdd10_open : float
        Measured open-field %dd(10) at 10 cm depth (EPOM-shifted upstream by 0.6*r_cav).
    is_fff : bool
        True for Flattening Filter Free beams.

    Returns
    -------
    tuple[float, str]
        (%dd(10)_x, method_string)

    References
    ----------
    Almond PR et al. TG-51 (1999) Med. Phys. 26(9):1847-1870.  Eq. 15.
    McEwen MR et al. TG-51 Addendum (2014) Med. Phys. 41(4):041501.  Sec. 2.2-2.3.
    """
    if pdd10_open is None:
        raise ValueError("pdd10_open is required to determine %dd(10)_x.")

    if is_fff:
        # FFF beams: no electron contamination present (addendum Sec. 2.3)
        return pdd10_open, "fff_direct"

    if pdd10_open < 75.0:
        # Low-energy / low-pdd flattened beam: contamination negligible
        return pdd10_open, "open_direct"

    # High-energy flattened beam: apply algebraic correction (TG-51 1999 Eq. 15)
    pdd10x = 1.267 * pdd10_open - 20.0
    return pdd10x, "addendum_eq15"


# ---------------------------------------------------------------------------
# Main photon calibration dataclass
# ---------------------------------------------------------------------------

@dataclass
class PhotonCalibrationInput:
    """All inputs required for a TG-51 photon beam calibration (Worksheet A)."""

    # Equipment
    chamber_model: str          # e.g. "Exradin A12"
    n_dw_gy_per_c: float        # N_D,w^60Co, Gy/C
    p_elec: float = 1.000       # Electrometer calibration factor

    # Environmental
    temperature_c: float = 22.0
    pressure_kpa: float = 101.33

    # Beam quality
    energy_mv: float = 6.0
    is_fff: bool = False
    pdd10_open: Optional[float] = None   # measured open-field %dd(10)

    # Raw readings (nC or rdg) — at reference depth 10 cm, 10x10 cm², SSD/SAD 100 cm
    m_raw_pos: float = 0.0      # M+_raw (positive bias, matching calibration polarity)
    m_raw_neg: float = 0.0      # M-_raw (negative bias)
    calibration_polarity: Literal["pos", "neg"] = "pos"

    # Two-voltage ion recombination
    v_high: float = 300.0       # V_H (normal operating voltage), V
    v_low: float = 150.0        # V_L (reduced voltage, at least V_H/2), V
    m_raw_high: float = 0.0     # Reading at V_H
    m_raw_low: float = 0.0      # Reading at V_L

    # FFF correction
    p_rp: float = 1.000         # Radial beam profile correction (measure with film or scanner)

    # Leakage correction (Report 374 §4.4.1)
    # Enter the leakage reading at the same bias and setup conditions but beam off.
    # Units must match m_raw_pos (i.e. Coulombs if m_raw is in C).
    # Leave at 0.0 to skip (P_leak = 1.000).
    m_leak: float = 0.0

    # Jaffé plot override: if set, skip two-voltage P_ion and use this value directly
    p_ion_override: Optional[float] = None

    # Monitor units used for measurement
    monitor_units: float = 200.0

    # Setup
    setup_type: Literal["SSD", "SAD"] = "SAD"
    ssd_or_sad_cm: float = 100.0

    # Clinical depth-dose for d_max conversion (optional)
    clinical_pdd_pct: Optional[float] = None   # %dd at d_max for SSD
    clinical_tmr: Optional[float] = None        # TMR(10, 10x10) for SAD


@dataclass
class PhotonCalibrationResult:
    """All intermediate and final results for a TG-51 photon calibration."""

    # Step 4 — Beam quality
    pdd10x: float = 0.0
    pdd10x_method: str = ""

    # Step 5 — kQ
    k_q: float = 0.0

    # Step 6 — Environmental
    p_tp: float = 0.0

    # Step 7 — Polarity
    m_raw_ref: float = 0.0
    p_pol: float = 0.0

    # Step 8 — Ion recombination
    p_ion: float = 0.0

    # Step 9 — Corrected reading
    m_corrected: float = 0.0

    # Step 10 — Dose at 10 cm
    dose_10cm_gy: float = 0.0
    dose_10cm_cgy_per_mu: float = 0.0

    # Step 11 — Dose at d_max (optional)
    dose_dmax_cgy_per_mu: Optional[float] = None

    # Supporting values
    p_elec: float = 1.000
    p_rp: float = 1.000
    n_dw_gy_per_c: float = 0.0
    monitor_units: float = 200.0

    # Leakage correction
    p_leak: float = 1.000

    # Warnings
    warnings: list[str] = field(default_factory=list)


def calculate_photon(inp: PhotonCalibrationInput) -> PhotonCalibrationResult:
    """
    Execute the full TG-51 photon beam calibration calculation (Worksheet A).

    Parameters
    ----------
    inp : PhotonCalibrationInput
        All required measurement inputs.

    Returns
    -------
    PhotonCalibrationResult
        All intermediate correction factors and final dose result.

    References
    ----------
    TG-51 (1999) Worksheet A steps 1–11.
    Core equation — Eq. (3): D_w^Q = M * k_Q * N_D,w^60Co
    """
    result = PhotonCalibrationResult()
    result.n_dw_gy_per_c = inp.n_dw_gy_per_c
    result.p_elec = inp.p_elec
    result.p_rp = inp.p_rp
    result.monitor_units = inp.monitor_units

    # --- Step 4: Beam quality %dd(10)_x ---
    # Per 2014 TG-51 Addendum (McEwen et al., Med. Phys. 41:041501):
    # Physical lead foil measurement not required; algebraic formula applied conditionally.
    result.pdd10x, result.pdd10x_method = compute_pdd10x(
        pdd10_open=inp.pdd10_open,
        is_fff=inp.is_fff,
    )


    # --- Step 5: k_Q ---
    result.k_q = get_photon_kq(inp.chamber_model, result.pdd10x)

    # --- Step 6: Temperature–pressure correction ---
    result.p_tp = p_tp(inp.temperature_c, inp.pressure_kpa)

    # --- Step 7: Polarity correction ---
    result.p_pol, result.m_raw_ref = p_pol(
        inp.m_raw_pos, inp.m_raw_neg, inp.calibration_polarity
    )
    if abs(result.p_pol - 1.0) > 0.003:
        result.warnings.append(
            f"P_pol = {result.p_pol:.4f} (deviation {abs(result.p_pol - 1.0)*100:.2f}%) "
            "exceeds 0.3% threshold for photon beams. Investigate chamber/cable connections."
        )

    # --- Step 8: Ion recombination ---
    if inp.p_ion_override is not None:
        # Jaffé plot result supplied directly by user
        result.p_ion = float(inp.p_ion_override)
        result.warnings.append(
            f"P_ion = {result.p_ion:.4f} set from Jaffé plot (user override). "
            "Two-voltage inputs were not used for P_ion."
        )
    else:
        # All linac beams are pulsed → use Eq. (12)
        result.p_ion = p_ion_pulsed(
            inp.v_high, inp.v_low, inp.m_raw_high, inp.m_raw_low
        )

    if inp.is_fff and result.p_ion > 1.010:
        result.warnings.append(
            f"FFF beam: P_ion = {result.p_ion:.4f} is elevated. "
            "Verify with Jaffé plot (Report 374 §4.4.4). "
            "FFF beams can have P_ion up to 2%."
        )

    # --- Step 9: Corrected reading M — Eq. (8) + Report 374 §4.4.1 (P_leak) ---
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
        p_rp=inp.p_rp,
        p_leak=p_leak,
    )
    result.m_corrected = reading.m_corrected

    # --- Step 10: Dose at 10 cm — Eq. (3) ---
    # D_w^Q = M * k_Q * N_D,w^60Co
    dose_10cm_total_gy = result.m_corrected * result.k_q * inp.n_dw_gy_per_c
    result.dose_10cm_gy = dose_10cm_total_gy
    result.dose_10cm_cgy_per_mu = (dose_10cm_total_gy * 100.0) / inp.monitor_units

    # --- Step 11: Dose at d_max (optional) ---
    if inp.setup_type == "SSD" and inp.clinical_pdd_pct is not None:
        # D(d_max) = D(10cm) / (%dd(10)/100)
        if inp.clinical_pdd_pct > 0:
            result.dose_dmax_cgy_per_mu = (
                result.dose_10cm_cgy_per_mu / (inp.clinical_pdd_pct / 100.0)
            )
    elif inp.setup_type == "SAD" and inp.clinical_tmr is not None:
        # D(d_max) = D(10cm) / TMR(10, 10x10)
        if inp.clinical_tmr > 0:
            result.dose_dmax_cgy_per_mu = (
                result.dose_10cm_cgy_per_mu / inp.clinical_tmr
            )

    return result
