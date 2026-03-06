"""
test_physics.py — Unit tests for TG-51 physics engine.

Validates all correction factors and dose calculations against
known analytical values and published TG-51 example data.
"""

import math
import pytest

from veritas_tg51.physics.corrections import (
    p_tp, p_pol, p_ion_pulsed, p_ion_continuous, mmhg_to_kpa
)
from veritas_tg51.physics.chamber_data import get_photon_kq, get_electron_kq
from veritas_tg51.physics.tg51_photon import (
    compute_pdd10x, PhotonCalibrationInput, calculate_photon
)
from veritas_tg51.physics.tg51_electron import (
    i50_to_r50, compute_d_ref, ElectronCalibrationInput, calculate_electron
)


# ---------------------------------------------------------------------------
# Corrections
# ---------------------------------------------------------------------------

class TestPTP:
    def test_standard_conditions(self):
        """At standard T=22°C, P=101.33 kPa: P_TP = 1.000"""
        assert abs(p_tp(22.0, 101.33) - 1.000) < 1e-5

    def test_higher_temp(self):
        """Higher T → higher P_TP (corrects upward)."""
        assert p_tp(25.0, 101.33) > 1.000

    def test_higher_pressure(self):
        """Higher P → lower P_TP."""
        assert p_tp(22.0, 103.0) < 1.000

    def test_formula(self):
        """Verify Eq.(10) numerically: P_TP = (273.2+T)/295.2 * 101.33/P"""
        T, P = 23.5, 100.0
        expected = ((273.2 + T) / 295.2) * (101.33 / P)
        assert abs(p_tp(T, P) - expected) < 1e-8

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            p_tp(5.0, 101.33)   # Too cold
        with pytest.raises(ValueError):
            p_tp(22.0, 50.0)    # Unrealistic pressure


class TestPPol:
    def test_no_polarity_effect(self):
        """Identical magnitude readings → P_pol = 1.0 (no correction needed)."""
        ppol, m_ref = p_pol(100.0, -100.0, "pos")
        assert abs(ppol - 1.0) < 1e-10

    def test_small_polarity(self):
        """Small asymmetry."""
        ppol, m_ref = p_pol(100.2, -99.8, "pos")
        expected = abs((100.2 - (-99.8)) / (2 * 100.2))
        assert abs(ppol - expected) < 1e-8
        assert m_ref == 100.2

    def test_negative_polarity_selected(self):
        ppol, m_ref = p_pol(100.0, -98.0, "neg")
        assert m_ref == -98.0


class TestPIon:
    def test_unity_readings(self):
        """If readings scale perfectly with voltage, P_ion is determined by ratio."""
        # Perfect collection: M_H/M_L = V_H/V_L → P_ion = 1 by definition is not
        # exactly 1 in this formula; test the formula directly
        vh, vl = 300.0, 150.0
        # Simulate: M_H/M_L slightly > V_H/V_L (normal)
        mh, ml = 1.010, 0.990
        p = p_ion_pulsed(vh, vl, mh, ml)
        assert 1.000 < p < 1.05

    def test_pulsed_formula(self):
        """Verify Eq.(12): P_ion = (1 - VH/VL)/(MH/ML - VH/VL)"""
        vh, vl, mh, ml = 300.0, 150.0, 1.005, 0.995
        expected = (1.0 - vh / vl) / (mh / ml - vh / vl)
        assert abs(p_ion_pulsed(vh, vl, mh, ml) - expected) < 1e-8

    def test_too_large_raises(self):
        """P_ion > 1.05 should raise.  VH/VL=2, MH/ML=1.1 → P_ion≈1.11."""
        with pytest.raises(ValueError, match="1.05"):
            p_ion_pulsed(300, 150, 1.1, 1.0)

    def test_continuous(self):
        """Continuous beam uses squared ratio — Eq.(11)."""
        vh, vl = 300.0, 150.0
        mh, ml = 1.004, 0.997
        p = p_ion_continuous(vh, vl, mh, ml)
        expected = (1.0 - (vh / vl) ** 2) / (mh / ml - (vh / vl) ** 2)
        assert abs(p - expected) < 1e-8

    def test_mmhg_conversion(self):
        """760 mmHg = 101.33 kPa."""
        assert abs(mmhg_to_kpa(760.0) - 101.33) < 0.01


# ---------------------------------------------------------------------------
# Chamber data / kQ
# ---------------------------------------------------------------------------

class TestPhotonKQ:
    def test_a12_at_71(self):
        """A12 kQ at %dd(10)_x = 71.0% should be 0.990 per TG-51 Table I."""
        kq = get_photon_kq("Exradin A12", 71.0)
        assert abs(kq - 0.990) < 1e-3

    def test_a12_at_66(self):
        assert abs(get_photon_kq("exradin a12", 66.0) - 0.996) < 1e-3

    def test_a12_at_81(self):
        assert abs(get_photon_kq("exradin a12", 81.0) - 0.972) < 1e-3

    def test_interpolation(self):
        """Interpolated value at 68.5% (midpoint of 66–71) ≈ midpoint of kQ values."""
        kq_66 = get_photon_kq("exradin a12", 66.0)
        kq_71 = get_photon_kq("exradin a12", 71.0)
        kq_mid = get_photon_kq("exradin a12", 68.5)
        expected_mid = (kq_66 + kq_71) / 2
        assert abs(kq_mid - expected_mid) < 0.0005

    def test_unknown_chamber(self):
        with pytest.raises(ValueError, match="not in photon kQ table"):
            get_photon_kq("Unknown Chamber XYZ", 71.0)

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            get_photon_kq("exradin a12", 30.0)


class TestElectronKQ:
    def test_a12_kqecal(self):
        """A12 k_Qecal = 0.907 per 2024 Addendum Table 4."""
        result = get_electron_kq("Exradin A12", 4.0, "cylindrical")
        assert abs(result["k_qecal"] - 0.907) < 1e-4

    def test_a12_kq_at_r50_4(self):
        """
        A12 k'_Q at R_50 = 4.0 cm:
        k'_Q = 0.965 + 0.119 * 4.0^0.607
        k_Q = k'_Q * 0.907
        """
        r50 = 4.0
        a0, b0, c0 = 0.965, 0.119, 0.607
        expected_kq_prime = a0 + b0 * (r50 ** c0)
        expected_kq = expected_kq_prime * 0.907
        result = get_electron_kq("exradin a12", r50, "cylindrical")
        assert abs(result["k_q_prime"] - expected_kq_prime) < 1e-5
        assert abs(result["k_q"] - expected_kq) < 1e-5

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="R_50"):
            get_electron_kq("exradin a12", 9.5, "cylindrical")

    def test_parallel_plate_roos(self):
        result = get_electron_kq("PTW Roos", 4.0, "parallel_plate")
        assert abs(result["k_qecal"] - 0.898) < 1e-4


# ---------------------------------------------------------------------------
# Beam quality helpers
# ---------------------------------------------------------------------------

class TestBeamQuality:
    def test_pdd10x_open_low_energy(self):
        pdd, method = compute_pdd10x(pdd10_open=66.5, energy_mv=6.0)
        assert abs(pdd - 66.5) < 1e-5
        assert method == "open_beam"

    def test_pdd10x_foil50(self):
        """Eq.(13): foil at 50 cm."""
        pdd_pb = 75.0
        pdd, method = compute_pdd10x(pdd10_pb=pdd_pb, pb_foil_distance_cm=50.0, energy_mv=15.0)
        expected = (0.8905 + 0.00150 * pdd_pb) * pdd_pb
        assert abs(pdd - expected) < 1e-5
        assert method == "foil50"

    def test_pdd10x_foil30(self):
        """Eq.(14): foil at 30 cm."""
        pdd_pb = 73.0
        pdd, method = compute_pdd10x(pdd10_pb=pdd_pb, pb_foil_distance_cm=30.0, energy_mv=10.0)
        expected = (0.8116 + 0.00264 * pdd_pb) * pdd_pb
        assert abs(pdd - expected) < 1e-5
        assert method == "foil30"

    def test_pdd10x_interim(self):
        """Eq.(15): interim, no foil."""
        pdd_open = 80.0
        pdd, method = compute_pdd10x(
            pdd10_open=pdd_open, energy_mv=10.0, use_interim=True
        )
        expected = 1.267 * pdd_open - 20.0
        assert abs(pdd - expected) < 1e-5
        assert method == "interim_no_foil"

    def test_i50_to_r50_low(self):
        """R_50 = 1.029*I_50 - 0.06 for I_50 <= 10."""
        i50 = 4.0
        r50 = i50_to_r50(i50)
        assert abs(r50 - (1.029 * i50 - 0.06)) < 1e-5

    def test_i50_to_r50_high(self):
        """R_50 = 1.059*I_50 - 0.37 for I_50 > 10."""
        i50 = 10.5
        r50 = i50_to_r50(i50)
        assert abs(r50 - (1.059 * i50 - 0.37)) < 1e-5

    def test_dref(self):
        """d_ref = 0.6*R_50 - 0.1."""
        r50 = 5.0
        assert abs(compute_d_ref(r50) - (0.6 * r50 - 0.1)) < 1e-8


# ---------------------------------------------------------------------------
# Full calculation integration tests
# ---------------------------------------------------------------------------

class TestPhotonCalculation:
    def _standard_input(self) -> PhotonCalibrationInput:
        # m_raw values in Coulombs (~37 nC typical for A12 in 6 MV, 200 MU, 10 cm)
        return PhotonCalibrationInput(
            chamber_model="exradin a12",
            n_dw_gy_per_c=5.450e7,
            p_elec=1.0000,
            temperature_c=22.0,
            pressure_kpa=101.33,
            energy_mv=6.0,
            is_fff=False,
            pdd10_open=66.4,
            m_raw_pos=3.700e-8,
            m_raw_neg=-3.680e-8,
            v_high=300.0,
            v_low=150.0,
            m_raw_high=3.700e-8,
            m_raw_low=3.680e-8,
            p_rp=1.0000,
            monitor_units=200.0,
            setup_type="SAD",
        )

    def test_dose_is_near_1cgy_per_mu(self):
        """A calibrated beam should yield ≈ 0.95–1.05 cGy/MU."""
        result = calculate_photon(self._standard_input())
        assert 0.90 <= result.dose_10cm_cgy_per_mu <= 1.10

    def test_ptp_at_standard_conditions(self):
        """At T=22°C, P=101.33 kPa, P_TP ≈ 1.000."""
        result = calculate_photon(self._standard_input())
        assert abs(result.p_tp - 1.000) < 1e-4

    def test_kq_for_6mv(self):
        """6 MV beam (%dd(10)_x ≈ 66.4%) → k_Q should be near 0.996."""
        result = calculate_photon(self._standard_input())
        assert 0.994 <= result.k_q <= 0.998


class TestElectronCalculation:
    def _standard_input(self) -> ElectronCalibrationInput:
        # m_raw values in Coulombs (~33 nC typical for A12 in 9 MeV, 200 MU, at d_ref)
        return ElectronCalibrationInput(
            chamber_model="exradin a12",
            chamber_type="cylindrical",
            n_dw_gy_per_c=5.450e7,
            p_elec=1.0000,
            temperature_c=22.0,
            pressure_kpa=101.33,
            energy_mev=9.0,
            i50_cm=3.8,   # Typical 9 MeV
            m_raw_pos=3.300e-8,
            m_raw_neg=-3.270e-8,
            v_high=300.0,
            v_low=150.0,
            m_raw_high=3.300e-8,
            m_raw_low=3.270e-8,
            monitor_units=200.0,
            ssd_cm=100.0,
        )

    def test_r50_computed(self):
        result = calculate_electron(self._standard_input())
        expected_r50 = 1.029 * 3.8 - 0.06
        assert abs(result.r50_cm - expected_r50) < 1e-4

    def test_dref_computed(self):
        result = calculate_electron(self._standard_input())
        assert abs(result.d_ref_cm - (0.6 * result.r50_cm - 0.1)) < 1e-4

    def test_kqecal(self):
        result = calculate_electron(self._standard_input())
        assert abs(result.k_qecal - 0.907) < 1e-4

    def test_dose_reasonable(self):
        result = calculate_electron(self._standard_input())
        assert 0.80 <= result.dose_dref_cgy_per_mu <= 1.20
