"""
new_session_dialog.py — Session setup wizard.

Collects: Site → Treatment Machine → Ion Chamber → Electrometer → Operator.
Returns a SessionSetup dataclass used to build the SessionPage.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


@dataclass
class SessionSetup:
    center_id: int
    center_name: str
    linac_id: int
    linac_name: str
    linac_model: str
    linac_sn: str
    chamber_id: int
    chamber_model: str
    chamber_sn: str
    n_dw_gy_per_c: float
    r_cav_cm: float
    electrometer_id: int
    electrometer_model: str
    electrometer_sn: str
    p_elec: float
    physicist: str
    session_date: datetime.date
    chamber_calibration_date: Optional[datetime.date] = None
    electrometer_calibration_date: Optional[datetime.date] = None


class NewSessionDialog(QDialog):
    """Select site, machine, instruments and operator for a new session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Calibration Session")
        self.setMinimumWidth(480)
        self.setup: Optional[SessionSetup] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── Site & Machine ──
        site_grp = QGroupBox("Site & Treatment Machine")
        site_form = QFormLayout(site_grp)
        site_form.setSpacing(10)

        self.cmb_center = QComboBox()
        self.cmb_center.currentIndexChanged.connect(self._on_center_changed)
        site_form.addRow("Center:", self.cmb_center)

        self.cmb_linac = QComboBox()
        site_form.addRow("Treatment machine:", self.cmb_linac)

        layout.addWidget(site_grp)

        # ── Instrumentation ──
        inst_grp = QGroupBox("Instrumentation")
        inst_form = QFormLayout(inst_grp)
        inst_form.setSpacing(10)

        self.cmb_chamber = QComboBox()
        inst_form.addRow("Ion chamber:", self.cmb_chamber)

        self.cmb_electrometer = QComboBox()
        inst_form.addRow("Electrometer:", self.cmb_electrometer)

        layout.addWidget(inst_grp)

        # ── Session info ──
        info_grp = QGroupBox("Session Information")
        info_form = QFormLayout(info_grp)
        info_form.setSpacing(10)

        self.txt_physicist = QLineEdit()
        self.txt_physicist.setPlaceholderText("Name of performing physicist")
        info_form.addRow("Physicist / operator:", self.txt_physicist)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        from PySide6.QtCore import QDate
        self.date_edit.setDate(QDate.currentDate())
        info_form.addRow("Session date:", self.date_edit)

        layout.addWidget(info_grp)

        # ── No data hint ──
        self.lbl_hint = QLabel(
            "ⓘ  No equipment found in database. "
            "Add centers, machines and instruments in the Equipment page first."
        )
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color: #7D6608; font-size: 11px;")
        self.lbl_hint.hide()
        layout.addWidget(self.lbl_hint)

        # ── Buttons ──
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Load data
        self._load_centers()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_centers(self):
        from ...models.db import get_session
        from ...models.entities import Center

        self.cmb_center.clear()
        db = get_session()
        try:
            centers = db.query(Center).order_by(Center.name).all()
        finally:
            db.close()

        if not centers:
            self.lbl_hint.show()
            return

        self.lbl_hint.hide()
        self._centers = centers
        for c in centers:
            self.cmb_center.addItem(c.name, userData=c.id)

    def _on_center_changed(self, idx: int):
        if idx < 0:
            return
        center_id = self.cmb_center.currentData()
        self._load_linacs(center_id)
        self._load_instruments(center_id)

    def _load_linacs(self, center_id: int):
        from ...models.db import get_session
        from ...models.entities import Linac

        self.cmb_linac.clear()
        db = get_session()
        try:
            linacs = db.query(Linac).filter(Linac.center_id == center_id).order_by(Linac.name).all()
        finally:
            db.close()

        self._linacs = linacs
        for l in linacs:
            display = f"{l.name}  ({l.manufacturer} {l.model})"
            self.cmb_linac.addItem(display, userData=l.id)

    def _load_instruments(self, center_id: int):
        from ...models.db import get_session
        from ...models.entities import IonChamber, Electrometer

        self.cmb_chamber.clear()
        self.cmb_electrometer.clear()
        db = get_session()
        try:
            chambers = (
                db.query(IonChamber)
                .filter(IonChamber.center_id == center_id)
                .order_by(IonChamber.model)
                .all()
            )
            electrometers = (
                db.query(Electrometer)
                .filter(Electrometer.center_id == center_id)
                .order_by(Electrometer.model)
                .all()
            )
        finally:
            db.close()

        self._chambers = chambers
        self._electrometers = electrometers

        for ch in chambers:
            label = f"{ch.model}  SN:{ch.serial_number}  N_D,w={ch.n_dw_gy_per_c:.3E} Gy/C"
            self.cmb_chamber.addItem(label, userData=ch.id)

        for el in electrometers:
            label = f"{el.model}  SN:{el.serial_number}  P_elec={el.p_elec:.4f}"
            self.cmb_electrometer.addItem(label, userData=el.id)

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _on_accept(self):
        if self.cmb_center.count() == 0:
            QMessageBox.warning(self, "No Data",
                                "Please add a center in the Equipment page first.")
            return
        if self.cmb_linac.count() == 0:
            QMessageBox.warning(self, "No Machine",
                                "Please add a treatment machine for this center first.")
            return
        if self.cmb_chamber.count() == 0:
            QMessageBox.warning(self, "No Chamber",
                                "Please add an ion chamber for this center first.")
            return
        if self.cmb_electrometer.count() == 0:
            QMessageBox.warning(self, "No Electrometer",
                                "Please add an electrometer for this center first.")
            return

        center_id = self.cmb_center.currentData()
        linac_id = self.cmb_linac.currentData()
        chamber_id = self.cmb_chamber.currentData()
        electrometer_id = self.cmb_electrometer.currentData()

        from ...models.db import get_session
        from ...models.entities import Center, Linac, IonChamber, Electrometer

        qdate = self.date_edit.date()
        session_date = datetime.date(qdate.year(), qdate.month(), qdate.day())

        db = get_session()
        try:
            center = db.get(Center, center_id)
            linac = db.get(Linac, linac_id)
            chamber = db.get(IonChamber, chamber_id)
            electrometer = db.get(Electrometer, electrometer_id)

            self.setup = SessionSetup(
                chamber_calibration_date=chamber.calibration_date,
                electrometer_calibration_date=electrometer.calibration_date,
                center_id=center_id,
                center_name=center.name,
                linac_id=linac_id,
                linac_name=linac.name,
                linac_model=f"{linac.manufacturer} {linac.model}",
                linac_sn=linac.serial_number or "",
                chamber_id=chamber_id,
                chamber_model=chamber.model,
                chamber_sn=chamber.serial_number,
                n_dw_gy_per_c=chamber.n_dw_gy_per_c,
                r_cav_cm=chamber.r_cav_cm,
                electrometer_id=electrometer_id,
                electrometer_model=electrometer.model,
                electrometer_sn=electrometer.serial_number,
                p_elec=electrometer.p_elec,
                physicist=self.txt_physicist.text().strip(),
                session_date=session_date,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load session data:\n{exc}")
            return
        finally:
            db.close()

        self.accept()
