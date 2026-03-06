"""
styles.py — Qt stylesheet for Veritas TG-51.

Design language:
  - Clinical / professional appearance
  - Clear visual hierarchy between input fields and computed results
  - Computed/read-only fields have a distinct background (light blue)
  - Warning indicators in amber
  - Error indicators in red
"""

MAIN_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #F5F6FA;
}

/* ── Sidebar navigation ── */
QListWidget#sidebar {
    background-color: #1B2A4A;
    color: #C8D6E5;
    border: none;
    font-size: 13px;
    outline: none;
}
QListWidget#sidebar::item {
    padding: 12px 18px;
    border-left: 3px solid transparent;
}
QListWidget#sidebar::item:selected {
    background-color: #243B5A;
    color: #FFFFFF;
    border-left: 3px solid #4DA6FF;
}
QListWidget#sidebar::item:hover:!selected {
    background-color: #20304F;
}

/* ── Section headings ── */
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: bold;
    color: #1B2A4A;
    padding: 4px 0px;
    border-bottom: 2px solid #1B2A4A;
}
QLabel#subTitle {
    font-size: 12px;
    font-weight: bold;
    color: #3A5078;
    padding-top: 8px;
}

/* ── Input fields ── */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #BDC3C7;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 24px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4DA6FF;
    background-color: #F0F8FF;
}
QLineEdit[readOnly="true"] {
    background-color: #E8F4FD;
    color: #1A5276;
    border: 1px solid #AED6F1;
    font-weight: bold;
}

/* ── Result display (computed, read-only) ── */
QLineEdit#result {
    background-color: #D6EAF8;
    color: #154360;
    border: 1.5px solid #2E86C1;
    font-size: 13px;
    font-weight: bold;
}
QLineEdit#resultFinal {
    background-color: #D5F5E3;
    color: #1D6A39;
    border: 1.5px solid #27AE60;
    font-size: 14px;
    font-weight: bold;
}
QLineEdit#resultWarning {
    background-color: #FEF9E7;
    color: #7D6608;
    border: 1.5px solid #F4D03F;
    font-size: 13px;
    font-weight: bold;
}

/* ── Labels ── */
QLabel {
    font-size: 12px;
    color: #2C3E50;
}
QLabel#stepNumber {
    font-size: 13px;
    font-weight: bold;
    color: #FFFFFF;
    background-color: #1B2A4A;
    border-radius: 10px;
    padding: 2px 8px;
    min-width: 20px;
    max-width: 26px;
}

/* ── GroupBox (worksheet sections) ── */
QGroupBox {
    font-size: 12px;
    font-weight: bold;
    color: #1B2A4A;
    border: 1px solid #BDC3C7;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 12px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: #FFFFFF;
}

/* ── Buttons ── */
QPushButton {
    background-color: #2E86C1;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #2874A6;
}
QPushButton:pressed {
    background-color: #1A5276;
}
QPushButton#btnCalculate {
    background-color: #1D8348;
    font-size: 13px;
    min-height: 34px;
    padding: 8px 24px;
}
QPushButton#btnCalculate:hover {
    background-color: #196F3D;
}
QPushButton#btnSecondary {
    background-color: #FFFFFF;
    color: #2E86C1;
    border: 1px solid #2E86C1;
}
QPushButton#btnSecondary:hover {
    background-color: #EBF5FB;
}
QPushButton#btnDanger {
    background-color: #C0392B;
}
QPushButton#btnDanger:hover {
    background-color: #A93226;
}

/* ── Warning label ── */
QLabel#warningLabel {
    color: #7D6608;
    background-color: #FEF9E7;
    border: 1px solid #F4D03F;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}
QLabel#errorLabel {
    color: #7B241C;
    background-color: #FDEDEC;
    border: 1px solid #E74C3C;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}

/* ── Tab widget ── */
QTabWidget::pane {
    border: 1px solid #BDC3C7;
    background-color: #FFFFFF;
    border-radius: 0px 4px 4px 4px;
}
QTabBar::tab {
    background-color: #ECF0F1;
    color: #5D6D7E;
    padding: 8px 18px;
    border: 1px solid #BDC3C7;
    border-bottom: none;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1B2A4A;
    font-weight: bold;
    border-top: 2px solid #2E86C1;
}
QTabBar::tab:hover:!selected {
    background-color: #D5D8DC;
}

/* ── Table / session history ── */
QTableWidget {
    background-color: #FFFFFF;
    gridline-color: #E5E8E8;
    font-size: 12px;
    border: 1px solid #BDC3C7;
}
QTableWidget::item:selected {
    background-color: #D6EAF8;
    color: #154360;
}
QHeaderView::section {
    background-color: #1B2A4A;
    color: #FFFFFF;
    padding: 6px 8px;
    font-size: 11px;
    font-weight: bold;
    border: none;
}

/* ── Scroll area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    width: 8px;
    background: #F0F0F0;
}
QScrollBar::handle:vertical {
    background: #BDC3C7;
    border-radius: 4px;
    min-height: 20px;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #1B2A4A;
    color: #C8D6E5;
    font-size: 11px;
}
"""
