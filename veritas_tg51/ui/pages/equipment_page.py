"""equipment_page.py — Equipment and machine management (CRUD)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate


class EquipmentPage(QWidget):
    """Tabbed CRUD interface for Institutions, Linacs, Beams, Chambers, Electrometers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #1B2A4A;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 10, 16, 10)
        lbl = QLabel("Equipment Manager")
        lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        h_lay.addWidget(lbl)
        h_lay.addStretch()
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_centers = _CentersTab()
        self.tab_linacs = _LinacsTab()
        self.tab_beams = _BeamsTab()
        self.tab_chambers = _ChambersTab()
        self.tab_electrometers = _ElectrometersTab()

        self.tabs.addTab(self.tab_centers, "Institutions")
        self.tabs.addTab(self.tab_linacs, "Linacs")
        self.tabs.addTab(self.tab_beams, "Beams")
        self.tabs.addTab(self.tab_chambers, "Ion Chambers")
        self.tabs.addTab(self.tab_electrometers, "Electrometers")

        # Refresh downstream tabs when parent tabs change data
        self.tab_centers.data_changed.connect(self.tab_linacs.refresh)
        self.tab_linacs.data_changed.connect(self.tab_beams.refresh)

        layout.addWidget(self.tabs)

    def showEvent(self, event):
        super().showEvent(event)
        for i in range(self.tabs.count()):
            self.tabs.widget(i).refresh()


# ---------------------------------------------------------------------------
# Generic table tab base
# ---------------------------------------------------------------------------

class _TableTab(QWidget):
    """Base class: toolbar (Add/Edit/Delete + Refresh) + QTableWidget."""

    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, columns: list[str], parent=None):
        super().__init__(parent)
        self._cols = columns
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_add.setFixedWidth(70)
        self.btn_add.clicked.connect(self._add)
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setFixedWidth(70)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setFixedWidth(70)
        self.btn_delete.clicked.connect(self._delete)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedWidth(80)
        btn_refresh.clicked.connect(self.refresh)
        self.lbl_count = QLabel("0 rows")
        self.lbl_count.setStyleSheet("color: #555; font-size: 12px;")

        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(btn_refresh)
        toolbar.addStretch()
        toolbar.addWidget(self.lbl_count)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._edit)
        layout.addWidget(self.table)

    def _selected_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _set_row(self, row: int, values: list):
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val) if val is not None else "")
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, col, item)

    def _update_count(self):
        self.lbl_count.setText(f"{self.table.rowCount()} rows")

    def refresh(self):
        raise NotImplementedError

    def _add(self):
        raise NotImplementedError

    def _edit(self):
        raise NotImplementedError

    def _delete(self):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Centers tab
# ---------------------------------------------------------------------------

class _CentersTab(_TableTab):
    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, parent=None):
        super().__init__(["ID", "Institution Name", "Health System / Network", "Physicist", "Created"], parent)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 140)

    def refresh(self):
        from ...models.db import get_session, is_ready
        from ...models.entities import Center
        from sqlalchemy import select

        if not is_ready():
            return

        session = get_session()
        try:
            rows = session.scalars(select(Center).order_by(Center.id)).all()
            self.table.setRowCount(0)
            for rec in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self._set_row(r, [
                    rec.id, rec.name, rec.institution or "",
                    rec.physicist or "",
                    rec.created_at.strftime("%Y-%m-%d") if rec.created_at else "",
                ])
            self._update_count()
        finally:
            session.close()

    def _add(self):
        dlg = _CenterDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            from ...models.db import get_session
            from ...models.entities import Center
            session = get_session()
            try:
                obj = Center(**dlg.get_data())
                session.add(obj)
                session.commit()
            finally:
                session.close()
            self.refresh()
            self.data_changed.emit()

    def _edit(self):
        rec_id = self._selected_id()
        if rec_id is None:
            return
        from ...models.db import get_session
        from ...models.entities import Center
        session = get_session()
        try:
            obj = session.get(Center, rec_id)
            if not obj:
                return
            data = {"name": obj.name, "institution": obj.institution, "physicist": obj.physicist}
        finally:
            session.close()

        dlg = _CenterDialog(data=data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            session = get_session()
            try:
                obj = session.get(Center, rec_id)
                for k, v in dlg.get_data().items():
                    setattr(obj, k, v)
                session.commit()
            finally:
                session.close()
            self.refresh()
            self.data_changed.emit()

    def _delete(self):
        rec_id = self._selected_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        if QMessageBox.question(
            self, "Confirm Delete", f"Delete Institution #{rec_id} and all its machines?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from ...models.db import get_session
        from ...models.entities import Center
        session = get_session()
        try:
            obj = session.get(Center, rec_id)
            if obj:
                session.delete(obj)
                session.commit()
        finally:
            session.close()
        self.refresh()
        self.data_changed.emit()


class _CenterDialog(QDialog):
    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Institution")
        self.setMinimumWidth(400)
        form = QFormLayout(self)
        self.txt_name = QLineEdit(data.get("name", "") if data else "")
        self.txt_name.setPlaceholderText("e.g. Franciscan Health Indianapolis")
        self.txt_institution = QLineEdit(data.get("institution", "") if data else "")
        self.txt_institution.setPlaceholderText("e.g. Franciscan Health  (optional)")
        self.txt_physicist = QLineEdit(data.get("physicist", "") if data else "")
        form.addRow("Institution name *:", self.txt_name)
        form.addRow("Health system / network:", self.txt_institution)
        form.addRow("Physicist:", self.txt_physicist)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Required", "Institution name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.txt_name.text().strip(),
            "institution": self.txt_institution.text().strip() or None,
            "physicist": self.txt_physicist.text().strip() or None,
        }


# ---------------------------------------------------------------------------
# Linacs tab
# ---------------------------------------------------------------------------

class _LinacsTab(_TableTab):
    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, parent=None):
        super().__init__(["ID", "Center", "Manufacturer", "Model", "Name", "S/N", "Notes"], parent)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 100)

    def refresh(self):
        from ...models.db import get_session, is_ready
        from ...models.entities import Linac, Center
        from sqlalchemy import select

        if not is_ready():
            return

        session = get_session()
        try:
            rows = session.scalars(select(Linac).order_by(Linac.id)).all()
            self.table.setRowCount(0)
            for rec in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                center_name = rec.center.name if rec.center else str(rec.center_id)
                self._set_row(r, [
                    rec.id, center_name, rec.manufacturer, rec.model,
                    rec.name, rec.serial_number or "", rec.notes or "",
                ])
            self._update_count()
        finally:
            session.close()

    def _add(self):
        centers = self._get_centers()
        if not centers:
            QMessageBox.warning(self, "No Centers", "Add a Center first.")
            return
        dlg = _LinacDialog(centers=centers, parent=self)
        if dlg.exec() == QDialog.Accepted:
            from ...models.db import get_session
            from ...models.entities import Linac
            session = get_session()
            try:
                session.add(Linac(**dlg.get_data()))
                session.commit()
            finally:
                session.close()
            self.refresh()
            self.data_changed.emit()

    def _edit(self):
        rec_id = self._selected_id()
        if rec_id is None:
            return
        centers = self._get_centers()
        from ...models.db import get_session
        from ...models.entities import Linac
        session = get_session()
        try:
            obj = session.get(Linac, rec_id)
            if not obj:
                return
            data = {
                "center_id": obj.center_id, "manufacturer": obj.manufacturer,
                "model": obj.model, "name": obj.name,
                "serial_number": obj.serial_number, "notes": obj.notes,
            }
        finally:
            session.close()
        dlg = _LinacDialog(centers=centers, data=data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            session = get_session()
            try:
                obj = session.get(Linac, rec_id)
                for k, v in dlg.get_data().items():
                    setattr(obj, k, v)
                session.commit()
            finally:
                session.close()
            self.refresh()
            self.data_changed.emit()

    def _delete(self):
        rec_id = self._selected_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        if QMessageBox.question(
            self, "Confirm Delete", f"Delete Linac #{rec_id} and all its beams/sessions?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from ...models.db import get_session
        from ...models.entities import Linac
        session = get_session()
        try:
            obj = session.get(Linac, rec_id)
            if obj:
                session.delete(obj)
                session.commit()
        finally:
            session.close()
        self.refresh()
        self.data_changed.emit()

    def _get_centers(self) -> list[tuple[int, str]]:
        from ...models.db import get_session, is_ready
        from ...models.entities import Center
        from sqlalchemy import select
        if not is_ready():
            return []
        session = get_session()
        try:
            return [(c.id, c.name) for c in session.scalars(select(Center).order_by(Center.name)).all()]
        finally:
            session.close()


class _LinacDialog(QDialog):
    def __init__(self, centers: list[tuple[int, str]], data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Linac")
        self.setMinimumWidth(380)
        form = QFormLayout(self)
        self.cmb_center = QComboBox()
        for cid, cname in centers:
            self.cmb_center.addItem(cname, cid)
        if data and data.get("center_id"):
            for i in range(self.cmb_center.count()):
                if self.cmb_center.itemData(i) == data["center_id"]:
                    self.cmb_center.setCurrentIndex(i)
        self.txt_manufacturer = QLineEdit(data.get("manufacturer", "") if data else "")
        self.txt_model = QLineEdit(data.get("model", "") if data else "")
        self.txt_name = QLineEdit(data.get("name", "") if data else "")
        self.txt_sn = QLineEdit(data.get("serial_number", "") if data else "")
        self.txt_notes = QLineEdit(data.get("notes", "") if data else "")
        form.addRow("Center *:", self.cmb_center)
        form.addRow("Manufacturer *:", self.txt_manufacturer)
        form.addRow("Model *:", self.txt_model)
        form.addRow("Name *:", self.txt_name)
        form.addRow("Serial number:", self.txt_sn)
        form.addRow("Notes:", self.txt_notes)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate(self):
        for field, name in [(self.txt_manufacturer, "Manufacturer"),
                            (self.txt_model, "Model"), (self.txt_name, "Name")]:
            if not field.text().strip():
                QMessageBox.warning(self, "Required", f"{name} is required.")
                return
        self.accept()

    def get_data(self) -> dict:
        return {
            "center_id": self.cmb_center.currentData(),
            "manufacturer": self.txt_manufacturer.text().strip(),
            "model": self.txt_model.text().strip(),
            "name": self.txt_name.text().strip(),
            "serial_number": self.txt_sn.text().strip() or None,
            "notes": self.txt_notes.text().strip() or None,
        }


# ---------------------------------------------------------------------------
# Beams tab
# ---------------------------------------------------------------------------

class _BeamsTab(_TableTab):
    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, parent=None):
        super().__init__(["ID", "Linac", "Modality", "Energy", "FFF", "Label"], parent)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 50)

    def refresh(self):
        from ...models.db import get_session, is_ready
        from ...models.entities import BeamEnergy
        from sqlalchemy import select

        if not is_ready():
            return
        session = get_session()
        try:
            rows = session.scalars(select(BeamEnergy).order_by(BeamEnergy.id)).all()
            self.table.setRowCount(0)
            for rec in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                linac_name = rec.linac.name if rec.linac else str(rec.linac_id)
                self._set_row(r, [
                    rec.id, linac_name, rec.modality,
                    f"{rec.energy_mv:.0f}", "Yes" if rec.is_fff else "No", rec.label,
                ])
            self._update_count()
        finally:
            session.close()

    def _get_linacs(self) -> list[tuple[int, str]]:
        from ...models.db import get_session, is_ready
        from ...models.entities import Linac
        from sqlalchemy import select
        if not is_ready():
            return []
        session = get_session()
        try:
            return [(l.id, l.name) for l in session.scalars(select(Linac).order_by(Linac.name)).all()]
        finally:
            session.close()

    def _add(self):
        linacs = self._get_linacs()
        if not linacs:
            QMessageBox.warning(self, "No Linacs", "Add a Linac first.")
            return
        dlg = _BeamDialog(linacs=linacs, parent=self)
        if dlg.exec() == QDialog.Accepted:
            from ...models.db import get_session
            from ...models.entities import BeamEnergy
            session = get_session()
            try:
                session.add(BeamEnergy(**dlg.get_data()))
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _edit(self):
        rec_id = self._selected_id()
        if rec_id is None:
            return
        linacs = self._get_linacs()
        from ...models.db import get_session
        from ...models.entities import BeamEnergy
        session = get_session()
        try:
            obj = session.get(BeamEnergy, rec_id)
            if not obj:
                return
            data = {
                "linac_id": obj.linac_id, "modality": obj.modality,
                "energy_mv": obj.energy_mv, "is_fff": obj.is_fff, "label": obj.label,
                "pdd_shift_pct": obj.pdd_shift_pct,
                "clinical_pdd_pct": obj.clinical_pdd_pct,
                "i50_cm": obj.i50_cm,
            }
        finally:
            session.close()
        dlg = _BeamDialog(linacs=linacs, data=data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            session = get_session()
            try:
                obj = session.get(BeamEnergy, rec_id)
                for k, v in dlg.get_data().items():
                    setattr(obj, k, v)
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _delete(self):
        rec_id = self._selected_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        if QMessageBox.question(
            self, "Confirm Delete", f"Delete Beam #{rec_id}?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from ...models.db import get_session
        from ...models.entities import BeamEnergy
        session = get_session()
        try:
            obj = session.get(BeamEnergy, rec_id)
            if obj:
                session.delete(obj)
                session.commit()
        finally:
            session.close()
        self.refresh()


class _BeamDialog(QDialog):
    def __init__(self, linacs: list[tuple[int, str]], data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Beam Energy")
        self.setMinimumWidth(400)
        form = QFormLayout(self)
        self.cmb_linac = QComboBox()
        for lid, lname in linacs:
            self.cmb_linac.addItem(lname, lid)
        if data and data.get("linac_id"):
            for i in range(self.cmb_linac.count()):
                if self.cmb_linac.itemData(i) == data["linac_id"]:
                    self.cmb_linac.setCurrentIndex(i)
        self.cmb_modality = QComboBox()
        self.cmb_modality.addItems(["photon", "electron"])
        if data:
            self.cmb_modality.setCurrentText(data.get("modality", "photon"))
        self.spn_energy = QDoubleSpinBox()
        self.spn_energy.setRange(1, 50); self.spn_energy.setDecimals(0)
        self.spn_energy.setValue(data.get("energy_mv", 6) if data else 6)
        self.chk_fff = QCheckBox("FFF (Flattening-Filter-Free)")
        if data:
            self.chk_fff.setChecked(data.get("is_fff", False))
        self.txt_label = QLineEdit(data.get("label", "") if data else "")
        self.txt_label.setPlaceholderText("e.g. 6 MV, 10 MV FFF, 9 MeV")

        # Photon-only defaults
        self.spn_pdd_shift = QDoubleSpinBox()
        self.spn_pdd_shift.setRange(0, 100); self.spn_pdd_shift.setDecimals(2)
        self.spn_pdd_shift.setSuffix(" %"); self.spn_pdd_shift.setSpecialValueText("—")
        self.spn_pdd_shift.setValue(data.get("pdd_shift_pct") or 0.0 if data else 0.0)

        self.spn_clinical_pdd = QDoubleSpinBox()
        self.spn_clinical_pdd.setRange(0, 100); self.spn_clinical_pdd.setDecimals(2)
        self.spn_clinical_pdd.setSuffix(" %"); self.spn_clinical_pdd.setSpecialValueText("—")
        self.spn_clinical_pdd.setValue(data.get("clinical_pdd_pct") or 0.0 if data else 0.0)

        # Electron-only defaults
        self.spn_i50 = QDoubleSpinBox()
        self.spn_i50.setRange(0, 20); self.spn_i50.setDecimals(2)
        self.spn_i50.setSuffix(" cm"); self.spn_i50.setSpecialValueText("—")
        self.spn_i50.setValue(data.get("i50_cm") or 0.0 if data else 0.0)

        # Labels we'll show/hide
        self._lbl_pdd_shift = QLabel("%dd shift:")
        self._lbl_clinical_pdd = QLabel("Clinical %dd:")
        self._lbl_i50 = QLabel("I_50:")

        form.addRow("Linac *:", self.cmb_linac)
        form.addRow("Modality *:", self.cmb_modality)
        form.addRow("Energy (MV/MeV) *:", self.spn_energy)
        form.addRow("", self.chk_fff)
        form.addRow("Label *:", self.txt_label)
        form.addRow(self._lbl_pdd_shift, self.spn_pdd_shift)
        form.addRow(self._lbl_clinical_pdd, self.spn_clinical_pdd)
        form.addRow(self._lbl_i50, self.spn_i50)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        self.cmb_modality.currentTextChanged.connect(self._update_visibility)
        self._update_visibility(self.cmb_modality.currentText())

    def _update_visibility(self, modality: str):
        photon = modality == "photon"
        for w in (self._lbl_pdd_shift, self.spn_pdd_shift,
                  self._lbl_clinical_pdd, self.spn_clinical_pdd):
            w.setVisible(photon)
        for w in (self._lbl_i50, self.spn_i50):
            w.setVisible(not photon)

    def _validate(self):
        if not self.txt_label.text().strip():
            QMessageBox.warning(self, "Required", "Label is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        modality = self.cmb_modality.currentText()
        d = {
            "linac_id":  self.cmb_linac.currentData(),
            "modality":  modality,
            "energy_mv": self.spn_energy.value(),
            "is_fff":    self.chk_fff.isChecked(),
            "label":     self.txt_label.text().strip(),
        }
        if modality == "photon":
            d["pdd_shift_pct"]   = self.spn_pdd_shift.value() or None
            d["clinical_pdd_pct"] = self.spn_clinical_pdd.value() or None
        else:
            d["i50_cm"] = self.spn_i50.value() or None
        return d


# ---------------------------------------------------------------------------
# Ion Chambers tab
# ---------------------------------------------------------------------------

class _ChambersTab(_TableTab):
    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, parent=None):
        super().__init__(
            ["ID", "Manufacturer", "Model", "S/N", "N_D,w (Gy/C)", "Cal. Date", "Notes"], parent,
        )
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 90)

    def refresh(self):
        from ...models.db import get_session, is_ready
        from ...models.entities import IonChamber
        from sqlalchemy import select
        if not is_ready():
            return
        session = get_session()
        try:
            rows = session.scalars(select(IonChamber).order_by(IonChamber.id)).all()
            self.table.setRowCount(0)
            for rec in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                cal_date = ""
                if rec.calibration_date:
                    try:
                        cal_date = rec.calibration_date.strftime("%Y-%m-%d")
                    except Exception:
                        cal_date = str(rec.calibration_date)
                self._set_row(r, [
                    rec.id, rec.manufacturer, rec.model,
                    rec.serial_number, f"{rec.n_dw_gy_per_c:.4g}", cal_date, rec.notes or "",
                ])
            self._update_count()
        finally:
            session.close()

    def _add(self):
        dlg = _ChamberDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            from ...models.db import get_session
            from ...models.entities import IonChamber
            session = get_session()
            try:
                session.add(IonChamber(**dlg.get_data()))
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _edit(self):
        rec_id = self._selected_id()
        if rec_id is None:
            return
        from ...models.db import get_session
        from ...models.entities import IonChamber
        session = get_session()
        try:
            obj = session.get(IonChamber, rec_id)
            if not obj:
                return
            data = {
                "manufacturer": obj.manufacturer,
                "model": obj.model, "serial_number": obj.serial_number,
                "r_cav_cm": obj.r_cav_cm, "wall_material": obj.wall_material or "",
                "volume_cc": obj.volume_cc, "is_waterproof": obj.is_waterproof,
                "n_dw_gy_per_c": obj.n_dw_gy_per_c,
                "calibration_date": obj.calibration_date,
                "calibration_lab": obj.calibration_lab or "",
                "notes": obj.notes or "",
            }
        finally:
            session.close()
        dlg = _ChamberDialog(data=data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            session = get_session()
            try:
                obj = session.get(IonChamber, rec_id)
                for k, v in dlg.get_data().items():
                    setattr(obj, k, v)
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _delete(self):
        rec_id = self._selected_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        if QMessageBox.question(
            self, "Confirm Delete", f"Delete Ion Chamber #{rec_id}?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from ...models.db import get_session
        from ...models.entities import IonChamber
        session = get_session()
        try:
            obj = session.get(IonChamber, rec_id)
            if obj:
                session.delete(obj)
                session.commit()
        finally:
            session.close()
        self.refresh()


class _ChamberDialog(QDialog):
    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ion Chamber")
        self.setMinimumWidth(400)
        form = QFormLayout(self)

        d = data or {}
        self.txt_manufacturer = QLineEdit(d.get("manufacturer", "Standard Imaging"))
        self.txt_model = QLineEdit(d.get("model", "Exradin A12"))
        self.txt_sn = QLineEdit(d.get("serial_number", ""))

        self.spn_ndw = QDoubleSpinBox()
        self.spn_ndw.setRange(1e6, 1e10)
        self.spn_ndw.setDecimals(4)
        self.spn_ndw.setValue(d.get("n_dw_gy_per_c", 5.450e7))
        self.spn_ndw.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.spn_ndw.setSuffix(" Gy/C")

        self.spn_rcav = QDoubleSpinBox()
        self.spn_rcav.setRange(0.01, 2.0)
        self.spn_rcav.setDecimals(3)
        self.spn_rcav.setValue(d.get("r_cav_cm", 0.305))
        self.spn_rcav.setSuffix(" cm")

        self.txt_wall = QLineEdit(d.get("wall_material", "C-552"))

        self.chk_waterproof = QCheckBox("Waterproof")
        self.chk_waterproof.setChecked(d.get("is_waterproof", True))

        self.de_caldate = QDateEdit()
        self.de_caldate.setCalendarPopup(True)
        self.de_caldate.setDisplayFormat("yyyy-MM-dd")
        if d.get("calibration_date"):
            try:
                import datetime
                cd = d["calibration_date"]
                if hasattr(cd, "year"):
                    self.de_caldate.setDate(QDate(cd.year, cd.month, cd.day))
                else:
                    self.de_caldate.setDate(QDate.currentDate())
            except Exception:
                self.de_caldate.setDate(QDate.currentDate())
        else:
            self.de_caldate.setDate(QDate.currentDate())

        self.txt_lab = QLineEdit(d.get("calibration_lab", ""))
        self.txt_notes = QLineEdit(d.get("notes", ""))

        form.addRow("Manufacturer *:", self.txt_manufacturer)
        form.addRow("Model *:", self.txt_model)
        form.addRow("Serial number *:", self.txt_sn)
        form.addRow("N_D,w^60Co *:", self.spn_ndw)
        form.addRow("r_cav:", self.spn_rcav)
        form.addRow("Wall material:", self.txt_wall)
        form.addRow("", self.chk_waterproof)
        form.addRow("Calibration date:", self.de_caldate)
        form.addRow("Calibration lab:", self.txt_lab)
        form.addRow("Notes:", self.txt_notes)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate(self):
        for field, name in [
            (self.txt_manufacturer, "Manufacturer"),
            (self.txt_model, "Model"),
            (self.txt_sn, "Serial number"),
        ]:
            if not field.text().strip():
                QMessageBox.warning(self, "Required", f"{name} is required.")
                return
        self.accept()

    def get_data(self) -> dict:
        import datetime
        qd = self.de_caldate.date()
        return {
            "manufacturer": self.txt_manufacturer.text().strip(),
            "model": self.txt_model.text().strip(),
            "serial_number": self.txt_sn.text().strip(),
            "n_dw_gy_per_c": self.spn_ndw.value(),
            "r_cav_cm": self.spn_rcav.value(),
            "wall_material": self.txt_wall.text().strip() or None,
            "is_waterproof": self.chk_waterproof.isChecked(),
            "calibration_date": datetime.date(qd.year(), qd.month(), qd.day()),
            "calibration_lab": self.txt_lab.text().strip() or None,
            "notes": self.txt_notes.text().strip() or None,
        }


# ---------------------------------------------------------------------------
# Electrometers tab
# ---------------------------------------------------------------------------

class _ElectrometersTab(_TableTab):
    from PySide6.QtCore import Signal
    data_changed = __import__('PySide6.QtCore', fromlist=['Signal']).Signal()

    def __init__(self, parent=None):
        super().__init__(
            ["ID", "Manufacturer", "Model", "S/N", "P_elec", "Cal. Date"], parent,
        )
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 70)

    def refresh(self):
        from ...models.db import get_session, is_ready
        from ...models.entities import Electrometer
        from sqlalchemy import select
        if not is_ready():
            return
        session = get_session()
        try:
            rows = session.scalars(select(Electrometer).order_by(Electrometer.id)).all()
            self.table.setRowCount(0)
            for rec in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                cal_date = ""
                if rec.calibration_date:
                    try:
                        cal_date = rec.calibration_date.strftime("%Y-%m-%d")
                    except Exception:
                        cal_date = str(rec.calibration_date)
                self._set_row(r, [
                    rec.id, rec.manufacturer, rec.model,
                    rec.serial_number, f"{rec.p_elec:.4f}", cal_date,
                ])
            self._update_count()
        finally:
            session.close()

    def _add(self):
        dlg = _ElectrometerDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            from ...models.db import get_session
            from ...models.entities import Electrometer
            session = get_session()
            try:
                session.add(Electrometer(**dlg.get_data()))
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _edit(self):
        rec_id = self._selected_id()
        if rec_id is None:
            return
        from ...models.db import get_session
        from ...models.entities import Electrometer
        session = get_session()
        try:
            obj = session.get(Electrometer, rec_id)
            if not obj:
                return
            data = {
                "manufacturer": obj.manufacturer,
                "model": obj.model, "serial_number": obj.serial_number,
                "p_elec": obj.p_elec, "calibration_date": obj.calibration_date,
                "calibration_lab": obj.calibration_lab or "", "notes": obj.notes or "",
            }
        finally:
            session.close()
        dlg = _ElectrometerDialog(data=data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            session = get_session()
            try:
                obj = session.get(Electrometer, rec_id)
                for k, v in dlg.get_data().items():
                    setattr(obj, k, v)
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _delete(self):
        rec_id = self._selected_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row first.")
            return
        if QMessageBox.question(
            self, "Confirm Delete", f"Delete Electrometer #{rec_id}?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        from ...models.db import get_session
        from ...models.entities import Electrometer
        session = get_session()
        try:
            obj = session.get(Electrometer, rec_id)
            if obj:
                session.delete(obj)
                session.commit()
        finally:
            session.close()
        self.refresh()


class _ElectrometerDialog(QDialog):
    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Electrometer")
        self.setMinimumWidth(360)
        form = QFormLayout(self)
        d = data or {}
        self.txt_manufacturer = QLineEdit(d.get("manufacturer", ""))
        self.txt_model = QLineEdit(d.get("model", ""))
        self.txt_sn = QLineEdit(d.get("serial_number", ""))
        self.spn_pelec = QDoubleSpinBox()
        self.spn_pelec.setRange(0.95, 1.05)
        self.spn_pelec.setDecimals(4)
        self.spn_pelec.setValue(d.get("p_elec", 1.0))
        self.de_caldate = QDateEdit()
        self.de_caldate.setCalendarPopup(True)
        self.de_caldate.setDisplayFormat("yyyy-MM-dd")
        if d.get("calibration_date"):
            try:
                cd = d["calibration_date"]
                if hasattr(cd, "year"):
                    self.de_caldate.setDate(QDate(cd.year, cd.month, cd.day))
                else:
                    self.de_caldate.setDate(QDate.currentDate())
            except Exception:
                self.de_caldate.setDate(QDate.currentDate())
        else:
            self.de_caldate.setDate(QDate.currentDate())
        self.txt_lab = QLineEdit(d.get("calibration_lab", ""))
        self.txt_notes = QLineEdit(d.get("notes", ""))

        form.addRow("Manufacturer *:", self.txt_manufacturer)
        form.addRow("Model *:", self.txt_model)
        form.addRow("Serial number *:", self.txt_sn)
        form.addRow("P_elec:", self.spn_pelec)
        form.addRow("Calibration date:", self.de_caldate)
        form.addRow("Calibration lab:", self.txt_lab)
        form.addRow("Notes:", self.txt_notes)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _validate(self):
        for field, name in [
            (self.txt_manufacturer, "Manufacturer"),
            (self.txt_model, "Model"),
            (self.txt_sn, "Serial number"),
        ]:
            if not field.text().strip():
                QMessageBox.warning(self, "Required", f"{name} is required.")
                return
        self.accept()

    def get_data(self) -> dict:
        import datetime
        qd = self.de_caldate.date()
        return {
            "manufacturer": self.txt_manufacturer.text().strip(),
            "model": self.txt_model.text().strip(),
            "serial_number": self.txt_sn.text().strip(),
            "p_elec": self.spn_pelec.value(),
            "calibration_date": datetime.date(qd.year(), qd.month(), qd.day()),
            "calibration_lab": self.txt_lab.text().strip() or None,
            "notes": self.txt_notes.text().strip() or None,
        }
