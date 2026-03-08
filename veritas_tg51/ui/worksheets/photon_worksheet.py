"""
photon_worksheet.py — TG-51 Worksheet A: Photon Beams

Mirrors the layout and step numbering of the official TG-51 Worksheet A
(Almond et al. 1999, pages 1861–1862), with extensions for FFF beams.

Steps:
  1.  Site data (header — handled by main window)
  2.  Instrumentation
  3.  Measurement conditions
  4.  Beam quality %dd(10)_x
  5.  k_Q
  6.  Temperature / pressure correction P_TP
  7.  Polarity correction P_pol
  8.  Ion recombination P_ion
  9.  Corrected reading M
  10. Dose at 10 cm reference depth
  11. Dose at d_max
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...physics.chamber_data import list_photon_chambers
from ...physics.corrections import mmhg_to_kpa
from ...physics.tg51_photon import PhotonCalibrationInput, calculate_photon
from ..widgets.form_widgets import DualFieldRow, FieldRow


class PhotonWorksheet(QWidget):
    """Full TG-51 Worksheet A for photon beam calibration."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._last_inp = None
        self._last_result = None
        self._p_ion_override: Optional[float] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #1B2A4A;")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(16, 10, 16, 10)
        lbl_title = QLabel("TG-51 Worksheet A — Photon Beam Calibration")
        lbl_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        title_bar_layout.addWidget(lbl_title)
        title_bar_layout.addStretch()
        self.lbl_beam = QLabel("")
        self.lbl_beam.setStyleSheet("color: #7FB3D3; font-size: 13px; font-weight: bold;")
        title_bar_layout.addWidget(self.lbl_beam)
        outer.addWidget(title_bar)

        # Scrollable worksheet area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("")

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

        # Chamber
        form = QFormLayout()
        form.setSpacing(8)

        self.cmb_chamber = QComboBox()
        self.cmb_chamber.addItems(
            [m.title() for m in list_photon_chambers()]
        )
        # Default to A12
        idx = self.cmb_chamber.findText("Exradin A12", Qt.MatchFixedString | Qt.MatchCaseSensitive)
        if idx < 0:
            idx = self.cmb_chamber.findText("exradin a12", Qt.MatchContains | Qt.MatchCaseSensitive)
        self.cmb_chamber.setCurrentIndex(max(0, idx))
        form.addRow("a. Chamber model:", self.cmb_chamber)

        self.txt_chamber_sn = QLineEdit()
        self.txt_chamber_sn.setPlaceholderText("e.g. A12-12345")
        form.addRow("   Serial number:", self.txt_chamber_sn)

        self.spn_rcav = QDoubleSpinBox()
        self.spn_rcav.setRange(0.01, 1.0)
        self.spn_rcav.setDecimals(3)
        self.spn_rcav.setValue(0.305)  # A12 default
        self.spn_rcav.setSuffix(" cm")
        form.addRow("   Cavity inner radius (r_cav):", self.spn_rcav)

        self.txt_elec_model = QLineEdit()
        self.txt_elec_model.setPlaceholderText("e.g. MAX-ELITE")
        form.addRow("b. Electrometer model:", self.txt_elec_model)

        self.txt_elec_sn = QLineEdit()
        form.addRow("   Serial number:", self.txt_elec_sn)

        self.spn_pelec = QDoubleSpinBox()
        self.spn_pelec.setRange(0.95, 1.05)
        self.spn_pelec.setDecimals(4)
        self.spn_pelec.setValue(1.0000)
        self.spn_pelec.setToolTip(
            "P_elec = 1.0000 if electrometer and chamber calibrated as a unit.\n"
            "Otherwise enter the electrometer calibration factor from the ADCL certificate."
        )
        form.addRow("   P_elec (Sec.VII.B):", self.spn_pelec)

        self.spn_ndw = QDoubleSpinBox()
        self.spn_ndw.setRange(1e6, 1e10)
        self.spn_ndw.setDecimals(4)
        self.spn_ndw.setValue(5.450e7)   # Typical A12 value
        self.spn_ndw.setSuffix(" Gy/C")
        self.spn_ndw.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        form.addRow("c. Calibration factor N_D,w^60Co:", self.spn_ndw)

        lay.addLayout(form)
        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 3 — Measurement Conditions
    # ------------------------------------------------------------------

    def _build_section_conditions(self):
        grp, lay = self._make_group(
            "3.  Measurement Conditions  (10×10 cm², point of measurement at 10 cm depth)"
        )
        form = QFormLayout()
        form.setSpacing(8)

        # SSD or SAD
        setup_row = QHBoxLayout()
        self.rdo_sad = QRadioButton("SAD")
        self.rdo_ssd = QRadioButton("SSD")
        self.rdo_sad.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self.rdo_sad)
        bg.addButton(self.rdo_ssd)
        setup_row.addWidget(QLabel("a. Setup:"))
        setup_row.addWidget(self.rdo_sad)
        setup_row.addWidget(self.rdo_ssd)
        setup_row.addStretch()
        lay.addLayout(setup_row)

        self.spn_distance = QDoubleSpinBox()
        self.spn_distance.setRange(80.0, 120.0)
        self.spn_distance.setDecimals(1)
        self.spn_distance.setValue(100.0)
        self.spn_distance.setSuffix(" cm")
        form.addRow("   SSD or SAD:", self.spn_distance)

        self.spn_mu = QDoubleSpinBox()
        self.spn_mu.setRange(1, 10000)
        self.spn_mu.setDecimals(0)
        self.spn_mu.setValue(200)
        self.spn_mu.setSuffix(" MU")
        form.addRow("c. Monitor units:", self.spn_mu)

        # FFF checkbox
        self.chk_fff = QCheckBox("FFF (Flattening-Filter-Free) beam")
        self.chk_fff.setToolTip(
            "FFF beams require lead foil for %dd(10)_x and P_rp correction."
        )
        lay.addLayout(form)
        lay.addWidget(self.chk_fff)
        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 4 — Beam Quality %dd(10)_x
    # ------------------------------------------------------------------

    def _build_section_beam_quality(self):
        grp, lay = self._make_group("4.  Beam Quality  (Sec. VIII.B)")

        # Energy
        energy_row = QHBoxLayout()
        energy_row.addWidget(QLabel("Nominal energy:"))
        self.spn_energy = QDoubleSpinBox()
        self.spn_energy.setRange(4.0, 50.0)
        self.spn_energy.setDecimals(0)
        self.spn_energy.setValue(6.0)
        self.spn_energy.setSuffix(" MV")
        energy_row.addWidget(self.spn_energy)
        energy_row.addStretch()
        lay.addLayout(energy_row)

        # Method selection
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Method:"))
        self.rdo_open = QRadioButton("Open beam (<10 MV)")
        self.rdo_foil50 = QRadioButton("Lead foil at 50 cm")
        self.rdo_foil30 = QRadioButton("Lead foil at 30 cm")
        self.rdo_interim = QRadioButton("Interim (no foil, Eq.15)")
        self.rdo_foil50.setChecked(True)
        bg_q = QButtonGroup(self)
        for r in [self.rdo_open, self.rdo_foil50, self.rdo_foil30, self.rdo_interim]:
            bg_q.addButton(r)
            method_row.addWidget(r)
        lay.addLayout(method_row)

        # Open beam %dd(10) — used for <10 MV or interim
        self.row_pdd10_open = FieldRow(
            label="%dd(10) — open beam [shifted upstream by 0.6·r_cav]",
            unit="%",
            ref="Sec.VIII.B",
            decimals=2,
        )
        lay.addWidget(self.row_pdd10_open)

        # Lead foil %dd(10)_Pb
        self.row_pdd10_pb = FieldRow(
            label="%dd(10)_Pb — with 1 mm Pb foil [shifted upstream by 0.6·r_cav]",
            unit="%",
            ref="Sec.VIII.B",
            decimals=2,
        )
        lay.addWidget(self.row_pdd10_pb)

        # %dd(10)_x result
        self.row_pdd10x = FieldRow(
            label="%dd(10)_x   (photon component)",
            unit="%",
            ref="Eq.(13)/(14)/(15)",
            read_only=True,
            decimals=2,
        )
        lay.addWidget(self.row_pdd10x)

        lbl_note = QLabel(
            "Note: Lead foil must be REMOVED for the reference dosimetry measurement. "
            "FFF beams require lead foil regardless of energy (Report 374 §3.3)."
        )
        lbl_note.setWordWrap(True)
        lbl_note.setObjectName("noteLabel")
        lay.addWidget(lbl_note)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 5 — kQ
    # ------------------------------------------------------------------

    def _build_section_kq(self):
        grp, lay = self._make_group("5.  Determination of k_Q  (Sec. IX.B)")

        self.row_kq = FieldRow(
            label="k_Q  [Table I, interpolated]",
            unit="",
            ref="Table I / Fig.4",
            step="5",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_kq)
        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 6–8 — Environmental & measurement corrections
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

        # mmHg conversion helper
        self.btn_mmhg = QPushButton("Enter mmHg")
        self.btn_mmhg.setObjectName("btnSecondary")
        self.btn_mmhg.setFixedWidth(100)
        self.btn_mmhg.clicked.connect(self._enter_pressure_mmhg)
        tp_row.addWidget(self.btn_mmhg)
        tp_row.addStretch()
        lay.addLayout(tp_row)

        self.row_ptp = FieldRow(
            label="P_TP",
            unit="",
            ref="Eq.(10)",
            step="6",
            read_only=True,
            decimals=5,
        )
        lay.addWidget(self.row_ptp)

        # 7. Polarity
        pol_lbl = QLabel("7.  Polarity Correction  (Sec. VII.A)")
        pol_lbl.setObjectName("subTitle")
        lay.addWidget(pol_lbl)

        self.row_mraw_pol = DualFieldRow(
            label="Raw readings:",
            label_a="−300 V  M+raw =",
            label_b="  +300 V  M−raw =",
            unit="nC or rdg",
            ref="Sec.VII.A",
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
            label="P_pol",
            unit="",
            ref="Eq.(9)",
            step="7",
            read_only=True,
            decimals=4,
        )
        lay.addWidget(self.row_ppol)

        # 8. Ion recombination
        ion_lbl = QLabel("8.  Ion Recombination  P_ion  (Sec. VII.D.2)")
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
            label="Two-voltage readings:",
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

        # Jaffé plot override (FFF / high-dose-rate beams)
        jaffe_row = QHBoxLayout()
        self.btn_jaffe = QPushButton("Jaffé Plot…")
        self.btn_jaffe.setObjectName("btnSecondary")
        self.btn_jaffe.setToolTip(
            "Opens the multi-voltage Jaffé plot analysis.\n"
            "Recommended for FFF beams where P_ion may exceed 1.5%.\n"
            "Result can be used to override the two-voltage P_ion."
        )
        self.btn_jaffe.clicked.connect(self._open_jaffe_dialog)
        jaffe_row.addWidget(self.btn_jaffe)

        self.lbl_jaffe_pion = QLabel("")
        self.lbl_jaffe_pion.setObjectName("infoLabel")
        jaffe_row.addWidget(self.lbl_jaffe_pion)

        self.btn_clear_jaffe = QPushButton("Clear Jaffé Override")
        self.btn_clear_jaffe.setObjectName("btnSecondary")
        self.btn_clear_jaffe.setVisible(False)
        self.btn_clear_jaffe.clicked.connect(self._clear_jaffe_override)
        jaffe_row.addWidget(self.btn_clear_jaffe)
        jaffe_row.addStretch()
        lay.addLayout(jaffe_row)

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
            "Enter the leakage reading with beam off at identical setup conditions.\n"
            "P_leak = 1 − M_leak/M_raw.\n"
            "Leave at 0.0 if not measuring leakage (P_leak = 1.000).\n"
            "Should be < 0.1% of M_raw for a well-maintained chamber."
        )
        self.spn_mleak.valueChanged.connect(self._update_pleak_label)
        leak_row.addWidget(self.spn_mleak)
        self.lbl_pleak = QLabel("P_leak = 1.0000")
        self.lbl_pleak.setObjectName("dimLabel")
        leak_row.addWidget(self.lbl_pleak)
        leak_row.addStretch()
        lay.addLayout(leak_row)

        # P_rp (FFF)
        prp_lbl = QLabel("P_rp — Radial beam profile correction  (WGTG51-X / Report 374 §4.5)")
        prp_lbl.setObjectName("subTitle")
        lay.addWidget(prp_lbl)

        self.spn_prp = QDoubleSpinBox()
        self.spn_prp.setRange(0.990, 1.010)
        self.spn_prp.setDecimals(4)
        self.spn_prp.setValue(1.0000)
        self.spn_prp.setToolTip(
            "P_rp = 1.0000 for standard flattened beams.\n"
            "For FFF beams, measure using film or a high-resolution scanner "
            "at the reference depth (Report 374 §4.5). Can be up to 0.7% for 10 MV FFF."
        )
        prp_row = QHBoxLayout()
        prp_row.addWidget(QLabel("   P_rp:"))
        prp_row.addWidget(self.spn_prp)
        prp_row.addStretch()
        lay.addLayout(prp_row)

        self.main_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: 9 — Corrected reading
    # ------------------------------------------------------------------

    def _build_section_corrected_reading(self):
        grp, lay = self._make_group("9.  Corrected Ion Chamber Reading  M  (Sec. VII)")

        self.row_m_corrected = FieldRow(
            label="M = P_ion · P_TP · P_elec · P_pol · P_rp · M_raw",
            unit="nC or rdg",
            ref="Eq.(8)",
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

        self.row_dose_10cm = FieldRow(
            label="D_w at 10 cm reference depth",
            unit="cGy/MU",
            ref="Eq.(3)",
            step="10",
            read_only=True,
            decimals=4,
        )
        self.row_dose_10cm.field.setObjectName("resultFinal")
        lay.addWidget(self.row_dose_10cm)

        # d_max translation
        dmax_lbl = QLabel("11.  Dose at d_max  (if required)")
        dmax_lbl.setObjectName("subTitle")
        lay.addWidget(dmax_lbl)

        dmax_row = QHBoxLayout()
        dmax_row.addWidget(QLabel("Clinical %dd(10) [SSD] or TMR(10,10×10) [SAD]:"))
        self.spn_pdd_tmr = QDoubleSpinBox()
        self.spn_pdd_tmr.setRange(0.0, 120.0)
        self.spn_pdd_tmr.setDecimals(2)
        self.spn_pdd_tmr.setValue(0.0)
        self.spn_pdd_tmr.setToolTip(
            "SSD setup: enter %dd(10) as a percentage (e.g. 66.7).\n"
            "SAD setup: enter TMR(10, 10×10) as a decimal (e.g. 0.734)."
        )
        dmax_row.addWidget(self.spn_pdd_tmr)
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
        """Show live P_leak estimate when leakage is entered."""
        m_pos, _ = self.row_mraw_pol.get_values()
        if m_pos and m_pos != 0.0 and m_leak != 0.0:
            p_leak = 1.0 - m_leak / m_pos
            self.lbl_pleak.setText(f"P_leak = {p_leak:.4f}")
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
        """Gather inputs, run physics engine, populate result fields."""
        try:
            inp = self._gather_inputs()
            result = calculate_photon(inp)
            self._populate_results(result)
            self._last_inp = inp
            self._last_result = result
            self.btn_save.setEnabled(True)
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error:\n{e}")

    def _gather_inputs(self) -> PhotonCalibrationInput:
        """Read all UI fields into a PhotonCalibrationInput."""
        m_pos, m_neg = self.row_mraw_pol.get_values()
        m_high, m_low = self.row_mraw_ion.get_values()

        if m_pos is None or m_neg is None:
            raise ValueError("Both polarity readings (M+ and M-) are required.")
        if m_high is None or m_low is None:
            raise ValueError("Both two-voltage readings (M^H and M^L) are required.")

        pdd10_open = self.row_pdd10_open.get_value()
        pdd10_pb = self.row_pdd10_pb.get_value()

        foil_dist: Optional[float] = None
        if self.rdo_foil50.isChecked():
            foil_dist = 50.0
        elif self.rdo_foil30.isChecked():
            foil_dist = 30.0

        # Clinical %dd or TMR for d_max (0 = not entered)
        pdd_tmr_val = self.spn_pdd_tmr.value()
        is_sad = self.rdo_sad.isChecked()

        return PhotonCalibrationInput(
            chamber_model=self.cmb_chamber.currentText().lower(),
            n_dw_gy_per_c=self.spn_ndw.value(),
            p_elec=self.spn_pelec.value(),
            temperature_c=self.spn_temp.value(),
            pressure_kpa=self.spn_pressure.value(),
            energy_mv=self.spn_energy.value(),
            is_fff=self.chk_fff.isChecked(),
            pdd10_open=pdd10_open,
            pdd10_pb=pdd10_pb,
            pb_foil_distance_cm=foil_dist,
            use_interim_pdd10x=self.rdo_interim.isChecked(),
            m_raw_pos=m_pos,
            m_raw_neg=m_neg,
            calibration_polarity="neg" if self.rdo_calpos.isChecked() else "pos",
            v_high=self.spn_vh.value(),
            v_low=self.spn_vl.value(),
            m_raw_high=m_high,
            m_raw_low=m_low,
            p_rp=self.spn_prp.value(),
            m_leak=self.spn_mleak.value(),
            p_ion_override=self._p_ion_override,
            monitor_units=self.spn_mu.value(),
            setup_type="SAD" if is_sad else "SSD",
            ssd_or_sad_cm=self.spn_distance.value(),
            clinical_pdd_pct=pdd_tmr_val if (pdd_tmr_val > 1.0 and not is_sad) else None,
            clinical_tmr=pdd_tmr_val if (pdd_tmr_val > 0.0 and is_sad) else None,
        )

    def _populate_results(self, result):
        """Fill all computed result fields from PhysicsResult."""
        self.row_pdd10x.set_value(result.pdd10x)
        self.row_kq.set_value(result.k_q)
        self.row_ptp.set_value(result.p_tp)
        self.row_ppol.set_value(result.p_pol)
        self.row_pion.set_value(result.p_ion)
        self.row_m_corrected.set_value(result.m_corrected)
        self.row_dose_10cm.set_value(result.dose_10cm_cgy_per_mu, highlight_final=True)

        if result.dose_dmax_cgy_per_mu is not None:
            self.row_dose_dmax.set_value(result.dose_dmax_cgy_per_mu, highlight_final=True)

        # Warnings
        if result.warnings:
            self.lbl_warnings.setText("⚠  " + "\n⚠  ".join(result.warnings))
            self.lbl_warnings.show()
        else:
            self.lbl_warnings.hide()

    def _clear_results(self):
        for row in [
            self.row_pdd10x, self.row_kq, self.row_ptp, self.row_ppol,
            self.row_pion, self.row_m_corrected, self.row_dose_10cm, self.row_dose_dmax,
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
            rec_id = db_mod.save_photon_record(
                self._last_inp, self._last_result, physicist=physicist
            )
            QMessageBox.information(self, "Saved",
                                    f"Record #{rec_id} saved to history.")
            self.btn_save.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _open_jaffe_dialog(self):
        from ..dialogs.jaffe_dialog import JaffePlotDialog
        dlg = JaffePlotDialog(
            v_h=self.spn_vh.value(),
            on_accept=self._apply_jaffe_pion,
            parent=self,
        )
        dlg.exec()

    def _apply_jaffe_pion(self, p_ion: float):
        """Store Jaffé-derived P_ion override and show it in the UI."""
        self._p_ion_override = p_ion
        self.lbl_jaffe_pion.setText(
            f"Jaffé P_ion = {p_ion:.5f}  (will override two-voltage value on next Calculate)"
        )
        self.btn_clear_jaffe.setVisible(True)

    def _clear_jaffe_override(self):
        self._p_ion_override = None
        self.lbl_jaffe_pion.setText("")
        self.btn_clear_jaffe.setVisible(False)

    def _generate_report(self):
        try:
            inp = self._gather_inputs()
            result = calculate_photon(inp)
            from ...reports.pdf_generator import generate_photon_report
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", "TG51_Photon_Report.pdf", "PDF Files (*.pdf)"
            )
            if path:
                generate_photon_report(inp, result, path)
                QMessageBox.information(self, "Report Saved", f"Report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", str(e))
