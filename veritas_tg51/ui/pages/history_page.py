"""history_page.py — Session history browser."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _export_record_pdf(rec, parent_widget):
    """Prompt for a save path and generate a PDF report from *rec*."""
    modality = rec.modality.title()
    energy = f"{rec.energy_nominal:.0f}"
    default_name = f"TG51_{modality}_{energy}_record{rec.id}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent_widget,
        "Save PDF Report",
        default_name,
        "PDF Files (*.pdf)",
    )
    if not path:
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    try:
        from ...reports.pdf_generator import generate_report_from_record
        generate_report_from_record(rec, path)
        QMessageBox.information(parent_widget, "PDF Saved", f"Report saved to:\n{path}")
    except Exception as exc:
        QMessageBox.critical(parent_widget, "Export Failed", str(exc))


# Columns in the history table
_COLS = [
    "ID", "Date/Time", "Modality", "Energy", "Chamber",
    "k_Q", "P_TP", "P_pol", "P_ion",
    "Dose (cGy/MU)", "Physicist", "Warnings",
]
_COL_IDX = {name: i for i, name in enumerate(_COLS)}


class HistoryPage(QWidget):
    """Browse and manage saved calibration records and sessions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #1B2A4A;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 10, 16, 10)
        lbl = QLabel("Session History")
        lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        h_lay.addWidget(lbl)
        h_lay.addStretch()
        layout.addWidget(header)

        # Tab widget: Sessions (full worksheets) | Records (individual beam results)
        self.inner_tabs = QTabWidget()
        self.inner_tabs.setDocumentMode(True)
        layout.addWidget(self.inner_tabs)

        # ── Tab 1: Saved Sessions ──────────────────────────────────────
        sessions_widget = QWidget()
        s_lay = QVBoxLayout(sessions_widget)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(0)

        s_bar = QWidget()
        s_bar.setStyleSheet("background-color: #F0F3F4; border-bottom: 1px solid #D5D8DC;")
        sb_lay = QHBoxLayout(s_bar)
        sb_lay.setContentsMargins(12, 8, 12, 8)
        self.lbl_sessions_count = QLabel("0 sessions")
        self.lbl_sessions_count.setStyleSheet("color: #555; font-size: 12px;")
        sb_lay.addWidget(self.lbl_sessions_count)
        sb_lay.addStretch()
        btn_s_refresh = QPushButton("Refresh")
        btn_s_refresh.setFixedWidth(80)
        btn_s_refresh.clicked.connect(self.refresh_sessions)
        sb_lay.addWidget(btn_s_refresh)
        btn_resume = QPushButton("Resume Session")
        btn_resume.setFixedWidth(130)
        btn_resume.clicked.connect(self._resume_selected_session)
        sb_lay.addWidget(btn_resume)
        btn_s_delete = QPushButton("Delete")
        btn_s_delete.setFixedWidth(70)
        btn_s_delete.clicked.connect(self._delete_selected_session)
        sb_lay.addWidget(btn_s_delete)
        s_lay.addWidget(s_bar)

        _S_COLS = ["ID", "Date", "Machine", "Physicist", "Beams", "Last Saved"]
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(len(_S_COLS))
        self.sessions_table.setHorizontalHeaderLabels(_S_COLS)
        self.sessions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sessions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setSortingEnabled(True)
        self.sessions_table.horizontalHeader().setStretchLastSection(True)
        self.sessions_table.verticalHeader().setVisible(False)
        self.sessions_table.doubleClicked.connect(self._resume_selected_session)
        self.sessions_table.setColumnWidth(0, 45)
        self.sessions_table.setColumnWidth(1, 100)
        self.sessions_table.setColumnWidth(2, 220)
        self.sessions_table.setColumnWidth(3, 140)
        self.sessions_table.setColumnWidth(4, 90)
        s_lay.addWidget(self.sessions_table)
        self.inner_tabs.addTab(sessions_widget, "Saved Sessions")

        # ── Tab 2: Individual Calibration Records ──────────────────────
        records_widget = QWidget()
        r_lay = QVBoxLayout(records_widget)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(0)

        filter_bar = QWidget()
        filter_bar.setStyleSheet("background-color: #F0F3F4; border-bottom: 1px solid #D5D8DC;")
        f_lay = QHBoxLayout(filter_bar)
        f_lay.setContentsMargins(12, 8, 12, 8)
        f_lay.addWidget(QLabel("Show:"))
        self.cmb_modality = QComboBox()
        self.cmb_modality.addItems(["All", "Photon", "Electron"])
        self.cmb_modality.currentIndexChanged.connect(self.refresh_records)
        f_lay.addWidget(self.cmb_modality)
        f_lay.addStretch()
        self.lbl_count = QLabel("0 records")
        self.lbl_count.setStyleSheet("color: #555; font-size: 12px;")
        f_lay.addWidget(self.lbl_count)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedWidth(80)
        btn_refresh.clicked.connect(self.refresh_records)
        f_lay.addWidget(btn_refresh)
        btn_export = QPushButton("Export PDF")
        btn_export.setFixedWidth(90)
        btn_export.clicked.connect(self._export_selected_pdf)
        f_lay.addWidget(btn_export)
        btn_delete = QPushButton("Delete Selected")
        btn_delete.setFixedWidth(120)
        btn_delete.clicked.connect(self._delete_selected)
        f_lay.addWidget(btn_delete)
        r_lay.addWidget(filter_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._view_details)
        self.table.setColumnWidth(_COL_IDX["ID"], 45)
        self.table.setColumnWidth(_COL_IDX["Date/Time"], 140)
        self.table.setColumnWidth(_COL_IDX["Modality"], 70)
        self.table.setColumnWidth(_COL_IDX["Energy"], 65)
        self.table.setColumnWidth(_COL_IDX["Chamber"], 130)
        self.table.setColumnWidth(_COL_IDX["k_Q"], 70)
        self.table.setColumnWidth(_COL_IDX["P_TP"], 70)
        self.table.setColumnWidth(_COL_IDX["P_pol"], 70)
        self.table.setColumnWidth(_COL_IDX["P_ion"], 70)
        self.table.setColumnWidth(_COL_IDX["Dose (cGy/MU)"], 100)
        self.table.setColumnWidth(_COL_IDX["Physicist"], 110)
        r_lay.addWidget(self.table)
        self.inner_tabs.addTab(records_widget, "Beam Records")

        self.refresh()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        self.refresh_sessions()
        self.refresh_records()

    def refresh_sessions(self):
        """Reload WorksheetSession rows."""
        from ...models import db as db_mod
        if not db_mod.is_ready():
            self.sessions_table.setRowCount(0)
            self.lbl_sessions_count.setText("DB not available")
            return
        sessions = db_mod.fetch_worksheet_sessions()
        self._populate_sessions_table(sessions)

    def _populate_sessions_table(self, sessions):
        self.sessions_table.setSortingEnabled(False)
        self.sessions_table.setRowCount(0)
        for ws in sessions:
            row = self.sessions_table.rowCount()
            self.sessions_table.insertRow(row)
            status = f"{ws.beams_calculated}/{ws.beams_total} calculated"
            date_str = ws.session_date.strftime("%Y-%m-%d") if hasattr(ws.session_date, 'strftime') else str(ws.session_date)[:10]
            updated_str = ws.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(ws.updated_at, 'strftime') else str(ws.updated_at)[:16]
            values = [
                str(ws.id),
                date_str,
                f"{ws.linac_name}  ({ws.linac_model})",
                ws.physicist or "—",
                status,
                updated_str,
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(Qt.UserRole, ws.id)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sessions_table.setItem(row, col, item)
            # Highlight rows with all beams calculated
            if ws.beams_total > 0 and ws.beams_calculated == ws.beams_total:
                for col in range(self.sessions_table.columnCount()):
                    it = self.sessions_table.item(row, col)
                    if it:
                        it.setBackground(QColor("#D5F5E3"))
        self.sessions_table.setSortingEnabled(True)
        self.lbl_sessions_count.setText(f"{len(sessions)} sessions")

    def refresh_records(self):
        """Reload CalibrationRecord rows."""
        from ...models import db as db_mod
        if not db_mod.is_ready():
            self.table.setRowCount(0)
            self.lbl_count.setText("DB not available")
            return
        modality_filter = self.cmb_modality.currentText().lower()
        if modality_filter == "all":
            modality_filter = None
        records = db_mod.fetch_all_records(modality=modality_filter)
        self._populate_table(records)

    def _populate_table(self, records):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for rec in records:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Energy label
            unit = "MV" if rec.modality == "photon" else "MeV"
            fff_tag = " FFF" if rec.is_fff else ""
            energy_str = f"{rec.energy_nominal:.0f}{unit}{fff_tag}"

            warnings = json.loads(rec.warnings_json or "[]")
            warn_str = f"{len(warnings)} ⚠" if warnings else "—"

            values = [
                (str(rec.id), Qt.AlignRight | Qt.AlignVCenter),
                (rec.recorded_at.strftime("%Y-%m-%d %H:%M"), Qt.AlignLeft | Qt.AlignVCenter),
                (rec.modality.title(), Qt.AlignCenter | Qt.AlignVCenter),
                (energy_str, Qt.AlignCenter | Qt.AlignVCenter),
                (rec.chamber_model.title(), Qt.AlignLeft | Qt.AlignVCenter),
                (f"{rec.k_q:.4f}", Qt.AlignRight | Qt.AlignVCenter),
                (f"{rec.p_tp:.5f}", Qt.AlignRight | Qt.AlignVCenter),
                (f"{rec.p_pol:.4f}", Qt.AlignRight | Qt.AlignVCenter),
                (f"{rec.p_ion:.4f}", Qt.AlignRight | Qt.AlignVCenter),
                (f"{rec.dose_ref_cgy_per_mu:.4f}", Qt.AlignRight | Qt.AlignVCenter),
                (rec.physicist or "—", Qt.AlignLeft | Qt.AlignVCenter),
                (warn_str, Qt.AlignCenter | Qt.AlignVCenter),
            ]

            for col, (text, align) in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if col == _COL_IDX["ID"]:
                    item.setData(Qt.UserRole, rec.id)
                self.table.setItem(row, col, item)

            # Colour-code dose: green near 1.00 cGy/MU, amber warning if >1.02 or <0.98
            dose = rec.dose_ref_cgy_per_mu
            dose_item = self.table.item(row, _COL_IDX["Dose (cGy/MU)"])
            if 0.98 <= dose <= 1.02:
                dose_item.setBackground(QColor("#D5F5E3"))
            elif 0.95 <= dose <= 1.05:
                dose_item.setBackground(QColor("#FDEBD0"))
            else:
                dose_item.setBackground(QColor("#FADBD8"))

            # Warnings column
            if warnings:
                self.table.item(row, _COL_IDX["Warnings"]).setBackground(QColor("#FEF9E7"))

        self.table.setSortingEnabled(True)
        self.lbl_count.setText(f"{self.table.rowCount()} records")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_session_id(self) -> Optional[int]:
        row = self.sessions_table.currentRow()
        if row < 0:
            return None
        item = self.sessions_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _resume_selected_session(self):
        ws_id = self._selected_session_id()
        if ws_id is None:
            QMessageBox.information(self, "No Selection", "Select a session row to resume.")
            return
        from ...models import db as db_mod
        ws = db_mod.load_worksheet_session(ws_id)
        if ws is None:
            QMessageBox.warning(self, "Not Found", f"Session #{ws_id} not found.")
            return
        # Delegate to main window
        from PySide6.QtWidgets import QApplication
        mw = QApplication.instance().activeWindow()
        if hasattr(mw, '_resume_worksheet_session'):
            mw._resume_worksheet_session(ws)
        else:
            QMessageBox.warning(self, "Cannot Resume", "Main window does not support session resume.")

    def _delete_selected_session(self):
        ws_id = self._selected_session_id()
        if ws_id is None:
            QMessageBox.information(self, "No Selection", "Select a session to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete saved session #{ws_id}?\n"
            "This removes the worksheet state but not individual beam records.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from ...models import db as db_mod
            db_mod.delete_worksheet_session(ws_id)
            self.refresh_sessions()

    def _selected_record_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, _COL_IDX["ID"])
        return item.data(Qt.UserRole) if item else None

    def _export_selected_pdf(self):
        rec_id = self._selected_record_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row to export.")
            return

        from ...models.db import get_session
        from ...models.entities import CalibrationRecord
        session = get_session()
        try:
            rec = session.get(CalibrationRecord, rec_id)
            if rec is None:
                return
            _export_record_pdf(rec, self)
        finally:
            session.close()

    def _delete_selected(self):
        rec_id = self._selected_record_id()
        if rec_id is None:
            QMessageBox.information(self, "No Selection", "Select a row to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete calibration record #{rec_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from ...models import db as db_mod
            db_mod.delete_record(rec_id)
            self.refresh()

    def _view_details(self):
        rec_id = self._selected_record_id()
        if rec_id is None:
            return

        from ...models.db import get_session
        from ...models.entities import CalibrationRecord
        session = get_session()
        try:
            rec = session.get(CalibrationRecord, rec_id)
            if rec:
                dlg = _RecordDetailDialog(rec, self)
                dlg.exec()
        finally:
            session.close()

    def showEvent(self, event):
        """Auto-refresh when this page becomes visible."""
        super().showEvent(event)
        self.refresh()


# ---------------------------------------------------------------------------
# Detail dialog
# ---------------------------------------------------------------------------

class _RecordDetailDialog(QDialog):
    """Shows full intermediate values for a saved calibration record."""

    def __init__(self, rec, parent=None):
        super().__init__(parent)
        self._rec = rec
        self.setWindowTitle(f"Calibration Record #{rec.id}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(560)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setSpacing(8)
        form.setContentsMargins(16, 16, 16, 16)

        def row(label, value):
            lbl = QLabel(str(value))
            lbl.setStyleSheet("font-family: monospace;")
            form.addRow(f"<b>{label}</b>", lbl)

        unit = "MV" if rec.modality == "photon" else "MeV"
        fff = " FFF" if rec.is_fff else ""
        row("Record ID", rec.id)
        row("Recorded at", rec.recorded_at.strftime("%Y-%m-%d %H:%M:%S"))
        row("Modality", rec.modality.title())
        row("Energy", f"{rec.energy_nominal:.0f} {unit}{fff}")
        row("Chamber", rec.chamber_model.title())
        if rec.chamber_type:
            row("Chamber type", rec.chamber_type)
        row("N_D,w (Gy/C)", f"{rec.n_dw_gy_per_c:.5g}")
        row("Physicist", rec.physicist or "—")
        form.addRow(QLabel(""))  # spacer

        row("Temperature", f"{rec.temperature_c:.1f} °C")
        row("Pressure", f"{rec.pressure_kpa:.2f} kPa")
        row("P_TP", f"{rec.p_tp:.5f}")
        row("P_pol", f"{rec.p_pol:.4f}")
        row("P_ion", f"{rec.p_ion:.4f}")
        row("P_elec", f"{rec.p_elec:.4f}")
        if rec.p_leak is not None and abs(rec.p_leak - 1.0) > 1e-6:
            row("P_leak", f"{rec.p_leak:.5f}")
        if rec.p_rp and rec.p_rp != 1.0:
            row("P_rp (FFF)", f"{rec.p_rp:.4f}")
        form.addRow(QLabel(""))

        if rec.modality == "photon":
            row("%dd(10)_x", f"{rec.pdd10x:.2f}%" if rec.pdd10x else "—")
            if rec.pdd10x_method:
                row("PDD method", rec.pdd10x_method)
        else:
            row("R_50", f"{rec.r50_cm:.3f} cm" if rec.r50_cm else "—")
            row("d_ref", f"{rec.d_ref_cm:.3f} cm" if rec.d_ref_cm else "—")
            row("k_Qecal", f"{rec.k_qecal:.4f}" if rec.k_qecal else "—")
            row("k'_Q", f"{rec.k_q_prime:.4f}" if rec.k_q_prime else "—")

        row("k_Q", f"{rec.k_q:.5f}")
        row("M_corrected (C)", f"{rec.m_corrected:.6g}")
        row("Monitor units", f"{rec.monitor_units:.0f} MU")
        form.addRow(QLabel(""))

        row("★ Dose at ref depth", f"{rec.dose_ref_cgy_per_mu:.4f} cGy/MU")
        if rec.dose_dmax_cgy_per_mu is not None:
            row("★ Dose at d_max", f"{rec.dose_dmax_cgy_per_mu:.4f} cGy/MU")

        warnings = json.loads(rec.warnings_json or "[]")
        if warnings:
            form.addRow(QLabel(""))
            w_lbl = QLabel("<b>Warnings:</b>")
            form.addRow(w_lbl)
            for w in warnings:
                wrow = QLabel(f"⚠ {w}")
                wrow.setWordWrap(True)
                wrow.setStyleSheet("color: #7D6608;")
                form.addRow(wrow)

        if rec.notes:
            form.addRow(QLabel(""))
            row("Notes", rec.notes)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_bar = QHBoxLayout()
        btn_export = QPushButton("Export PDF")
        btn_export.clicked.connect(self._export_pdf)
        btn_bar.addWidget(btn_export)
        btn_bar.addStretch()
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btn_bar.addWidget(btns)
        layout.addLayout(btn_bar)

    def _export_pdf(self):
        _export_record_pdf(self._rec, self)
