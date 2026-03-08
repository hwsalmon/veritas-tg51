"""
electron_worksheet.py — TG-51 Electron Beam Calibration Worksheet

Implements the 2024 WGTG51-e Addendum formalism (WGTG51 Report 385).
Mirrors Worksheet B (cylindrical chambers) with updated k_Q procedure.

Key UI differences from 1999 protocol:
  - No P_gr^Q gradient correction input (eliminated in 2024 Addendum)
  - k_Q displayed as k'_Q × k_Qecal components
  - Prominent note that chamber axis is placed at d_ref (no EPOM shift for measurement)
  - EPOM shift reminder for PDI scanning phase only
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...physics.chamber_data import list_electron_chambers
from ...physics.corrections import mmhg_to_kpa
from ...physics.tg51_electron import ElectronCalibrationInput, calculate_electron
from ..widgets.form_widgets import DualFieldRow, FieldRow


class ElectronWorksheet(QWidget):
    """Full TG-51 Worksheet B — Electron Beam Calibration (2024 Addendum formalism)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._last_inp = None
        self._last_result = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #1B3A2A;")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(16, 10, 16, 10)
        lbl_title = QLabel(
            "TG-51 Worksheet B — Electron Beam Calibration  "
            "[2024 WGTG51-e Addendum Formalism]"
        )
        lbl_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        title_bar_layout.addWidget(lbl_title)
        title_bar_layout.addStretch()
        self.lbl_beam = QLabel("")
        self.lbl_beam.setStyleSheet("color: #7DCEA0; font-size: 13px; font-weight: bold;")
        title_bar_layout.addWidget(self.lbl_beam)
        outer.addWidget(title_bar)

        # Addendum notice banner
        notice = QLabel(
            "This worksheet uses the updated 2024 WGTG51-e Addendum (Report 385) formalism: "
            "k_Q = k'_Q × k_Qecal  with Monte Carlo-based data.  "
            "No measured gradient correction P_gr is required for cylindrical chambers.  "
            "Results are expected to be ~1–2% higher than the 1999 TG-51 protocol."
        )
        notice.setWordWrap(True)
        notice.setObjectName("infoNotice")
        outer.addWidget(notice)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(24, 16, 24, 24)
        self.main_layout.setSpacing(14)

        self._build_section_instrumentation()
        self._build_section_conditions()
        self._build_section_beam_quality()
        self._build_section_kq()
        self._build_section_corrections()
        self._build_section_corrected_reading()
        self._build_section_dose()
        self._build_warnings_panel()
        self._build_action_buttons()

        self.main_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _make_group(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        grp = QGroupBox(title)
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)
        lay.setContentsMargins(12, 16, 12, 12)
        return grp, lay

    # ------------------------------------------------------------------
    # Section: 2 — Instrumentation
    # ------------------------------------------------------------------

    def _build_section_instrumentation(self):
        grp, lay = self._make_group("2.  Instrumentation")
        form = QFormLayout()
        form.setSpacing(8)

        # Chamber type
        chamber_type_row = QHBoxLayout()
        self.rdo_cyl = QRadioButton("Cylindrical (preferred)")
        self.rdo_pp = QRadioButton("Parallel-plate")
        self.rdo_cyl.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self.rdo_cyl)
        bg.addButton(self.rdo_pp)
        self.rdo_cyl.toggled.connect(self._update_chamber_list)
        chamber_type_row.addWidget(self.rdo_cyl)
        chamber_type_row.addWidget(self.rdo_pp)
        chamber_type_row.addStretch()
        lay.addLayout(chamber_type_row)

        self.cmb_chamber = QComboBox()
        self._update_chamber_list()
        form.addRow("a. Chamber model:", self.cmb_chamber)

        self.txt_chamber_sn = QLineEdit()
        form.addRow("   Serial number:", self.txt_chamber_sn)

        self.spn_rcav = QDoubleSpinBox()
        self.spn_rcav.setRange(0.01, 1.0)
        self.spn_rcav.setDecimals(3)
        self.spn_rcav.setValue(0.305)
        self.spn_rcav.setSuffix(" cm")
        form.addRow("   Cavity inner radius (r_cav):", self.spn_rcav)

        self.spn_pelec = QDoubleSpinBox()
        self.spn_pelec.setRange(0.95, 1.05)
        self.spn_pelec.setDecimals(4)
        self.spn_pelec.setValue(1.0000)
        form.addRow("b. P_elec (Sec.VII.B):", self.spn_pelec)

        self.spn_ndw = QDoubleSpinBox()
        self.spn_ndw.setRange(1e6, 1e10)
        self.spn_ndw.setDecimals(4)
        self.spn_ndw.setValue(5.450e7)
        self.spn_ndw.setSuffix(" Gy/C")
        self.spn_ndw.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        form.addRow("c. Calibration factor N_D,w^60Co:", self.spn_ndw)

        lay.addLayout(form)
        self.main_layout.addWidget(grp)

    def _update_chamber_list(self):
        ctype = "cylindrical" if self.rdo_cyl.isChecked() else "parallel_plate"
        self.cmb_chamber.clear()
        chambers = list_electron_chambers(ctype)
        self.cmb_chamber.addItems([c.title() for c in chambers])
        # Default to A12 if cylindrical
        if ctype == "cylindrical":
            for i in range(self.cmb_chamber.count()):
                if "A12" in self.cmb_chamber.itemText(i):
                    self.cmb_chamber.setCurrentIndex(i)
                    break

    # ------------------------------------------------------------------
    # Section: 3 — Measurement Conditions
    # ------------------------------------------------------------------

    def _build_section_conditions(self):
        grp, lay = self._make_group(
            "3.  Measurement Conditions  (chamber central axis at d_ref)"
        )
        form = QFormLayout()
        form.setSpacing(8)

        self.spn_energy = QDoubleSpinBox()
        self.spn_energy.setRange(4.0, 22.0)
        self.spn_energy.setDecimals(0)
        self.spn_energy.setValue(9.0)
        self.spn_energy.setSuffix(" MeV")
        form.addRow("Nominal electron energy:", self.spn_energy)

        self.spn_ssd = QDoubleSpinBox()
        self.spn_ssd.setRange(90.0, 110.0)
        self.spn_ssd.setDecimals(1)
        self.spn_ssd.setValue(100.0)
        self.spn_ssd.setSuffix(" cm")
        form.addRow("a. SSD:", self.spn_ssd)

        self.spn_mu = QDoubleSpinBox()
        self.spn_mu.setRange(1, 10000)
        self.spn_mu.setDecimals(0)
        self.spn_mu.setValue(200)
        self.spn_mu.setSuffix(" MU")
        form.addRow("c. Monitor units:", self.spn_mu)

        lay.addLayout(form)

        # Position reminder
        pos_note = QLabel(
            "IMPORTANT (2024 Addendum): The cylindrical chamber central axis is positioned "
            "at d_ref for the reference dosimetry measurement.  Do NOT shift the chamber "
            "by EPOM for the measurement point — EPOM shift (1.1 mm for A12) is applied "
            "ONLY during PDI scanning to find I_50."
        )
        pos_note.setWordWrap(True)
        pos_note.setObjectName("posNote")
        lay.addWidget(pos_note)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 4 — Beam Quality R_50
    # ------------------------------------------------------------------

    def _build_section_beam_quality(self):
        grp, lay = self._make_group("4.  Beam Quality  (Sec. VIII.C)")

        epom_note = QLabel(
            "Measure I_50 from the depth-ionization curve with the cylindrical chamber "
            "EPOM shift applied (shift curve upstream by 1.1 mm for A12 before finding I_50). "
            "Then convert I_50 → R_50 using Eq. (3) below."
        )
        epom_note.setWordWrap(True)
        epom_note.setObjectName("dimLabel")
        lay.addWidget(epom_note)

        self.row_i50 = FieldRow(
            label="I_50  (from EPOM-corrected depth-ionization curve)",
            unit="cm",
            ref="Sec.VIII.C",
            step="4",
            decimals=3,
            value_min=1.5,
            value_max=12.0,
        )
        lay.addWidget(self.row_i50)

        self.row_r50 = FieldRow(
            label="R_50 = 1.029·I_50 − 0.06  (for 2 ≤ I_50 ≤ 10 cm)",
            unit="cm",
            ref="Eq.(3)/TG-51 Eq.(16)",
            read_only=True,
            decimals=3,
        )
        lay.addWidget(self.row_r50)

        self.row_dref = FieldRow(
            label="d_ref = 0.6·R_50 − 0.1",
            unit="cm",
            ref="Eq.(2)/TG-51 Eq.(18)",
            read_only=True,
            decimals=3,
        )
        lay.addWidget(self.row_dref)

        # Auto-calculate R50 and d_ref when I50 is entered
        self.row_i50.value_changed.connect(self._update_beam_quality)

        self.main_layout.addWidget(grp)

    def _update_beam_quality(self, i50: float):
        """Live-update R_50 and d_ref when I_50 is typed."""
        try:
            from ...physics.tg51_electron import i50_to_r50, compute_d_ref
            r50 = i50_to_r50(i50)
            dref = compute_d_ref(r50)
            self.row_r50.set_value(r50)
            self.row_dref.set_value(dref)
        except ValueError:
            self.row_r50.clear()
            self.row_dref.clear()

    # ------------------------------------------------------------------
    # Section: 5 — kQ Components
    # ------------------------------------------------------------------

    def _build_section_kq(self):
        grp, lay = self._make_group(
            "5.  Beam Quality Conversion  k_Q = k'_Q × k_Qecal  (2024 Addendum)"
        )

        self.row_kqecal = FieldRow(
            label="k_Qecal  [Table 4 or 6 — fixed for this chamber model]",
            unit="",
            ref="Table 4/6",
            step="5a",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_kqecal)

        self.row_kq_prime = FieldRow(
            label="k'_Q  [fit to R_50 — Table 5 (cyl) or Table 7 (PP)]",
            unit="",
            ref="Table 5/7, Eq.(7)/(8)",
            step="5b",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_kq_prime)

        self.row_kq = FieldRow(
            label="k_Q = k'_Q × k_Qecal",
            unit="",
            ref="Eq.(4)",
            step="5c",
            read_only=True,
            decimals=5,
        )
        lay.addWidget(self.row_kq)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 6–8 — Corrections
    # ------------------------------------------------------------------

    def _build_section_corrections(self):
        grp, lay = self._make_group("6–8.  Measurement Corrections")

        # 6. T/P
        tp_lbl = QLabel("6.  Temperature / Pressure Correction  (Sec. VII.C)")
        tp_lbl.setObjectName("subTitle")
        lay.addWidget(tp_lbl)

        tp_row = QHBoxLayout()
        tp_row.addWidget(QLabel("Temperature:"))
        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(10.0, 40.0)
        self.spn_temp.setDecimals(1)
        self.spn_temp.setValue(22.0)
        self.spn_temp.setSuffix(" °C")
        tp_row.addWidget(self.spn_temp)
        tp_row.addSpacing(20)

        tp_row.addWidget(QLabel("Pressure:"))
        self.spn_pressure = QDoubleSpinBox()
        self.spn_pressure.setRange(85.0, 110.0)
        self.spn_pressure.setDecimals(2)
        self.spn_pressure.setValue(101.33)
        self.spn_pressure.setSuffix(" kPa")
        tp_row.addWidget(self.spn_pressure)

        self.btn_mmhg = QPushButton("Enter mmHg")
        self.btn_mmhg.setObjectName("btnSecondary")
        self.btn_mmhg.setFixedWidth(100)
        self.btn_mmhg.clicked.connect(self._enter_pressure_mmhg)
        tp_row.addWidget(self.btn_mmhg)
        tp_row.addStretch()
        lay.addLayout(tp_row)

        self.row_ptp = FieldRow(
            label="P_TP", unit="", ref="Eq.(10)", step="6", read_only=True, decimals=5
        )
        lay.addWidget(self.row_ptp)

        # 7. Polarity
        pol_lbl = QLabel("7.  Polarity Correction  (Sec. VII.A)  — Always measure in electron beams")
        pol_lbl.setObjectName("subTitle")
        lay.addWidget(pol_lbl)

        self.row_mraw_pol = DualFieldRow(
            label="Raw readings at d_ref:",
            label_a="−300 V  M+raw =",
            label_b="  +300 V  M−raw =",
            unit="nC or rdg",
            ref="Eq.(9)",
        )
        lay.addWidget(self.row_mraw_pol)

        cal_pol_row = QHBoxLayout()
        cal_pol_row.addWidget(QLabel("   Operating voltage:"))
        self.rdo_calpos = QRadioButton("+300 V")
        self.rdo_calneg = QRadioButton("−300 V")
        self.rdo_calneg.setChecked(True)
        bg_pol = QButtonGroup(self)
        bg_pol.addButton(self.rdo_calpos)
        bg_pol.addButton(self.rdo_calneg)
        cal_pol_row.addWidget(self.rdo_calpos)
        cal_pol_row.addWidget(self.rdo_calneg)
        cal_pol_row.addStretch()
        lay.addLayout(cal_pol_row)

        self.row_ppol = FieldRow(
            label="P_pol  [up to 2% in electron beams — never assume unity]",
            unit="",
            ref="Eq.(9)",
            step="7",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_ppol)

        # 8. Ion recombination
        ion_lbl = QLabel("8.  Ion Recombination  P_ion  (Sec. VII.D.2, pulsed beam)")
        ion_lbl.setObjectName("subTitle")
        lay.addWidget(ion_lbl)

        volt_row = QHBoxLayout()
        volt_row.addWidget(QLabel("Operating voltage V_H:"))
        self.spn_vh = QDoubleSpinBox()
        self.spn_vh.setRange(50, 1000)
        self.spn_vh.setDecimals(0)
        self.spn_vh.setValue(300)
        self.spn_vh.setSuffix(" V")
        volt_row.addWidget(self.spn_vh)
        volt_row.addSpacing(20)
        volt_row.addWidget(QLabel("Lower voltage V_L:"))
        self.spn_vl = QDoubleSpinBox()
        self.spn_vl.setRange(25, 500)
        self.spn_vl.setDecimals(0)
        self.spn_vl.setValue(150)
        self.spn_vl.setSuffix(" V")
        volt_row.addWidget(self.spn_vl)
        volt_row.addStretch()
        lay.addLayout(volt_row)

        self.row_mraw_ion = DualFieldRow(
            label="Two-voltage readings at d_ref:",
            label_a="−300 V  M^H_raw =",
            label_b="  −150 V  M^L_raw =",
            unit="nC or rdg",
            ref="Eq.(12)",
        )
        lay.addWidget(self.row_mraw_ion)

        self.row_pion = FieldRow(
            label="P_ion(V_H)  [pulsed beam, Eq.(12)]",
            unit="",
            ref="Eq.(12)",
            step="8",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_pion)

        # Leakage (Report 374 §4.4.1)
        leak_lbl = QLabel("Leakage Correction  P_leak  (Report 374 §4.4.1)")
        leak_lbl.setObjectName("subTitle")
        lay.addWidget(leak_lbl)

        leak_row = QHBoxLayout()
        leak_row.addWidget(QLabel("   M_leak  (beam-off leakage reading, same units as M_raw):"))
        self.spn_mleak = QDoubleSpinBox()
        self.spn_mleak.setRange(-1e-5, 1e-5)
        self.spn_mleak.setDecimals(10)
        self.spn_mleak.setValue(0.0)
        self.spn_mleak.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.spn_mleak.setToolTip(
            "Leakage reading (beam off, same conditions). "
            "P_leak = 1 − M_leak/M_raw.  Leave 0.0 to skip (P_leak = 1.000)."
        )
        self.spn_mleak.valueChanged.connect(self._update_pleak_label)
        leak_row.addWidget(self.spn_mleak)
        self.lbl_pleak = QLabel("P_leak = 1.0000")
        self.lbl_pleak.setObjectName("dimLabel")
        leak_row.addWidget(self.lbl_pleak)
        leak_row.addStretch()
        lay.addLayout(leak_row)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 9 — Corrected reading
    # ------------------------------------------------------------------

    def _build_section_corrected_reading(self):
        grp, lay = self._make_group("9.  Corrected Ion Chamber Reading  M  (Sec. VII)")

        self.row_m_corrected = FieldRow(
            label="M = P_ion · P_TP · P_elec · P_pol · M_raw",
            unit="nC or rdg",
            ref="Eq.(9)/TG-51 Eq.(8)",
            step="9",
            read_only=True,
            decimals=5,
        )
        lay.addWidget(self.row_m_corrected)
        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 10–11 — Dose
    # ------------------------------------------------------------------

    def _build_section_dose(self):
        grp, lay = self._make_group("10–11.  Absorbed Dose to Water")

        self.row_dose_dref = FieldRow(
            label="D_w at d_ref  (reference depth)",
            unit="cGy/MU",
            ref="Eq.(4)",
            step="10",
            read_only=True,
            decimals=4,
        )
        self.row_dose_dref.field.setObjectName("resultFinal")
        lay.addWidget(self.row_dose_dref)

        # d_max conversion
        dmax_lbl = QLabel("11.  Dose at d_max  (clinical normalization depth)")
        dmax_lbl.setObjectName("subTitle")
        lay.addWidget(dmax_lbl)

        dmax_row = QHBoxLayout()
        dmax_row.addWidget(QLabel("Clinical %dd at d_ref (from TPS clinical PDD curve):"))
        self.spn_pdd_dref = QDoubleSpinBox()
        self.spn_pdd_dref.setRange(0.0, 120.0)
        self.spn_pdd_dref.setDecimals(2)
        self.spn_pdd_dref.setValue(0.0)
        self.spn_pdd_dref.setSuffix(" %")
        self.spn_pdd_dref.setToolTip(
            "Enter the clinical %dd at d_ref from the clinical PDD curve used by the TPS.\n"
            "Do NOT use the depth-ionization curve for this step.\n"
            "D(d_max)/MU = D(d_ref)/MU / (%dd(d_ref)/100)"
        )
        dmax_row.addWidget(self.spn_pdd_dref)
        dmax_row.addStretch()
        lay.addLayout(dmax_row)

        self.row_dose_dmax = FieldRow(
            label="D_w at d_max",
            unit="cGy/MU",
            ref="Step 11",
            step="11",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_dose_dmax)

        dmax_warn = QLabel(
            "Note: Failure to translate dose from d_ref to d_max is a common source of "
            "errors >8% in electron beam calibrations (Report 374 §2.4.3)."
        )
        dmax_warn.setWordWrap(True)
        dmax_warn.setObjectName("noteLabel")
        lay.addWidget(dmax_warn)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Warnings panel
    # ------------------------------------------------------------------

    def _build_warnings_panel(self):
        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setObjectName("warningLabel")
        self.lbl_warnings.setWordWrap(True)
        self.lbl_warnings.hide()
        self.main_layout.addWidget(self.lbl_warnings)

    # ------------------------------------------------------------------
    # Action buttons
    # ------------------------------------------------------------------

    def _build_action_buttons(self):
        btn_row = QHBoxLayout()

        self.btn_calculate = QPushButton("Calculate")
        self.btn_calculate.setObjectName("btnCalculate")
        self.btn_calculate.clicked.connect(self.calculate)

        self.btn_clear = QPushButton("Clear Results")
        self.btn_clear.setObjectName("btnSecondary")
        self.btn_clear.clicked.connect(self._clear_results)

        self.btn_save = QPushButton("Save to History")
        self.btn_save.setObjectName("btnSecondary")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_to_history)

        self.btn_report = QPushButton("Generate PDF Report")
        self.btn_report.setObjectName("btnSecondary")
        self.btn_report.clicked.connect(self._generate_report)

        btn_row.addWidget(self.btn_calculate)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_report)

        self.main_layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _update_pleak_label(self, m_leak: float):
        m_pos, _ = self.row_mraw_pol.get_values()
        if m_pos and m_pos != 0.0 and m_leak != 0.0:
            self.lbl_pleak.setText(f"P_leak = {1.0 - m_leak / m_pos:.4f}")
        else:
            self.lbl_pleak.setText("P_leak = 1.0000")

    def _enter_pressure_mmhg(self):
        from PySide6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getDouble(
            self, "Enter Pressure", "Pressure (mmHg):", 760.0, 500.0, 900.0, 1
        )
        if ok:
            self.spn_pressure.setValue(mmhg_to_kpa(val))

    def calculate(self):
        try:
            inp = self._gather_inputs()
            result = calculate_electron(inp)
            self._populate_results(result)
            self._last_inp = inp
            self._last_result = result
            self.btn_save.setEnabled(True)
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error:\n{e}")

    def _gather_inputs(self) -> ElectronCalibrationInput:
        m_pos, m_neg = self.row_mraw_pol.get_values()
        m_high, m_low = self.row_mraw_ion.get_values()
        i50 = self.row_i50.get_value()

        if m_pos is None or m_neg is None:
            raise ValueError("Both polarity readings (M+ and M-) are required.")
        if m_high is None or m_low is None:
            raise ValueError("Both two-voltage readings are required.")
        if i50 is None:
            raise ValueError("I_50 is required.")

        pdd_dref = self.spn_pdd_dref.value()

        return ElectronCalibrationInput(
            chamber_model=self.cmb_chamber.currentText().lower(),
            chamber_type="cylindrical" if self.rdo_cyl.isChecked() else "parallel_plate",
            n_dw_gy_per_c=self.spn_ndw.value(),
            p_elec=self.spn_pelec.value(),
            temperature_c=self.spn_temp.value(),
            pressure_kpa=self.spn_pressure.value(),
            energy_mev=self.spn_energy.value(),
            i50_cm=i50,
            m_raw_pos=m_pos,
            m_raw_neg=m_neg,
            calibration_polarity="neg" if self.rdo_calpos.isChecked() else "pos",
            v_high=self.spn_vh.value(),
            v_low=self.spn_vl.value(),
            m_raw_high=m_high,
            m_raw_low=m_low,
            m_leak=self.spn_mleak.value(),
            monitor_units=self.spn_mu.value(),
            ssd_cm=self.spn_ssd.value(),
            clinical_pdd_at_dref_pct=pdd_dref if pdd_dref > 0 else None,
        )

    def _populate_results(self, result):
        self.row_r50.set_value(result.r50_cm)
        self.row_dref.set_value(result.d_ref_cm)
        self.row_kqecal.set_value(result.k_qecal)
        self.row_kq_prime.set_value(result.k_q_prime)
        self.row_kq.set_value(result.k_q)
        self.row_ptp.set_value(result.p_tp)
        self.row_ppol.set_value(result.p_pol)
        self.row_pion.set_value(result.p_ion)
        self.row_m_corrected.set_value(result.m_corrected)
        self.row_dose_dref.set_value(result.dose_dref_cgy_per_mu, highlight_final=True)

        if result.dose_dmax_cgy_per_mu is not None:
            self.row_dose_dmax.set_value(result.dose_dmax_cgy_per_mu, highlight_final=True)

        if result.warnings:
            self.lbl_warnings.setText("⚠  " + "\n⚠  ".join(result.warnings))
            self.lbl_warnings.show()
        else:
            self.lbl_warnings.hide()

    def _clear_results(self):
        for row in [
            self.row_r50, self.row_dref, self.row_kqecal, self.row_kq_prime,
            self.row_kq, self.row_ptp, self.row_ppol, self.row_pion,
            self.row_m_corrected, self.row_dose_dref, self.row_dose_dmax,
        ]:
            row.clear()
        self.lbl_warnings.hide()
        self._last_inp = None
        self._last_result = None
        self.btn_save.setEnabled(False)

    def _save_to_history(self):
        """Persist last calculation result to the history database."""
        from ...models import db as db_mod
        if not db_mod.is_ready():
            QMessageBox.warning(self, "Database Unavailable",
                                "Database is not initialised. Cannot save.")
            return
        from PySide6.QtWidgets import QInputDialog
        physicist, ok = QInputDialog.getText(
            self, "Save to History", "Physicist name (optional):"
        )
        if not ok:
            return
        try:
            rec_id = db_mod.save_electron_record(
                self._last_inp, self._last_result, physicist=physicist
            )
            QMessageBox.information(self, "Saved",
                                    f"Record #{rec_id} saved to history.")
            self.btn_save.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _generate_report(self):
        try:
            inp = self._gather_inputs()
            result = calculate_electron(inp)
            from ...reports.pdf_generator import generate_electron_report
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", "TG51_Electron_Report.pdf", "PDF Files (*.pdf)"
            )
            if path:
                generate_electron_report(inp, result, path)
                QMessageBox.information(self, "Report Saved", f"Report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", str(e))
