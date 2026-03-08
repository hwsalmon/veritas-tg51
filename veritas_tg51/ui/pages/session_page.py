"""
session_page.py — Session-based calibration interface.

One tab per beam energy, ordered: Photon (non-FFF, by energy) → Photon FFF → Electron.
All raw readings entered in nC (3 replicates each); averages used for calculations.
Everything auto-calculates as values are entered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..dialogs.new_session_dialog import SessionSetup

_NC_TO_C = 1e-9   # nC → C


# ---------------------------------------------------------------------------
# Plain-data copy of BeamEnergy — safe after session close
# ---------------------------------------------------------------------------

@dataclass
class _BeamSnapshot:
    id: int
    modality: str
    energy_mv: float
    is_fff: bool
    label: str
    pdd_shift_pct: Optional[float] = None
    clinical_pdd_pct: Optional[float] = None
    i50_cm: Optional[float] = None


# ---------------------------------------------------------------------------
# Triplicate reading row
# ---------------------------------------------------------------------------

class TriplicateRow(QWidget):
    """
    Three side-by-side nC reading fields with a live average label.
    Emits `changed` whenever any field is edited.
    """
    changed = Signal()

    def __init__(self, row_label: str, label_width: int = 80, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel(row_label)
        lbl.setFixedWidth(label_width)
        lay.addWidget(lbl)

        self._fields = []
        val = QDoubleValidator()
        val.setDecimals(4)
        for _ in range(3):
            f = QLineEdit()
            f.setFixedWidth(75)
            f.setPlaceholderText("nC")
            f.setValidator(val)
            f.textChanged.connect(self._on_changed)
            lay.addWidget(f)
            self._fields.append(f)

        lay.addWidget(QLabel("→  avg ="))
        self.lbl_avg = QLabel("—")
        self.lbl_avg.setMinimumWidth(95)
        self.lbl_avg.setStyleSheet("font-family: monospace; color: #1A5276;")
        lay.addWidget(self.lbl_avg)

        lay.addStretch()

    def _on_changed(self):
        vals = self._values()
        if vals:
            avg = sum(vals) / len(vals)
            self.lbl_avg.setText(f"{avg:.4f} nC")
        else:
            self.lbl_avg.setText("—")
        self.changed.emit()

    def _values(self) -> list[float]:
        out = []
        for f in self._fields:
            try:
                v = float(f.text())
                out.append(v)
            except ValueError:
                pass
        return out

    def get_average_nc(self) -> Optional[float]:
        """Return average of entered values in nC, or None if no values."""
        vals = self._values()
        return sum(vals) / len(vals) if vals else None

    def get_average_c(self) -> Optional[float]:
        """Return average converted to Coulombs, or None."""
        v = self.get_average_nc()
        return v * _NC_TO_C if v is not None else None

    def clear(self):
        for f in self._fields:
            f.clear()
        self.lbl_avg.setText("—")


# ---------------------------------------------------------------------------
# Session page
# ---------------------------------------------------------------------------

class SessionPage(QWidget):
    """Tabbed calibration session.  One EnergyTab per beam energy."""

    def __init__(self, setup: SessionSetup, parent=None, ws_id: int = None):
        super().__init__(parent)
        self._setup = setup
        self._ws_id = ws_id          # WorksheetSession DB id; None until first save
        self._auto_save_pending = False
        self._build_ui()
        self._setup_autosave()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Session header ──
        header = QWidget()
        header.setStyleSheet("background-color: #1B2A4A;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 8, 16, 8)

        s = self._setup
        lbl = QLabel(
            f"<span style='color:white; font-size:13px; font-weight:bold;'>{s.linac_name}</span>"
            f"<span style='color:#7FB3D3;'>  ·  {s.center_name}"
            f"  |  Chamber: {s.chamber_model} SN {s.chamber_sn}"
            f"  N<sub>D,w</sub>={s.n_dw_gy_per_c:.3E} Gy/C"
            f"  |  Electrometer: {s.electrometer_model} SN {s.electrometer_sn}"
            f"  P<sub>elec</sub>={s.p_elec:.4f}"
            f"  |  {s.physicist or '—'}"
            f"  |  {s.session_date}</span>"
        )
        lbl.setTextFormat(Qt.RichText)
        h_lay.addWidget(lbl)
        h_lay.addStretch()
        layout.addWidget(header)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)
        self._load_beam_energies()
        layout.addWidget(self.tabs)

        # ── Auto-save status strip ──
        self._lbl_save_status = QLabel("  Not yet saved")
        self._lbl_save_status.setObjectName("saveStatus")
        layout.addWidget(self._lbl_save_status)

    def _load_beam_energies(self):
        from ...models.db import get_session as db_get_session
        from ...models.entities import BeamEnergy

        db = db_get_session()
        try:
            beams = (
                db.query(BeamEnergy)
                .filter(BeamEnergy.linac_id == self._setup.linac_id)
                .all()
            )
            beam_list = [
                _BeamSnapshot(
                    id=b.id, modality=b.modality,
                    energy_mv=b.energy_mv, is_fff=b.is_fff, label=b.label,
                    pdd_shift_pct=b.pdd_shift_pct,
                    clinical_pdd_pct=b.clinical_pdd_pct,
                    i50_cm=b.i50_cm,
                )
                for b in beams
            ]
        finally:
            db.close()

        if not beam_list:
            lbl = QLabel(
                "No beam energies configured for this machine.\n"
                "Add beams in Equipment → Treatment Machine."
            )
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #7D6608; font-size: 13px;")
            self.tabs.addTab(lbl, "No Beams")
            return

        # Order: photon non-FFF → photon FFF → electron, each by energy
        # Also detect electron beams from the label ("MeV") in case modality is mis-set in DB
        def sort_key(b: _BeamSnapshot):
            is_electron = (b.modality == "electron") or ("mev" in b.label.lower() and "mv" not in b.label.lower())
            if is_electron:
                return (2, b.energy_mv)
            fff_order = 1 if b.is_fff else 0
            return (fff_order, b.energy_mv)

        for beam in sorted(beam_list, key=sort_key):
            tab = EnergyTab(beam, self._setup)
            tab.state_changed.connect(self._schedule_autosave)
            self.tabs.addTab(tab, beam.label)

    def _energy_tabs(self) -> list:
        """Return all EnergyTab widgets from the tab widget."""
        tabs = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, EnergyTab):
                tabs.append(w)
        return tabs

    def _setup_autosave(self):
        """Configure the 3-second debounce auto-save timer."""
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(3000)   # 3 seconds after last change
        self._save_timer.timeout.connect(self._do_autosave)

    def _schedule_autosave(self):
        """Reset the debounce timer — called whenever any field changes."""
        self._save_timer.start()   # restarts if already running
        self._lbl_save_status.setText("  Unsaved changes…")
        self._lbl_save_status.setStyleSheet("color: #E67E22; font-size: 10px; padding: 2px 10px;")

    def _do_autosave(self):
        """Persist full session state to WorksheetSession table."""
        from ...models import db as db_mod
        if not db_mod.is_ready():
            return
        try:
            beam_states = {}
            beams_calculated = 0
            for tab in self._energy_tabs():
                state = tab.get_state()
                beam_states[str(tab._beam.id)] = state
                if state.get("has_result"):
                    beams_calculated += 1

            self._ws_id = db_mod.upsert_worksheet_session(
                ws_id=self._ws_id,
                setup=self._setup,
                beam_states=beam_states,
                beams_total=len(beam_states),
                beams_calculated=beams_calculated,
            )
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._lbl_save_status.setText(f"  Auto-saved {ts}")
            self._lbl_save_status.setStyleSheet(
                "color: #1E8449; font-size: 10px; padding: 2px 10px;"
            )
        except Exception as exc:
            self._lbl_save_status.setText(f"  Save error: {exc}")
            self._lbl_save_status.setStyleSheet(
                "color: #C0392B; font-size: 10px; padding: 2px 10px;"
            )

    def restore_beam_states(self, beam_states: dict):
        """Restore all tab field values from a saved beam_states dict."""
        for tab in self._energy_tabs():
            state = beam_states.get(str(tab._beam.id))
            if state:
                tab.restore_state(state)

    def print_full_report(self):
        """Generate a complete calibration report for all calculated beams."""
        import datetime
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        s = self._setup
        default_name = f"TG51_FullReport_{s.linac_name}_{ts}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Full Calibration Report", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            from ...reports.pdf_generator import generate_full_session_report
            tabs = self._energy_tabs()
            beam_results = []
            for tab in tabs:
                if tab._last_inp is not None and tab._last_result is not None:
                    if tab._beam.modality == "electron":
                        field_info = {"cone": tab.cmb_cone.currentText()}
                    else:
                        field_info = {"field_size": "10x10 cm"}
                    field_info["mraw_adjusted"] = tab._mraw_adjusted
                    beam_results.append((tab._beam, tab._last_inp, tab._last_result, field_info))
            if not beam_results:
                QMessageBox.warning(self, "No Results",
                    "Calculate at least one beam before printing a full report.")
                return
            # Always look up cal dates & linac SN fresh from DB for restored sessions
            ch_cal = str(s.chamber_calibration_date) if s.chamber_calibration_date else None
            el_cal = str(s.electrometer_calibration_date) if s.electrometer_calibration_date else None
            linac_sn = getattr(s, "linac_sn", None) or ""
            if (ch_cal is None or el_cal is None or not linac_sn) and s.chamber_id and s.electrometer_id:
                try:
                    from ...models.db import get_session as _db
                    from ...models.entities import IonChamber, Electrometer, Linac
                    _sess = _db()
                    try:
                        ch_obj = _sess.get(IonChamber, s.chamber_id)
                        el_obj = _sess.get(Electrometer, s.electrometer_id)
                        li_obj = _sess.get(Linac, s.linac_id)
                        if ch_obj and ch_obj.calibration_date:
                            ch_cal = str(ch_obj.calibration_date).split()[0]
                        if el_obj and el_obj.calibration_date:
                            el_cal = str(el_obj.calibration_date).split()[0]
                        if li_obj and li_obj.serial_number:
                            linac_sn = li_obj.serial_number
                    finally:
                        _sess.close()
                except Exception:
                    pass
            sn_part = f"  SN {linac_sn}" if linac_sn else ""
            machine_str = f"{s.linac_model}  ({s.linac_name}){sn_part}"
            common = dict(
                institution=s.center_name,
                physicist=s.physicist,
                machine=machine_str,
                chamber_model=s.chamber_model,
                chamber_sn=s.chamber_sn,
                electrometer_model=s.electrometer_model,
                electrometer_sn=s.electrometer_sn,
                r_cav_cm=s.r_cav_cm,
                session_date=str(s.session_date),
                chamber_calibration_date=ch_cal,
                electrometer_calibration_date=el_cal,
            )
            generate_full_session_report(beam_results, path, **common)
            QMessageBox.information(self, "Report Saved", f"Full report saved to:\n{path}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Report Error", f"{e}\n\n{traceback.format_exc()}")


# ---------------------------------------------------------------------------
# Per-energy calibration tab
# ---------------------------------------------------------------------------

class EnergyTab(QScrollArea):
    """Full TG-51 calibration form for one beam energy, with triplicate readings."""

    state_changed = Signal()   # emitted whenever any field changes (for auto-save)

    def __init__(self, beam: _BeamSnapshot, setup: SessionSetup, parent=None):
        super().__init__(parent)
        self._beam = beam
        self._setup = setup
        self._last_inp = None
        self._last_result = None
        self._p_ion_override: Optional[float] = None
        self._mraw_adjusted = False   # True when user has locked M_raw after cal adjustment
        self._restoring = False   # suppress re-entrant auto-saves during restore
        self.setWidgetResizable(True)

        inner = QWidget()
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(20, 14, 20, 20)
        self._lay.setSpacing(10)

        self._build_site_info()
        self._build_conditions()
        self._build_beam_quality()
        self._build_readings()
        self._build_results_bar()
        self._build_action_row()

        self._lay.addStretch()
        self.setWidget(inner)
        self._apply_beam_defaults()

    # ------------------------------------------------------------------
    # Section: site info + notes
    # ------------------------------------------------------------------

    def _apply_beam_defaults(self):
        """Pre-fill beam quality and d_max fields from stored beam defaults."""
        b = self._beam
        if b.modality == "photon":
            if b.pdd_shift_pct:
                self.txt_pdd10.setText(str(b.pdd_shift_pct))
            if b.clinical_pdd_pct:
                self.txt_pdd_tmr.setText(str(b.clinical_pdd_pct))
        else:
            if b.i50_cm:
                self.txt_i50.setText(str(b.i50_cm))
            if b.clinical_pdd_pct:
                self.txt_pdd_tmr.setText(str(b.clinical_pdd_pct))

    def _build_site_info(self):
        s = self._setup
        is_photon = self._beam.modality == "photon"
        color = "#1B2A4A" if is_photon else "#1B3A2A"

        bar = QWidget()
        bar.setStyleSheet(f"background:{color}; border-radius:4px;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 12, 6)

        lbl = QLabel(
            f"<b style='color:white'>{self._beam.label}"
            f"{'  [FFF]' if self._beam.is_fff else ''}</b>"
            f"<span style='color:#AED6F1;'>"
            f"  ·  {s.linac_name}  ({s.linac_model})"
            f"  ·  {s.center_name}"
            f"  ·  Chamber: {s.chamber_model} SN {s.chamber_sn}"
            f"    N<sub>D,w</sub> = {s.n_dw_gy_per_c:.3E} Gy/C"
            f"  ·  Electrometer: {s.electrometer_model} SN {s.electrometer_sn}"
            f"    P<sub>elec</sub> = {s.p_elec:.4f}"
            f"  ·  Physicist: {s.physicist or '—'}"
            f"  ·  Date: {s.session_date}"
            f"</span>"
        )
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self._lay.addWidget(bar)

        # Notes row
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Notes:"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Optional measurement notes for this beam energy")
        notes_row.addWidget(self.txt_notes)
        self._lay.addLayout(notes_row)

    # ------------------------------------------------------------------
    # Section: environmental conditions
    # ------------------------------------------------------------------

    def _build_conditions(self):
        grp = QGroupBox("Environmental Conditions  &  Setup")
        form = QFormLayout(grp)
        form.setSpacing(8)
        form.setContentsMargins(12, 14, 12, 12)

        # Temperature / Pressure → P_TP live
        tp_row = QHBoxLayout()
        tp_row.addWidget(QLabel("Temperature:"))
        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(10, 40); self.spn_temp.setDecimals(1)
        self.spn_temp.setValue(22.0); self.spn_temp.setSuffix(" °C")
        self.spn_temp.valueChanged.connect(self._update_ptp)
        tp_row.addWidget(self.spn_temp)
        tp_row.addSpacing(16)

        tp_row.addWidget(QLabel("Pressure:"))
        self.spn_pressure = QDoubleSpinBox()
        self.spn_pressure.setRange(85, 110); self.spn_pressure.setDecimals(2)
        self.spn_pressure.setValue(101.33); self.spn_pressure.setSuffix(" kPa")
        self.spn_pressure.valueChanged.connect(self._update_ptp)
        tp_row.addWidget(self.spn_pressure)

        btn_mmhg = QPushButton("mmHg")
        btn_mmhg.setMinimumWidth(65); btn_mmhg.setObjectName("btnSecondary")
        btn_mmhg.clicked.connect(self._enter_mmhg)
        tp_row.addWidget(btn_mmhg)
        tp_row.addSpacing(16)

        tp_row.addWidget(QLabel("P_TP ="))
        self.lbl_ptp = QLabel("—")
        self.lbl_ptp.setStyleSheet("font-family:monospace; font-size:12px; color:#1A5276; font-weight:bold;")
        tp_row.addWidget(self.lbl_ptp)
        tp_row.addStretch()
        form.addRow(tp_row)

        # MU / Setup
        setup_row = QHBoxLayout()
        setup_row.addWidget(QLabel("Monitor units:"))
        self.spn_mu = QDoubleSpinBox()
        self.spn_mu.setRange(1, 10000); self.spn_mu.setDecimals(0)
        self.spn_mu.setValue(200); self.spn_mu.setSuffix(" MU")
        setup_row.addWidget(self.spn_mu)
        setup_row.addSpacing(16)

        setup_row.addWidget(QLabel("Setup:"))
        self.rdo_sad = QRadioButton("SAD"); self.rdo_ssd = QRadioButton("SSD")
        self.rdo_ssd.setChecked(True)   # default SSD
        bg = QButtonGroup(self); bg.addButton(self.rdo_sad); bg.addButton(self.rdo_ssd)
        setup_row.addWidget(self.rdo_sad); setup_row.addWidget(self.rdo_ssd)
        setup_row.addSpacing(8)
        setup_row.addWidget(QLabel("Distance:"))
        self.spn_dist = QDoubleSpinBox()
        self.spn_dist.setRange(80, 120); self.spn_dist.setDecimals(1)
        self.spn_dist.setValue(100.0); self.spn_dist.setSuffix(" cm")
        setup_row.addWidget(self.spn_dist)
        setup_row.addStretch()
        form.addRow(setup_row)

        # Field size / applicator row
        field_row = QHBoxLayout()
        if self._beam.modality == "photon":
            field_row.addWidget(QLabel("Field size:"))
            field_row.addWidget(QLabel("10×10 cm"))
            field_row.addSpacing(24)
        else:
            field_row.addWidget(QLabel("Applicator/cone:"))
            self.cmb_cone = QComboBox()
            self.cmb_cone.addItems([
                "6×6 cm", "10×10 cm", "14×14 cm", "20×20 cm", "25×25 cm",
            ])
            self.cmb_cone.setCurrentText("10×10 cm")
            field_row.addWidget(self.cmb_cone)
        field_row.addStretch()
        form.addRow(field_row)

        self._lay.addWidget(grp)
        self._update_ptp()

    # ------------------------------------------------------------------
    # Section: beam quality
    # ------------------------------------------------------------------

    def _build_beam_quality(self):
        if self._beam.modality == "photon":
            self._build_bq_photon()
        else:
            self._build_bq_electron()

    def _build_bq_photon(self):
        grp = QGroupBox(
            "Beam Quality  —  %dd(10)_x  "
            "(TG-51 1999 Eq. 15 / 2014 Addendum Sec. 2.2-2.3)"
        )
        form = QFormLayout(grp)
        form.setSpacing(8); form.setContentsMargins(12, 14, 12, 12)

        pdd_row = QHBoxLayout()
        pdd_row.addWidget(QLabel("%dd(10):"))
        self.txt_pdd10 = QLineEdit(); self.txt_pdd10.setFixedWidth(72)
        self.txt_pdd10.setPlaceholderText("e.g. 66.7")
        self.txt_pdd10.textChanged.connect(self._try_auto_calc)
        pdd_row.addWidget(self.txt_pdd10); pdd_row.addWidget(QLabel("%"))
        pdd_row.addSpacing(20)
        pdd_row.addWidget(QLabel("->  %dd(10)_x ="))
        self.lbl_pdd10x = QLabel("—")
        self.lbl_pdd10x.setStyleSheet("font-family:monospace; color:#1A5276; font-weight:bold;")
        pdd_row.addWidget(self.lbl_pdd10x)
        pdd_row.addSpacing(20)
        pdd_row.addWidget(QLabel("k_Q ="))
        self.lbl_kq = QLabel("—")
        self.lbl_kq.setStyleSheet("font-family:monospace; color:#1A5276; font-weight:bold;")
        pdd_row.addWidget(self.lbl_kq)
        pdd_row.addStretch()
        form.addRow(pdd_row)

        # d_max conversion
        dmax_row = QHBoxLayout()
        dmax_row.addWidget(QLabel("Clinical %dd(10) or TMR for d_max  (0 = skip):"))
        self.txt_pdd_tmr = QLineEdit(); self.txt_pdd_tmr.setFixedWidth(72)
        self.txt_pdd_tmr.setText("0"); self.txt_pdd_tmr.textChanged.connect(self._try_auto_calc)
        dmax_row.addWidget(self.txt_pdd_tmr); dmax_row.addStretch()
        form.addRow(dmax_row)

        self._lay.addWidget(grp)

    def _build_bq_electron(self):
        grp = QGroupBox("Beam Quality  —  I_50 → R_50  (Report 385 §III.B)")
        form = QFormLayout(grp)
        form.setSpacing(8); form.setContentsMargins(12, 14, 12, 12)

        i50_row = QHBoxLayout()
        i50_row.addWidget(QLabel("I_50  (depth 50% ionization, EPOM-corrected):"))
        self.txt_i50 = QLineEdit(); self.txt_i50.setFixedWidth(72)
        self.txt_i50.setPlaceholderText("cm"); self.txt_i50.textChanged.connect(self._on_i50_changed)
        i50_row.addWidget(self.txt_i50); i50_row.addWidget(QLabel("cm"))
        i50_row.addSpacing(20)
        i50_row.addWidget(QLabel("→  R_50 ="))
        self.lbl_r50 = QLabel("—")
        self.lbl_r50.setStyleSheet("font-family:monospace; color:#1A5276; font-weight:bold;")
        i50_row.addWidget(self.lbl_r50)
        i50_row.addSpacing(12)
        i50_row.addWidget(QLabel("d_ref ="))
        self.lbl_dref = QLabel("—")
        self.lbl_dref.setStyleSheet("font-family:monospace; color:#1A5276; font-weight:bold;")
        i50_row.addWidget(self.lbl_dref)
        i50_row.addSpacing(12)
        i50_row.addWidget(QLabel("k_Q ="))
        self.lbl_kq = QLabel("—")
        self.lbl_kq.setStyleSheet("font-family:monospace; color:#1A5276; font-weight:bold;")
        i50_row.addWidget(self.lbl_kq)
        i50_row.addStretch()
        form.addRow(i50_row)

        dmax_row = QHBoxLayout()
        dmax_row.addWidget(QLabel("Clinical %dd(d_ref) or TMR at d_ref for d_max  (0 = skip):"))
        self.txt_pdd_tmr = QLineEdit(); self.txt_pdd_tmr.setFixedWidth(72)
        self.txt_pdd_tmr.setText("0"); self.txt_pdd_tmr.textChanged.connect(self._try_auto_calc)
        dmax_row.addWidget(self.txt_pdd_tmr); dmax_row.addStretch()
        form.addRow(dmax_row)

        self._lay.addWidget(grp)

    # ------------------------------------------------------------------
    # Section: readings (triplicate)
    # ------------------------------------------------------------------

    def _build_readings(self):
        # ── Polarity correction ──
        pol_grp = QGroupBox("Polarity Correction  (P_pol)")
        pol_lay = QVBoxLayout(pol_grp)
        pol_lay.setContentsMargins(12, 14, 12, 12); pol_lay.setSpacing(6)

        # Header row showing column labels
        hdr = QHBoxLayout()
        hdr.addWidget(_hdr_lbl("", 80))
        for txt in ("Reading 1", "Reading 2", "Reading 3", "→  Mean"):
            hdr.addWidget(_hdr_lbl(txt, 75 if "Reading" in txt else 110))
        hdr.addStretch()
        pol_lay.addLayout(hdr)

        # Operating voltage selector
        cp_row = QHBoxLayout()
        cp_row.addWidget(QLabel("Operating voltage:"))
        self.rdo_calpos = QRadioButton("−300 V")
        self.rdo_calneg = QRadioButton("+300 V")
        self.rdo_calpos.setChecked(True)   # default: −300 V operating
        bg_pol = QButtonGroup(self)
        bg_pol.addButton(self.rdo_calpos); bg_pol.addButton(self.rdo_calneg)
        cp_row.addWidget(self.rdo_calpos); cp_row.addWidget(self.rdo_calneg)
        cp_row.addStretch()
        pol_lay.addLayout(cp_row)

        self.row_mpos = TriplicateRow("−300 V  M⁺ (nC):", label_width=140)
        self.row_mneg = TriplicateRow("+300 V  M⁻ (nC):", label_width=140)
        self.row_mpos.changed.connect(self._update_ppol)
        self.row_mneg.changed.connect(self._update_ppol)
        self.rdo_calpos.toggled.connect(self._update_ppol)
        self.rdo_calpos.toggled.connect(self._update_ion_signs)
        pol_lay.addWidget(self.row_mpos)
        pol_lay.addWidget(self.row_mneg)

        ppol_row = QHBoxLayout()
        ppol_row.addSpacing(80)
        ppol_row.addWidget(QLabel("P_pol ="))
        self.lbl_ppol = QLabel("—")
        self.lbl_ppol.setStyleSheet(
            "font-family:monospace; font-size:13px; font-weight:bold; color:#1A5276;"
        )
        ppol_row.addWidget(self.lbl_ppol)
        ppol_row.addStretch()
        pol_lay.addLayout(ppol_row)
        self._lay.addWidget(pol_grp)

        # ── Ion recombination ──
        ion_grp = QGroupBox("Ion Recombination  (P_ion)  —  Two-Voltage Method")
        ion_lay = QVBoxLayout(ion_grp)
        ion_lay.setContentsMargins(12, 14, 12, 12); ion_lay.setSpacing(6)

        # Voltage row
        vrow = QHBoxLayout()
        vrow.addWidget(QLabel("V_H:"))
        self.lbl_vh_sign = QLabel("−")
        vrow.addWidget(self.lbl_vh_sign)
        self.spn_vh = QDoubleSpinBox()
        self.spn_vh.setRange(50, 1000); self.spn_vh.setDecimals(0)
        self.spn_vh.setValue(300); self.spn_vh.setSuffix(" V")
        self.spn_vh.valueChanged.connect(self._update_pion)
        vrow.addWidget(self.spn_vh)
        vrow.addSpacing(20)
        vrow.addWidget(QLabel("V_L:"))
        self.lbl_vl_sign = QLabel("−")
        vrow.addWidget(self.lbl_vl_sign)
        self.spn_vl = QDoubleSpinBox()
        self.spn_vl.setRange(25, 500); self.spn_vl.setDecimals(0)
        self.spn_vl.setValue(150); self.spn_vl.setSuffix(" V")
        self.spn_vl.valueChanged.connect(self._update_pion)
        vrow.addWidget(self.spn_vl)
        vrow.addStretch()
        ion_lay.addLayout(vrow)

        # Column header
        hdr2 = QHBoxLayout()
        hdr2.addWidget(_hdr_lbl("", 80))
        for txt in ("Reading 1", "Reading 2", "Reading 3", "→  Mean"):
            hdr2.addWidget(_hdr_lbl(txt, 75 if "Reading" in txt else 110))
        hdr2.addStretch()
        ion_lay.addLayout(hdr2)

        # M_H = reference reading at V_H — auto-populated from M⁺ polarity average
        mh_row = QHBoxLayout()
        mh_lbl = _hdr_lbl("M_H (nC):", 80); mh_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        mh_row.addWidget(mh_lbl)
        self.txt_mhigh = QLineEdit(); self.txt_mhigh.setFixedWidth(90)
        self.txt_mhigh.setPlaceholderText("auto from M⁺ (−300 V avg)")
        self.txt_mhigh.setStyleSheet("background:#EBF5FB;")
        self.txt_mhigh.textChanged.connect(self._update_pion)
        mh_row.addWidget(self.txt_mhigh)
        lbl_mh_hint = QLabel("  ← auto-filled from operating-voltage avg  (editable override)")
        lbl_mh_hint.setStyleSheet("color:#888; font-size:10px;")
        mh_row.addWidget(lbl_mh_hint)
        mh_row.addStretch()
        ion_lay.addLayout(mh_row)

        self.row_mlow = TriplicateRow("M_L (nC):")
        self.row_mlow.changed.connect(self._update_pion)
        ion_lay.addWidget(self.row_mlow)

        pion_row = QHBoxLayout()
        pion_row.addSpacing(80)
        pion_row.addWidget(QLabel("P_ion ="))
        self.lbl_pion = QLabel("—")
        self.lbl_pion.setStyleSheet(
            "font-family:monospace; font-size:13px; font-weight:bold; color:#1A5276;"
        )
        pion_row.addWidget(self.lbl_pion)

        btn_jaffe = QPushButton("Jaffé…")
        btn_jaffe.setMinimumWidth(75); btn_jaffe.setObjectName("btnSecondary")
        btn_jaffe.clicked.connect(self._open_jaffe)
        pion_row.addSpacing(20); pion_row.addWidget(btn_jaffe)
        self.lbl_jaffe = QLabel("")
        self.lbl_jaffe.setStyleSheet("color:#1A5276; font-size:10px;")
        pion_row.addWidget(self.lbl_jaffe)
        pion_row.addStretch()
        ion_lay.addLayout(pion_row)
        self._lay.addWidget(ion_grp)

        # ── Leakage ──
        leak_row = QHBoxLayout()
        leak_row.addWidget(QLabel("M_leak (beam-off, nC):"))
        self.txt_mleak = QLineEdit(); self.txt_mleak.setFixedWidth(80)
        self.txt_mleak.setText("0"); self.txt_mleak.setPlaceholderText("0 = skip")
        self.txt_mleak.textChanged.connect(self._try_auto_calc)
        leak_row.addWidget(self.txt_mleak)
        leak_row.addWidget(QLabel("   P_leak ="))
        self.lbl_pleak = QLabel("1.0000")
        self.lbl_pleak.setStyleSheet("font-family:monospace; color:#1A5276;")
        leak_row.addWidget(self.lbl_pleak)
        leak_row.addStretch()
        self._lay.addLayout(leak_row)

        # ── M_raw reference for calibration ──
        mraw_grp = QGroupBox("Reference Reading  M_raw  (used in D_w = M·k_Q·N_D,w)")
        mraw_lay = QHBoxLayout(mraw_grp)
        mraw_lay.setContentsMargins(12, 10, 12, 10); mraw_lay.setSpacing(10)

        mraw_lay.addWidget(QLabel("M_raw:"))
        self.txt_mraw_cal = QLineEdit()
        self.txt_mraw_cal.setFixedWidth(100)
        self.txt_mraw_cal.setPlaceholderText("auto from M⁺")
        self.txt_mraw_cal.setStyleSheet("background:#EBF5FB; font-family:monospace;")
        self.txt_mraw_cal.textChanged.connect(self._on_mraw_cal_changed)
        mraw_lay.addWidget(self.txt_mraw_cal)
        mraw_lay.addWidget(QLabel("nC"))

        self.lbl_mraw_hint = QLabel(
            "  ← defaults to M⁺ average.  "
            "After machine output adjustment, enter the new reading here "
            "to confirm the calibration is correct — dose auto-recalculates."
        )
        self.lbl_mraw_hint.setWordWrap(True)
        self.lbl_mraw_hint.setStyleSheet("color:#555; font-size:10px;")
        mraw_lay.addWidget(self.lbl_mraw_hint)
        mraw_lay.addStretch()
        self._lay.addWidget(mraw_grp)

        # ── FFF P_rp ──
        if self._beam.is_fff:
            from ...physics.chamber_data import get_fff_prp
            prp_row = QHBoxLayout()
            prp_row.addWidget(QLabel("P_rp (FFF radial correction):"))
            self.spn_prp = QDoubleSpinBox()
            self.spn_prp.setRange(0.990, 1.020); self.spn_prp.setDecimals(4)

            # Auto-fill from published data (chamber+linac specific, or energy-based typical)
            prp_val, prp_unc, prp_src = get_fff_prp(
                self._setup.chamber_model,
                self._setup.linac_model,
                self._beam.energy_mv,
            )
            self.spn_prp.setValue(prp_val)
            prp_note = QLabel(
                f"  Recommended: {prp_val:.3f} \u00b1 {prp_unc:.4f}  [{prp_src}]  "
                "\u2014 editable; measure with water tank scan for site-specific value"
            )
            prp_note.setStyleSheet("color: #555; font-size: 10px;")

            self.spn_prp.valueChanged.connect(self._try_auto_calc)
            prp_row.addWidget(self.spn_prp)
            prp_row.addWidget(prp_note)
            prp_row.addStretch()
            self._lay.addLayout(prp_row)
        else:
            self.spn_prp = None

    # ------------------------------------------------------------------
    # Section: results bar
    # ------------------------------------------------------------------

    def _build_results_bar(self):
        grp = QGroupBox("Results")
        lay = QFormLayout(grp)
        lay.setSpacing(6); lay.setContentsMargins(12, 12, 12, 12)

        def _r():
            lbl = QLabel("—")
            lbl.setStyleSheet("font-family:monospace; font-size:12px;")
            return lbl

        self.lbl_res_ptp  = _r()
        self.lbl_res_ppol = _r()
        self.lbl_res_pion = _r()
        self.lbl_res_kq   = _r()
        self.lbl_res_pleak= _r()
        self.lbl_mcorr    = _r()
        self.lbl_dose     = _r()
        self.lbl_dmax = QLabel("—")
        self.lbl_dmax.setStyleSheet(
            "font-family:monospace; font-size:15px; font-weight:bold; color:#1A5276;"
        )
        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setWordWrap(True)
        self.lbl_warnings.setStyleSheet("color:#7D6608; font-size:11px;")

        lay.addRow("P_TP:", self.lbl_res_ptp)
        lay.addRow("P_pol:", self.lbl_res_ppol)
        lay.addRow("P_ion:", self.lbl_res_pion)
        lay.addRow("P_leak:", self.lbl_res_pleak)
        lay.addRow("k_Q:", self.lbl_res_kq)
        lay.addRow("M_corrected:", self.lbl_mcorr)
        lay.addRow("Dose at ref depth:", self.lbl_dose)
        lay.addRow("<b>★ Dose at d_max:</b>", self.lbl_dmax)
        lay.addRow(self.lbl_warnings)

        self._lay.addWidget(grp)

    def _build_action_row(self):
        row = QHBoxLayout()
        self.btn_save = QPushButton("Save to History")
        self.btn_save.setObjectName("btnSecondary"); self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_save)
        self.btn_pdf = QPushButton("PDF Report")
        self.btn_pdf.setObjectName("btnSecondary"); self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self._pdf_report)
        row.addWidget(self.btn_pdf)
        row.addStretch()
        self._lay.addLayout(row)

    # ------------------------------------------------------------------
    # Live partial calculations
    # ------------------------------------------------------------------

    def _update_ptp(self):
        try:
            from ...physics.corrections import p_tp
            val = p_tp(self.spn_temp.value(), self.spn_pressure.value())
            self.lbl_ptp.setText(f"{val:.3f}")
        except Exception:
            self.lbl_ptp.setText("—")
        self._try_auto_calc()

    def _on_i50_changed(self, text: str):
        try:
            from ...physics.tg51_electron import i50_to_r50
            i50 = float(text)
            r50 = i50_to_r50(i50)
            dref = 0.6 * r50 - 0.1
            self.lbl_r50.setText(f"{r50:.3f} cm")
            self.lbl_dref.setText(f"{dref:.3f} cm")
        except Exception:
            self.lbl_r50.setText("—"); self.lbl_dref.setText("—")
        self._update_kq_electron()
        self._try_auto_calc()

    def _update_kq_electron(self):
        try:
            from ...physics.tg51_electron import i50_to_r50
            from ...physics.chamber_data import get_electron_kq, list_electron_chambers
            i50 = float(self.txt_i50.text())
            r50 = i50_to_r50(i50)
            model = self._setup.chamber_model.lower()
            avail = list_electron_chambers()
            if model not in avail:
                model = avail[0] if avail else None
            if model:
                kqecal, kqp, kq = get_electron_kq(model, r50)
                self.lbl_kq.setText(f"{kq:.3f}  (k_Qecal={kqecal:.3f}, k'_Q={kqp:.3f})")
        except Exception:
            self.lbl_kq.setText("—")

    def _update_ion_signs(self):
        """Update ± sign labels on V_H / V_L to reflect operating voltage polarity."""
        sign = "−" if self.rdo_calpos.isChecked() else "+"
        self.lbl_vh_sign.setText(sign)
        self.lbl_vl_sign.setText(sign)

    def _update_ppol(self):
        m_pos = self.row_mpos.get_average_c()
        m_neg = self.row_mneg.get_average_c()

        # M_H auto-fills from the CALIBRATION POLARITY reading (operating voltage).
        # If calibration polarity is negative (-V), M_H comes from M⁻, not M⁺.
        cal = "pos" if self.rdo_calpos.isChecked() else "neg"
        ref_row = self.row_mpos if cal == "pos" else self.row_mneg
        ref_avg_nc = ref_row.get_average_nc()
        if ref_avg_nc is not None and not self.txt_mhigh.hasFocus():
            self.txt_mhigh.blockSignals(True)
            self.txt_mhigh.setText(f"{ref_avg_nc:.4f}")
            self.txt_mhigh.blockSignals(False)

        # M_raw cal reference syncs to the calibration polarity reading,
        # but only if the user has NOT locked it with a calibration adjustment.
        if ref_avg_nc is not None and not self.txt_mraw_cal.hasFocus() and not self._mraw_adjusted:
            self.txt_mraw_cal.blockSignals(True)
            self.txt_mraw_cal.setText(f"{ref_avg_nc:.4f}")
            self.txt_mraw_cal.blockSignals(False)

        if m_pos is None or m_neg is None:
            self.lbl_ppol.setText("—")
            return
        try:
            from ...physics.corrections import p_pol
            ppol, _ = p_pol(m_pos, m_neg, cal)
            self.lbl_ppol.setText(f"{ppol:.3f}")
        except Exception:
            self.lbl_ppol.setText("—")
        self._try_auto_calc()

    def _get_mhigh_c(self) -> Optional[float]:
        """M_H in Coulombs — from editable txt_mhigh field."""
        try:
            return float(self.txt_mhigh.text()) * _NC_TO_C
        except ValueError:
            return None

    def _update_pion(self):
        m_h = self._get_mhigh_c()
        m_l = self.row_mlow.get_average_c()
        if m_h is None or m_l is None:
            self.lbl_pion.setText("—")
            return
        try:
            from ...physics.corrections import p_ion_pulsed
            if self._p_ion_override is not None:
                self.lbl_pion.setText(f"{self._p_ion_override:.3f}  [Jaffé]")
            else:
                pion = p_ion_pulsed(self.spn_vh.value(), self.spn_vl.value(), m_h, m_l)
                self.lbl_pion.setText(f"{pion:.3f}")
        except Exception:
            self.lbl_pion.setText("—")
        self._try_auto_calc()

    def _on_mraw_cal_changed(self):
        """User has manually edited M_raw — lock it and recalculate."""
        if not self._restoring:
            text = self.txt_mraw_cal.text().strip()
            self._mraw_adjusted = bool(text)
            self._update_mraw_hint()
        self._try_auto_calc()

    def _update_mraw_hint(self):
        """Update the M_raw hint label and field style to reflect adjustment state."""
        if self._mraw_adjusted:
            self.lbl_mraw_hint.setText(
                "  ✔ Calibration adjustment made — this reading is locked "
                "and will not auto-update from M⁺."
            )
            self.lbl_mraw_hint.setStyleSheet("color:#B7700A; font-size:10px; font-weight:bold;")
            self.txt_mraw_cal.setStyleSheet("background:#FEF9E7; font-family:monospace; border:1px solid #B7700A;")
        else:
            self.lbl_mraw_hint.setText(
                "  ← defaults to M⁺ average.  "
                "After machine output adjustment, enter the new reading here "
                "to confirm the calibration is correct — dose auto-recalculates."
            )
            self.lbl_mraw_hint.setStyleSheet("color:#555; font-size:10px;")
            self.txt_mraw_cal.setStyleSheet("background:#EBF5FB; font-family:monospace;")

    def _get_mraw_cal_c(self) -> Optional[float]:
        """Return the M_raw reference value in Coulombs (from txt_mraw_cal or M⁺ fallback)."""
        try:
            return float(self.txt_mraw_cal.text()) * _NC_TO_C
        except ValueError:
            return self.row_mpos.get_average_c()

    # ------------------------------------------------------------------
    # Full auto-calculation
    # ------------------------------------------------------------------

    def _try_auto_calc(self, *_):
        """Attempt a full calculation; show reason if inputs are incomplete."""
        try:
            if self._beam.modality == "photon":
                self._calc_photon()
            else:
                self._calc_electron()
        except Exception as exc:
            # Show the blocking reason so the user knows what's missing
            if hasattr(self, 'lbl_warnings'):
                self.lbl_warnings.setText(f"Awaiting inputs: {exc}")
        if not self._restoring:
            self.state_changed.emit()

    def _calc_photon(self):
        from ...physics.tg51_photon import PhotonCalibrationInput, calculate_photon

        # M⁺ average is ALWAYS used for correction factors (P_pol, P_ion, etc.)
        m_pos  = self.row_mpos.get_average_c()
        m_neg  = self.row_mneg.get_average_c()
        m_high = self._get_mhigh_c()
        m_low  = self.row_mlow.get_average_c()
        missing = [n for n, v in [("M+", m_pos), ("M-", m_neg), ("M_H", m_high), ("M_L", m_low)] if v is None]
        if missing:
            raise ValueError(f"Enter readings: {', '.join(missing)}")

        pdd10_open = _safe_float(self.txt_pdd10.text())
        pdd_tmr    = _safe_float(self.txt_pdd_tmr.text()) or 0.0
        m_leak     = (_safe_float(self.txt_mleak.text()) or 0.0) * _NC_TO_C
        is_sad     = self.rdo_sad.isChecked()

        inp = PhotonCalibrationInput(
            chamber_model=self._setup.chamber_model.lower(),
            n_dw_gy_per_c=self._setup.n_dw_gy_per_c,
            p_elec=self._setup.p_elec,
            temperature_c=self.spn_temp.value(),
            pressure_kpa=self.spn_pressure.value(),
            energy_mv=self._beam.energy_mv,
            is_fff=self._beam.is_fff,
            pdd10_open=pdd10_open,
            m_raw_pos=m_pos, m_raw_neg=m_neg,
            calibration_polarity="pos" if self.rdo_calpos.isChecked() else "neg",
            v_high=self.spn_vh.value(), v_low=self.spn_vl.value(),
            m_raw_high=m_high, m_raw_low=m_low,
            p_rp=self.spn_prp.value() if self.spn_prp else 1.0,
            m_leak=m_leak, p_ion_override=self._p_ion_override,
            monitor_units=self.spn_mu.value(),
            setup_type="SAD" if is_sad else "SSD",
            ssd_or_sad_cm=self.spn_dist.value(),
            clinical_pdd_pct=pdd_tmr if (pdd_tmr > 1.0 and not is_sad) else None,
            clinical_tmr=pdd_tmr if (pdd_tmr > 0.0 and is_sad) else None,
        )
        result = calculate_photon(inp)

        # Post-calc M_raw override: scales dose only, correction factors unchanged.
        m_raw_override = self._get_mraw_cal_c()
        if m_raw_override is not None and result.m_raw_ref != 0:
            override_ratio = m_raw_override / abs(result.m_raw_ref)
            if override_ratio != 1.0:
                result.m_raw_ref *= override_ratio
                result.m_corrected *= override_ratio
                result.dose_10cm_gy *= override_ratio
                result.dose_10cm_cgy_per_mu *= override_ratio
                if result.dose_dmax_cgy_per_mu is not None:
                    result.dose_dmax_cgy_per_mu *= override_ratio

        self._last_inp = inp; self._last_result = result

        # Beam quality label — show method applied
        _method = result.pdd10x_method
        _tag = " [Eq.15]" if _method == "addendum_eq15" else (" [FFF]" if _method == "fff_direct" else "")
        self.lbl_pdd10x.setText(f"{result.pdd10x:.2f} %{_tag}")
        self.lbl_kq.setText(f"{result.k_q:.3f}")
        self._show_results_photon(result)

    def _calc_electron(self):
        from ...physics.tg51_electron import ElectronCalibrationInput, calculate_electron
        from ...physics.chamber_data import list_electron_chambers

        # M⁺ average is ALWAYS used for correction factors (P_pol, P_ion, etc.)
        m_pos  = self.row_mpos.get_average_c()
        m_neg  = self.row_mneg.get_average_c()
        m_high = self._get_mhigh_c()
        m_low  = self.row_mlow.get_average_c()
        missing = [n for n, v in [("M+", m_pos), ("M-", m_neg), ("M_H", m_high), ("M_L", m_low)] if v is None]
        if missing:
            raise ValueError(f"Enter readings: {', '.join(missing)}")

        i50_text = self.txt_i50.text().strip()
        if not i50_text:
            return
        i50 = float(i50_text)

        pdd_tmr = _safe_float(self.txt_pdd_tmr.text()) or 0.0
        m_leak  = (_safe_float(self.txt_mleak.text()) or 0.0) * _NC_TO_C
        is_sad  = self.rdo_sad.isChecked()

        from ...physics.chamber_data import _PHOTON_KQ_ALIASES
        model = self._setup.chamber_model.lower()
        model = _PHOTON_KQ_ALIASES.get(model, model)   # resolve "standard imaging a12" → "exradin a12" etc.
        avail = list_electron_chambers()
        if model not in avail:
            model = avail[0] if avail else model

        inp = ElectronCalibrationInput(
            chamber_model=model,
            n_dw_gy_per_c=self._setup.n_dw_gy_per_c,
            p_elec=self._setup.p_elec,
            temperature_c=self.spn_temp.value(),
            pressure_kpa=self.spn_pressure.value(),
            energy_mev=self._beam.energy_mv,
            i50_cm=i50,
            m_raw_pos=m_pos, m_raw_neg=m_neg,
            calibration_polarity="pos" if self.rdo_calpos.isChecked() else "neg",
            v_high=self.spn_vh.value(), v_low=self.spn_vl.value(),
            m_raw_high=m_high, m_raw_low=m_low,
            m_leak=m_leak, p_ion_override=self._p_ion_override,
            monitor_units=self.spn_mu.value(),
            clinical_pdd_at_dref_pct=pdd_tmr if pdd_tmr > 0 else None,
        )
        result = calculate_electron(inp)

        # Post-calc M_raw override: scales dose only, correction factors unchanged.
        m_raw_override = self._get_mraw_cal_c()
        if m_raw_override is not None and result.m_raw_ref != 0:
            override_ratio = m_raw_override / abs(result.m_raw_ref)
            if override_ratio != 1.0:
                result.m_raw_ref *= override_ratio
                result.m_corrected *= override_ratio
                result.dose_dref_gy *= override_ratio
                result.dose_dref_cgy_per_mu *= override_ratio
                if result.dose_dmax_cgy_per_mu is not None:
                    result.dose_dmax_cgy_per_mu *= override_ratio

        self._last_inp = inp; self._last_result = result

        self._show_results_electron(result)

    # ------------------------------------------------------------------
    # Result display
    # ------------------------------------------------------------------

    @staticmethod
    def _pct_err(dose: float) -> str:
        err = (dose - 1.000) * 100.0
        sign = "+" if err >= 0 else ""
        return f"{sign}{err:.1f}%"

    def _show_results_photon(self, result):
        self.lbl_res_ptp.setText(f"{result.p_tp:.3f}")
        self.lbl_res_ppol.setText(f"{result.p_pol:.3f}")
        self.lbl_res_pion.setText(f"{result.p_ion:.3f}")
        self.lbl_res_pleak.setText(f"{result.p_leak:.3f}")
        self.lbl_res_kq.setText(f"{result.k_q:.3f}")
        self.lbl_mcorr.setText(f"{result.m_corrected:.3E} C")
        self.lbl_dose.setText(f"{result.dose_10cm_cgy_per_mu:.3f} cGy/MU")
        if result.dose_dmax_cgy_per_mu is not None:
            dmax = result.dose_dmax_cgy_per_mu
            self.lbl_dmax.setText(f"{dmax:.3f} cGy/MU  ({self._pct_err(dmax)})")
        else:
            self.lbl_dmax.setText("—")
        self.lbl_warnings.setText("[!]  " + "\n[!]  ".join(result.warnings) if result.warnings else "")
        self.btn_save.setEnabled(True); self.btn_pdf.setEnabled(True)

    def _show_results_electron(self, result):
        self.lbl_res_ptp.setText(f"{result.p_tp:.3f}")
        self.lbl_res_ppol.setText(f"{result.p_pol:.3f}")
        self.lbl_res_pion.setText(f"{result.p_ion:.3f}")
        self.lbl_res_pleak.setText(f"{result.p_leak:.3f}")
        self.lbl_res_kq.setText(
            f"{result.k_q:.3f}  (k_Qecal={result.k_qecal:.3f}, k'_Q={result.k_q_prime:.3f})"
        )
        self.lbl_mcorr.setText(f"{result.m_corrected:.3E} C")
        self.lbl_dose.setText(f"{result.dose_dref_cgy_per_mu:.3f} cGy/MU")
        if result.dose_dmax_cgy_per_mu is not None:
            dmax = result.dose_dmax_cgy_per_mu
            self.lbl_dmax.setText(f"{dmax:.3f} cGy/MU  ({self._pct_err(dmax)})")
        else:
            self.lbl_dmax.setText("—")
        self.lbl_warnings.setText("[!]  " + "\n[!]  ".join(result.warnings) if result.warnings else "")
        self.btn_save.setEnabled(True); self.btn_pdf.setEnabled(True)

    # ------------------------------------------------------------------
    # Jaffé / helpers
    # ------------------------------------------------------------------

    def _enter_mmhg(self):
        val, ok = QInputDialog.getDouble(self, "Pressure (mmHg)", "mmHg:", 760.0, 500.0, 900.0, 1)
        if ok:
            from ...physics.corrections import mmhg_to_kpa
            self.spn_pressure.setValue(mmhg_to_kpa(val))

    def _open_jaffe(self):
        from ..dialogs.jaffe_dialog import JaffePlotDialog
        dlg = JaffePlotDialog(v_h=self.spn_vh.value(), on_accept=self._apply_jaffe, parent=self)
        dlg.exec()

    def _apply_jaffe(self, p_ion: float):
        self._p_ion_override = p_ion
        self.lbl_jaffe.setText(f"Jaffé: {p_ion:.3f}")
        self.lbl_pion.setText(f"{p_ion:.3f}  [Jaffé]")
        self._try_auto_calc()

    # ------------------------------------------------------------------
    # State serialisation — full field snapshot for auto-save / restore
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return a JSON-serialisable dict of every field in this tab."""
        state = {
            "temperature":  self.spn_temp.value(),
            "pressure":     self.spn_pressure.value(),
            "mu":           self.spn_mu.value(),
            "setup":        "SAD" if self.rdo_sad.isChecked() else "SSD",
            "distance":     self.spn_dist.value(),
            "notes":        self.txt_notes.text(),
            "cal_polarity": "pos" if self.rdo_calpos.isChecked() else "neg",
            "m_pos":        [f.text() for f in self.row_mpos._fields],
            "m_neg":        [f.text() for f in self.row_mneg._fields],
            "m_high":       self.txt_mhigh.text(),
            "m_low":        [f.text() for f in self.row_mlow._fields],
            "v_h":          self.spn_vh.value(),
            "v_l":          self.spn_vl.value(),
            "m_raw_cal":    self.txt_mraw_cal.text(),
            "mraw_adjusted": self._mraw_adjusted,
            "m_leak":       self.txt_mleak.text(),
            "pdd_tmr":      self.txt_pdd_tmr.text(),
            "p_ion_override": self._p_ion_override,
            "has_result":   self._last_result is not None,
        }
        if self._beam.modality == "photon":
            state["pdd10"]    = self.txt_pdd10.text()
            if self.spn_prp is not None:
                state["p_rp"] = self.spn_prp.value()
        else:
            state["i50"] = self.txt_i50.text()
            state["cone"] = self.cmb_cone.currentText()
        return state

    def restore_state(self, state: dict):
        """Restore all fields from a previously saved state dict."""
        self._restoring = True
        try:
            self.spn_temp.setValue(state.get("temperature", 22.0))
            self.spn_pressure.setValue(state.get("pressure", 101.33))
            self.spn_mu.setValue(state.get("mu", 200.0))
            dist = state.get("distance", 100.0)
            if state.get("setup") == "SAD":
                self.rdo_sad.setChecked(True)
            else:
                self.rdo_ssd.setChecked(True)
            self.spn_dist.setValue(dist)
            self.txt_notes.setText(state.get("notes", ""))

            if state.get("cal_polarity") == "pos":
                self.rdo_calpos.setChecked(True)
            else:
                self.rdo_calneg.setChecked(True)

            for i, f in enumerate(self.row_mpos._fields):
                f.setText(state["m_pos"][i] if "m_pos" in state and i < len(state["m_pos"]) else "")
            for i, f in enumerate(self.row_mneg._fields):
                f.setText(state["m_neg"][i] if "m_neg" in state and i < len(state["m_neg"]) else "")

            self.txt_mhigh.setText(state.get("m_high", ""))
            for i, f in enumerate(self.row_mlow._fields):
                f.setText(state["m_low"][i] if "m_low" in state and i < len(state["m_low"]) else "")

            self.spn_vh.setValue(state.get("v_h", 300.0))
            self.spn_vl.setValue(state.get("v_l", 150.0))
            # Restore adjustment flag BEFORE setting text so _update_ppol won't overwrite it
            self._mraw_adjusted = state.get("mraw_adjusted", False)
            self.txt_mraw_cal.setText(state.get("m_raw_cal", ""))
            self._update_mraw_hint()
            self.txt_mleak.setText(state.get("m_leak", "0"))
            self.txt_pdd_tmr.setText(state.get("pdd_tmr", "0"))
            if self._beam.modality == "electron" and "cone" in state:
                idx = self.cmb_cone.findText(state["cone"])
                if idx >= 0:
                    self.cmb_cone.setCurrentIndex(idx)
            self._p_ion_override = state.get("p_ion_override")
            if self._p_ion_override is not None:
                self.lbl_pion.setText(f"{self._p_ion_override:.3f}  [Jaffé]")
                self.lbl_jaffe.setText(f"Jaffé: {self._p_ion_override:.3f}")

            if self._beam.modality == "photon":
                self.txt_pdd10.setText(state.get("pdd10", ""))
                if self.spn_prp is not None:
                    saved_prp = state.get("p_rp", None)
                    # Only restore if physicist explicitly set a non-default value;
                    # otherwise keep the auto-filled recommended value from the table.
                    if saved_prp is not None and abs(saved_prp - 1.0) > 1e-6:
                        self.spn_prp.setValue(saved_prp)
            else:
                self.txt_i50.setText(state.get("i50", ""))

        finally:
            self._restoring = False

        # Trigger a fresh calculation with the restored values
        self._update_ptp()
        self._update_ppol()
        self._update_pion()
        self._try_auto_calc()

    # ------------------------------------------------------------------
    # Save / PDF
    # ------------------------------------------------------------------

    def _save(self):
        from ...models import db as db_mod
        if not db_mod.is_ready():
            QMessageBox.warning(self, "DB Unavailable", "Database not initialised."); return
        try:
            if self._beam.modality == "photon":
                rec_id = db_mod.save_photon_record(
                    self._last_inp, self._last_result, physicist=self._setup.physicist,
                    notes=self.txt_notes.text()
                )
            else:
                rec_id = db_mod.save_electron_record(
                    self._last_inp, self._last_result, physicist=self._setup.physicist,
                    notes=self.txt_notes.text()
                )
            QMessageBox.information(self, "Saved", f"Record #{rec_id} saved to history.")
            self.btn_save.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _pdf_report(self):
        import datetime
        from PySide6.QtWidgets import QFileDialog
        energy = f"{self._beam.energy_mv:.0f}"
        mod = self._beam.modality.title()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report",
            f"TG51_{mod}_{energy}_{self._setup.linac_name}_{ts}.pdf", "PDF Files (*.pdf)"
        )
        if not path: return
        if not path.lower().endswith(".pdf"): path += ".pdf"
        try:
            s = self._setup
            common = dict(
                institution=s.center_name,
                physicist=s.physicist,
                machine=f"{s.linac_name}  ({s.linac_model})",
                chamber_sn=s.chamber_sn,
                electrometer_model=s.electrometer_model,
                electrometer_sn=s.electrometer_sn,
                r_cav_cm=s.r_cav_cm,
                notes=self.txt_notes.text(),
                session_date=str(s.session_date),
            )
            if self._beam.modality == "photon":
                from ...reports.pdf_generator import generate_photon_report
                generate_photon_report(self._last_inp, self._last_result, path,
                                       mraw_adjusted=self._mraw_adjusted, **common)
            else:
                from ...reports.pdf_generator import generate_electron_report
                generate_electron_report(self._last_inp, self._last_result, path,
                                         mraw_adjusted=self._mraw_adjusted, **common)
            QMessageBox.information(self, "PDF Saved", f"Report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", str(e))



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hdr_lbl(text: str, width: int) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(width)
    lbl.setStyleSheet("color:#555; font-size:10px; font-weight:bold;")
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def _safe_float(text: str) -> Optional[float]:
    try:
        return float(text)
    except (ValueError, TypeError):
        return None
