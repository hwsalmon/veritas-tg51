"""
jaffe_dialog.py — Jaffé plot analysis dialog for ion recombination.

The Jaffé method fits multiple (V, M) readings to the linear model:

    1/M = α + β/V

so that M_sat = 1/α (fully saturated reading) and

    P_ion(V_H) = M_sat / M(V_H) = 1 + β / (α · V_H)

This gives a more robust P_ion than the two-voltage method, particularly for
FFF beams where ion recombination is larger (Report 374 §4.4.4).

References
----------
AAPM WGTG51 Report 374. Med. Phys. 2022;49(9):6739–6764. §4.4.4.
Jaffé G. Ann. Phys. 1913;42:303.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class JaffePlotDialog(QDialog):
    """
    Jaffé plot analysis dialog.

    Opens from the photon worksheet ion recombination section.
    The user enters ≥3 (V, M) data points, clicks Analyze, and can then
    push the resulting P_ion back into the worksheet.

    Parameters
    ----------
    v_h : float
        Operating voltage V_H (pre-populated from the worksheet).
    on_accept : Callable[[float], None]
        Called with the computed P_ion(V_H) when the user clicks
        "Use this P_ion".
    parent : QWidget, optional
    """

    def __init__(
        self,
        v_h: float = 300.0,
        on_accept: Optional[Callable[[float], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._v_h = v_h
        self._on_accept = on_accept
        self._p_ion_result: Optional[float] = None

        self.setWindowTitle("Jaffé Plot — Ion Recombination Analysis")
        self.setMinimumWidth(540)
        self.setMinimumHeight(580)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- Instructions ---
        info = QLabel(
            "<b>Jaffé plot method</b> (Report 374 §4.4.4)<br>"
            "Enter ≥3 (V, M) measurement pairs at the same geometry and MU "
            "but with different collector voltages. "
            "Readings must be raw (unscaled, same units). "
            "Include your operating voltage V<sub>H</sub> as one of the rows."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #2C3E50; font-size: 12px;")
        layout.addWidget(info)

        # --- V_H input ---
        vh_row = QHBoxLayout()
        vh_row.addWidget(QLabel("Operating voltage V<sub>H</sub>:"))
        self.spn_vh = QDoubleSpinBox()
        self.spn_vh.setRange(50, 2000)
        self.spn_vh.setDecimals(0)
        self.spn_vh.setValue(self._v_h)
        self.spn_vh.setSuffix(" V")
        self.spn_vh.setFixedWidth(100)
        vh_row.addWidget(self.spn_vh)
        vh_row.addStretch()
        layout.addLayout(vh_row)

        # --- Data table ---
        tbl_grp = QGroupBox("Measurement Pairs  ( V , M )")
        tbl_lay = QVBoxLayout(tbl_grp)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Voltage V (V)", "Reading M (same units as M_raw)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        tbl_lay.addWidget(self.table)

        # Table action buttons
        tbl_btns = QHBoxLayout()
        btn_add = QPushButton("Add Row")
        btn_add.setFixedWidth(80)
        btn_add.clicked.connect(self._add_row)
        btn_remove = QPushButton("Remove Row")
        btn_remove.setFixedWidth(100)
        btn_remove.clicked.connect(self._remove_row)
        tbl_btns.addWidget(btn_add)
        tbl_btns.addWidget(btn_remove)
        tbl_btns.addStretch()
        tbl_lay.addLayout(tbl_btns)

        layout.addWidget(tbl_grp)

        # Seed the table with 5 blank rows
        for _ in range(5):
            self._add_row()

        # --- Analyze button ---
        btn_analyze = QPushButton("Analyze")
        btn_analyze.setObjectName("btnCalculate")
        btn_analyze.clicked.connect(self._analyze)
        layout.addWidget(btn_analyze, alignment=Qt.AlignLeft)

        # --- Results ---
        self.results_grp = QGroupBox("Regression Results")
        results_form = QFormLayout(self.results_grp)
        results_form.setSpacing(8)

        def res_label(text="—"):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-family: monospace; font-size: 13px;")
            return lbl

        self.lbl_alpha = res_label()
        self.lbl_beta = res_label()
        self.lbl_r2 = res_label()
        self.lbl_msat = res_label()
        self.lbl_pion = res_label()
        self.lbl_pion.setStyleSheet(
            "font-family: monospace; font-size: 15px; font-weight: bold; color: #1A5276;"
        )

        results_form.addRow("α  (intercept = 1/M_sat):", self.lbl_alpha)
        results_form.addRow("β  (slope):", self.lbl_beta)
        results_form.addRow("R²:", self.lbl_r2)
        results_form.addRow("M_sat = 1/α:", self.lbl_msat)
        results_form.addRow("★  P_ion(V_H):", self.lbl_pion)

        layout.addWidget(self.results_grp)

        # --- Dialog buttons ---
        btn_bar = QHBoxLayout()
        self.btn_use = QPushButton("Use this P_ion")
        self.btn_use.setEnabled(False)
        self.btn_use.clicked.connect(self._use_pion)
        btn_bar.addWidget(self.btn_use)
        btn_bar.addStretch()

        close_btn = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn.rejected.connect(self.reject)
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

    # ------------------------------------------------------------------
    # Table helpers
    # ------------------------------------------------------------------

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(2):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, item)

    def _remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _parse_table(self) -> tuple[list[float], list[float]]:
        """Return lists of voltages and readings from non-empty rows."""
        voltages, readings = [], []
        for r in range(self.table.rowCount()):
            v_item = self.table.item(r, 0)
            m_item = self.table.item(r, 1)
            if not v_item or not m_item:
                continue
            v_text = v_item.text().strip()
            m_text = m_item.text().strip()
            if not v_text or not m_text:
                continue
            try:
                v = float(v_text)
                m = float(m_text)
            except ValueError:
                raise ValueError(
                    f"Row {r + 1}: could not parse values '{v_text}', '{m_text}'."
                )
            if v <= 0:
                raise ValueError(f"Row {r + 1}: voltage must be positive, got {v}.")
            if m == 0:
                raise ValueError(f"Row {r + 1}: reading M must not be zero.")
            voltages.append(v)
            readings.append(m)
        return voltages, readings

    def _analyze(self):
        try:
            voltages, readings = self._parse_table()
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
            return

        if len(voltages) < 3:
            QMessageBox.warning(
                self, "Insufficient Data",
                "At least 3 (V, M) pairs are required for a meaningful regression."
            )
            return

        try:
            p_ion, alpha, beta, r2, m_sat = _jaffe_regression(
                voltages, readings, self.spn_vh.value()
            )
        except Exception as e:
            QMessageBox.critical(self, "Regression Error", str(e))
            return

        self.lbl_alpha.setText(f"{alpha:.6g}")
        self.lbl_beta.setText(f"{beta:.6g}")
        self.lbl_r2.setText(f"{r2:.6f}")
        self.lbl_msat.setText(f"{m_sat:.6g}")
        self.lbl_pion.setText(f"{p_ion:.5f}")

        self._p_ion_result = p_ion
        self.btn_use.setEnabled(True)

        if p_ion > 1.050:
            QMessageBox.warning(
                self, "P_ion Warning",
                f"P_ion(V_H) = {p_ion:.4f} > 1.05. This is unusually large.\n\n"
                "Check that the operating voltage is sufficient and that "
                "the beam output is stable. TG-51 requires P_ion ≤ 1.05."
            )

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _use_pion(self):
        if self._p_ion_result is not None and self._on_accept is not None:
            self._on_accept(self._p_ion_result)
        self.accept()


# ---------------------------------------------------------------------------
# Pure physics — Jaffé linear regression
# ---------------------------------------------------------------------------

def _jaffe_regression(
    voltages: list[float],
    readings: list[float],
    v_h: float,
) -> tuple[float, float, float, float, float]:
    """
    Fit 1/M = α + β/V  via ordinary least-squares.

    Returns
    -------
    p_ion : float
        P_ion at V_H = 1 + β/(α·V_H)
    alpha : float
        Regression intercept (= 1/M_sat)
    beta : float
        Regression slope (coefficient of 1/V)
    r2 : float
        Coefficient of determination R²
    m_sat : float
        Saturated reading 1/α
    """
    x = np.array([1.0 / v for v in voltages], dtype=float)   # 1/V
    y = np.array([1.0 / m for m in readings], dtype=float)    # 1/M

    # OLS: y = alpha + beta * x
    coeffs = np.polyfit(x, y, 1)    # returns [slope, intercept]
    beta = float(coeffs[0])
    alpha = float(coeffs[1])

    if alpha <= 0:
        raise ValueError(
            f"Regression intercept α = {alpha:.4g} ≤ 0. "
            "Check your data — readings may not be monotone in voltage."
        )

    # R²
    y_pred = alpha + beta * x
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    m_sat = 1.0 / alpha
    p_ion = 1.0 + beta / (alpha * v_h)
    return p_ion, alpha, beta, r2, m_sat
