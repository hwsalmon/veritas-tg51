"""
form_widgets.py — Reusable form row widgets for TG-51 worksheets.

Each worksheet row shows:  [Step#]  Label  [Input/Result field]  [Unit]  [Equation ref]
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QWidget,
)


class ScientificDoubleEdit(QLineEdit):
    """
    A QLineEdit that accepts and displays floating-point values in
    3-significant-figure scientific notation (e.g. "4.818E+07").

    Users can type any float or scientific notation string; on focus-out the
    value is reformatted to  X.XXXE+YY  style.
    """

    value_changed = Signal(float)

    def __init__(self, value: float = 0.0, parent=None):
        super().__init__(parent)
        self._value: float = value
        self.setFixedWidth(120)
        self.set_value(value)
        self.editingFinished.connect(self._reformat)

    def set_value(self, value: float):
        self._value = value
        self.setText(f"{value:.3E}")

    def get_value(self) -> Optional[float]:
        try:
            v = float(self.text().replace(",", "").strip())
            return v
        except ValueError:
            return None

    def _reformat(self):
        v = self.get_value()
        if v is not None:
            self._value = v
            self.setText(f"{v:.3E}")
            self.value_changed.emit(v)
        else:
            self.setText(f"{self._value:.3E}")


class FieldRow(QWidget):
    """
    A single labeled row in a worksheet form.

    Layout:  [step_label]  [field_label]  ... spacer ...  [input]  [unit]  [ref]
    """

    value_changed = Signal(float)

    def __init__(
        self,
        label: str,
        unit: str = "",
        ref: str = "",
        step: str = "",
        read_only: bool = False,
        decimals: int = 4,
        value_min: float = -1e9,
        value_max: float = 1e9,
        placeholder: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._decimals = decimals
        self._read_only = read_only

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # Step number badge
        if step:
            lbl_step = QLabel(step)
            lbl_step.setObjectName("stepNumber")
            lbl_step.setFixedWidth(28)
            lbl_step.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_step)
        else:
            spacer_step = QWidget()
            spacer_step.setFixedWidth(28)
            layout.addWidget(spacer_step)

        # Field label
        lbl_field = QLabel(label)
        lbl_field.setMinimumWidth(220)
        lbl_field.setWordWrap(True)
        layout.addWidget(lbl_field)

        layout.addStretch()

        # Input / result field
        self.field = QLineEdit()
        self.field.setFixedWidth(120)
        self.field.setPlaceholderText(placeholder)
        if read_only:
            self.field.setReadOnly(True)
            self.field.setObjectName("result")
        else:
            validator = QDoubleValidator(value_min, value_max, decimals)
            validator.setNotation(QDoubleValidator.StandardNotation)
            self.field.setValidator(validator)
            self.field.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.field)

        # Unit label
        lbl_unit = QLabel(unit)
        lbl_unit.setFixedWidth(70)
        lbl_unit.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(lbl_unit)

        # Equation reference
        lbl_ref = QLabel(ref)
        lbl_ref.setFixedWidth(90)
        lbl_ref.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        layout.addWidget(lbl_ref)

    def _on_text_changed(self, text: str):
        try:
            val = float(text)
            self.value_changed.emit(val)
        except ValueError:
            pass

    def set_value(self, value: float, highlight_final: bool = False):
        """Set the displayed value."""
        fmt = f"{{:.{self._decimals}f}}"
        self.field.setText(fmt.format(value))
        if self._read_only and highlight_final:
            self.field.setObjectName("resultFinal")
            self.field.style().unpolish(self.field)
            self.field.style().polish(self.field)

    def get_value(self) -> Optional[float]:
        """Get the current value or None if empty/invalid."""
        try:
            return float(self.field.text())
        except ValueError:
            return None

    def set_warning_style(self):
        self.field.setObjectName("resultWarning")
        self.field.style().unpolish(self.field)
        self.field.style().polish(self.field)

    def clear(self):
        self.field.clear()


class DualFieldRow(QWidget):
    """Two input fields side by side (e.g. M+_raw and M-_raw on one line)."""

    def __init__(
        self,
        label: str,
        label_a: str,
        label_b: str,
        unit: str = "",
        ref: str = "",
        step: str = "",
        decimals: int = 4,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        if step:
            lbl_step = QLabel(step)
            lbl_step.setObjectName("stepNumber")
            lbl_step.setFixedWidth(28)
            lbl_step.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_step)
        else:
            spacer = QWidget()
            spacer.setFixedWidth(28)
            layout.addWidget(spacer)

        lbl_field = QLabel(label)
        lbl_field.setMinimumWidth(180)
        layout.addWidget(lbl_field)

        layout.addStretch()

        validator = QDoubleValidator()
        validator.setDecimals(decimals)

        lbl_a = QLabel(label_a)
        lbl_a.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(lbl_a)

        self.field_a = QLineEdit()
        self.field_a.setFixedWidth(90)
        self.field_a.setValidator(validator)
        layout.addWidget(self.field_a)

        lbl_b = QLabel(label_b)
        lbl_b.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(lbl_b)

        self.field_b = QLineEdit()
        self.field_b.setFixedWidth(90)
        self.field_b.setValidator(validator)
        layout.addWidget(self.field_b)

        lbl_unit = QLabel(unit)
        lbl_unit.setFixedWidth(60)
        lbl_unit.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(lbl_unit)

        lbl_ref = QLabel(ref)
        lbl_ref.setFixedWidth(90)
        lbl_ref.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        layout.addWidget(lbl_ref)

    def get_values(self) -> tuple[Optional[float], Optional[float]]:
        try:
            a = float(self.field_a.text())
        except ValueError:
            a = None
        try:
            b = float(self.field_b.text())
        except ValueError:
            b = None
        return a, b
