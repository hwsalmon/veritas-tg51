"""
corrections.py — TG-51 ion chamber correction factors.

Implements:
  P_TP   — Temperature–pressure correction     [TG-51 Eq. 10]
  P_pol  — Polarity correction                  [TG-51 Eq. 9]
  P_ion  — Ion recombination correction          [TG-51 Eqs. 11, 12]
  M      — Fully corrected reading               [TG-51 Eq. 8]

References
----------
Almond PR et al. AAPM's TG-51 protocol. Med. Phys. 1999;26(9):1847–1870.
Muir BR et al. AAPM WGTG51 Report 374. Med. Phys. 2022;49(9):6739–6764.
Muir BR et al. AAPM WGTG51 Report 385. Med. Phys. 2024;51:5840–5857.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# Standard environmental reference conditions (US/Canada)
T0_CELSIUS = 22.0     # Reference temperature, °C
P0_KPA = 101.33       # Reference pressure, kPa


def p_tp(temperature_c: float, pressure_kpa: float) -> float:
    """
    Temperature–pressure correction factor.

    Corrects the ion chamber reading to the standard environmental conditions
    (T0 = 22°C, P0 = 101.33 kPa) for which the N_D,w calibration factor applies.

    Parameters
    ----------
    temperature_c : float
        Temperature of the water near the ion chamber, °C.
        Should be the water temperature after thermal equilibrium is reached
        (typically 5–10 min after chamber insertion).
    pressure_kpa : float
        Ambient air pressure at the measurement altitude, kPa.
        Use uncorrected barometer reading (not sea-level corrected).

    Returns
    -------
    float
        P_TP correction factor.

    Notes
    -----
    For vented chambers, cavity air pressure equals ambient pressure.

    References
    ----------
    TG-51 (1999) Eq. (10):
        P_TP = ((273.2 + T) / (273.2 + T0)) * (P0 / P)
             = ((273.2 + T) / 295.2) * (101.33 / P)
    """
    if not (10.0 <= temperature_c <= 40.0):
        raise ValueError(f"Temperature {temperature_c}°C is outside expected range 10–40°C.")
    if not (85.0 <= pressure_kpa <= 110.0):
        raise ValueError(f"Pressure {pressure_kpa} kPa is outside expected range 85–110 kPa.")

    return ((273.2 + temperature_c) / (273.2 + T0_CELSIUS)) * (P0_KPA / pressure_kpa)


def p_pol(m_pos: float, m_neg: float, calibration_polarity: Literal["pos", "neg"] = "pos") -> tuple[float, float]:
    """
    Polarity correction factor.

    Takes readings at both bias polarities and computes the correction that
    accounts for any polarity-dependent response of the ion chamber.

    Parameters
    ----------
    m_pos : float
        Raw ion chamber reading with positive bias voltage (same sign as collecting charge).
    m_neg : float
        Raw ion chamber reading with negative bias voltage.
    calibration_polarity : str
        Polarity used during ADCL calibration: "pos" or "neg".
        The reading M_raw for subsequent correction is the one matching this polarity.

    Returns
    -------
    tuple[float, float]
        (P_pol, M_raw_ref) where M_raw_ref is the reading at the calibration polarity.

    Warnings
    --------
    If P_pol > 1.003 (0.3%) in a photon beam, the chamber behaviour should be investigated.
    For electron beams P_pol can be up to 2% — always measure, never assume unity.

    References
    ----------
    TG-51 (1999) Eq. (9):
        P_pol = (|M+_raw| + |M-_raw|) / (2 |M_raw|)
    Both readings are treated as positive magnitudes as displayed by the electrometer.
    The subtraction form (M+ - M-) is equivalent only when M- carries a negative sign.
    """
    if m_pos == 0.0 and m_neg == 0.0:
        raise ValueError("Both polarity readings are zero.")

    m_raw_ref = m_pos if calibration_polarity == "pos" else m_neg

    # TG-51 Eq. (9): P_pol = (|M+| + |M-|) / (2 |M_cal|)
    # Both readings are entered as positive magnitudes from the electrometer display,
    # so we sum the absolute values rather than subtract.
    p = (abs(m_pos) + abs(m_neg)) / (2.0 * abs(m_raw_ref))
    return p, m_raw_ref


def p_ion_pulsed(v_high: float, v_low: float,
                 m_high: float, m_low: float) -> float:
    """
    Ion recombination correction for pulsed (linac) and pulsed-swept beams.

    Uses the two-voltage linear saturation formula. Valid when P_ion ≤ 1.05
    (linear approximation holds within 0.4% for a voltage ratio of 3).

    Parameters
    ----------
    v_high : float
        Normal operating bias voltage V_H (always the higher magnitude), V.
    v_low : float
        Reduced bias voltage V_L (at least V_H/2), V.
    m_high : float
        Raw reading at V_H.
    m_low : float
        Raw reading at V_L.

    Returns
    -------
    float
        P_ion(V_H).

    Raises
    ------
    ValueError
        If P_ion > 1.05 (use a different chamber or a nonlinear solver).

    References
    ----------
    TG-51 (1999) Eq. (12) for pulsed/pulsed-swept beams:
        P_ion(V_H) = (1 - V_H/V_L) / (M^H_raw/M^L_raw - V_H/V_L)
    """
    ratio_v = v_high / v_low
    ratio_m = m_high / m_low

    denom = ratio_m - ratio_v
    if abs(denom) < 1e-10:
        raise ValueError("Voltage and reading ratios are equal — check two-voltage measurement.")

    p = (1.0 - ratio_v) / denom

    if p > 1.05:
        raise ValueError(
            f"P_ion = {p:.4f} > 1.05. Ion recombination is too large for the linear "
            "two-voltage approximation. Use a chamber with smaller recombination, "
            "or solve the nonlinear equations per TG-51 Sec. VII.D."
        )
    if p < 1.000:
        # Negative P_ion can occur with reversed voltage polarity convention — warn only
        pass

    return p


def p_ion_continuous(v_high: float, v_low: float,
                     m_high: float, m_low: float) -> float:
    """
    Ion recombination correction for continuous (e.g., 60Co) beams.

    Uses the two-voltage nonlinear saturation formula.

    Parameters
    ----------
    v_high, v_low : float
        Bias voltages (V_H > V_L), V.
    m_high, m_low : float
        Raw readings at V_H and V_L respectively.

    Returns
    -------
    float
        P_ion(V_H).

    References
    ----------
    TG-51 (1999) Eq. (11) for continuous beams:
        P_ion(V_H) = (1 - (V_H/V_L)^2) / (M^H_raw/M^L_raw - (V_H/V_L)^2)
    """
    ratio_v2 = (v_high / v_low) ** 2
    ratio_m = m_high / m_low

    denom = ratio_m - ratio_v2
    if abs(denom) < 1e-10:
        raise ValueError("Cannot compute P_ion: denominator is zero.")

    p = (1.0 - ratio_v2) / denom

    if p > 1.05:
        raise ValueError(
            f"P_ion = {p:.4f} > 1.05. Ion recombination correction is too large."
        )
    return p


@dataclass
class CorrectedReading:
    """Result of fully correcting a raw ion chamber reading per TG-51 Eq. (8)."""
    m_raw: float
    p_ion: float
    p_tp: float
    p_elec: float
    p_pol: float
    p_rp: float = 1.000   # Radial beam profile correction (WGTG51-X / Report 374 §4.5)
    p_leak: float = 1.000 # Leakage correction (Report 374 §4.4.1; typically 1.000)

    @property
    def m_corrected(self) -> float:
        """
        Fully corrected ion chamber reading M.

        M = P_ion * P_TP * P_elec * P_pol * P_rp * P_leak * M_raw   [TG-51 Eq. 8]

        References
        ----------
        TG-51 (1999) Eq. (8): M = P_ion * P_TP * P_elec * P_pol * M_raw
        WGTG51 Report 374 (2022) Eq. (2): adds P_leak and P_rp
        WGTG51 Report 385 (2024) Eq. (9): confirms same form for electrons
        """
        return (
            self.m_raw
            * self.p_ion
            * self.p_tp
            * self.p_elec
            * self.p_pol
            * self.p_rp
            * self.p_leak
        )

    def summary(self) -> dict:
        return {
            "M_raw": self.m_raw,
            "P_ion": self.p_ion,
            "P_TP": self.p_tp,
            "P_elec": self.p_elec,
            "P_pol": self.p_pol,
            "P_rp": self.p_rp,
            "P_leak": self.p_leak,
            "M_corrected": self.m_corrected,
        }


def mmhg_to_kpa(mmhg: float) -> float:
    """Convert pressure from mmHg to kPa. 1 atm = 101.33 kPa = 760.0 mmHg."""
    return mmhg * (101.33 / 760.0)


def inhg_to_kpa(inhg: float) -> float:
    """Convert pressure from inHg to kPa. 1 inHg = 3.38639 kPa."""
    return inhg * 3.38639
