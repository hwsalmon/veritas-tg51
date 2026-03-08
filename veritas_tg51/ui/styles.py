"""
styles.py — Qt stylesheet for Veritas TG-51.

Design language:
  - Clinical / professional appearance
  - Clear visual hierarchy between input fields and computed results
  - Computed/read-only fields have a distinct background (light blue)
  - Warning indicators in amber
  - Error indicators in red
  - Supports light mode (default) and dark mode
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
    max-height: 30px;
    color: #2C3E50;
}
/* Ensure combobox popup is wide enough to show full item text */
QComboBox QAbstractItemView {
    min-width: 320px;
    background-color: #FFFFFF;
    border: 1px solid #BDC3C7;
    selection-background-color: #D6EAF8;
    selection-color: #154360;
    color: #2C3E50;
    padding: 2px;
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
    color: #1B2A4A;
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
    color: #2C3E50;
}
QTableWidget::item {
    color: #2C3E50;
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

/* ── Menu bar ── */
QMenuBar {
    background-color: #F5F6FA;
    color: #2C3E50;
}
QMenuBar::item:selected {
    background-color: #D6EAF8;
}
QMenu {
    background-color: #FFFFFF;
    color: #2C3E50;
    border: 1px solid #BDC3C7;
}
QMenu::item:selected {
    background-color: #D6EAF8;
    color: #154360;
}

/* ── Toolbar / filter bars (scoped via objectName) ── */
QWidget#sessionsBar {
    background-color: #F0F3F4;
    border-bottom: 1px solid #D5D8DC;
}
QWidget#filterBar {
    background-color: #F0F3F4;
    border-bottom: 1px solid #D5D8DC;
}

/* ── Themed inline labels (must use objectName) ── */
QLabel#noteLabel {
    color: #7D6608;
    font-size: 11px;
    font-style: italic;
}
QLabel#infoLabel {
    color: #1A5276;
    font-size: 11px;
    margin-left: 8px;
}
QLabel#dimLabel {
    color: #7A8899;
    font-size: 11px;
    font-style: italic;
}
QLabel#infoNotice {
    background-color: #EBF5FB;
    color: #1A5276;
    font-size: 11px;
    padding: 8px 16px;
    border-bottom: 1px solid #AED6F1;
}
QLabel#posNote {
    color: #154360;
    background-color: #D6EAF8;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}
QLabel#saveStatus {
    color: #888;
    font-size: 10px;
    padding: 2px 10px;
}

/* ── Theme toggle button in header ── */
QPushButton#btnTheme {
    background-color: transparent;
    color: #C8D6E5;
    border: 1px solid #3D4A5C;
    border-radius: 14px;
    padding: 2px 8px;
    font-size: 16px;
    min-height: 28px;
    min-width: 36px;
    font-weight: normal;
}
QPushButton#btnTheme:hover {
    background-color: #1E3050;
    border-color: #4DA6FF;
}
"""

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #1A1F2E;
    color: #D0D8E8;
}

/* ── Sidebar navigation ── */
QListWidget#sidebar {
    background-color: #0F1420;
    color: #9BAEC8;
    border: none;
    font-size: 13px;
    outline: none;
}
QListWidget#sidebar::item {
    padding: 12px 18px;
    border-left: 3px solid transparent;
}
QListWidget#sidebar::item:selected {
    background-color: #1E2D4A;
    color: #FFFFFF;
    border-left: 3px solid #4DA6FF;
}
QListWidget#sidebar::item:hover:!selected {
    background-color: #181E2E;
}

/* ── Section headings ── */
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: bold;
    color: #7CC8FF;
    padding: 4px 0px;
    border-bottom: 2px solid #4DA6FF;
}
QLabel#subTitle {
    font-size: 12px;
    font-weight: bold;
    color: #7399BB;
    padding-top: 8px;
}

/* ── Input fields ── */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background-color: #252B3B;
    border: 1px solid #3D4A5C;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 30px;
    color: #D0D8E8;
}
/* Ensure combobox popup is wide enough to show full item text */
QComboBox QAbstractItemView {
    min-width: 320px;
    background-color: #252B3B;
    border: 1px solid #3D4A5C;
    selection-background-color: #1E3A5A;
    selection-color: #7CC8FF;
    color: #D0D8E8;
    padding: 2px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4DA6FF;
    background-color: #1E2D42;
}
QLineEdit[readOnly="true"] {
    background-color: #1A2E42;
    color: #7CC8FF;
    border: 1px solid #2E5070;
    font-weight: bold;
}

/* ── Result display (computed, read-only) ── */
QLineEdit#result {
    background-color: #1A2E42;
    color: #7CC8FF;
    border: 1.5px solid #2E86C1;
    font-size: 13px;
    font-weight: bold;
}
QLineEdit#resultFinal {
    background-color: #1A3228;
    color: #5AE89A;
    border: 1.5px solid #27AE60;
    font-size: 14px;
    font-weight: bold;
}
QLineEdit#resultWarning {
    background-color: #2E2800;
    color: #FFD700;
    border: 1.5px solid #B8A000;
    font-size: 13px;
    font-weight: bold;
}

/* ── Labels ── */
QLabel {
    font-size: 12px;
    color: #C0C8D8;
}
QLabel#stepNumber {
    font-size: 13px;
    font-weight: bold;
    color: #FFFFFF;
    background-color: #1E3050;
    border-radius: 10px;
    padding: 2px 8px;
    min-width: 20px;
    max-width: 26px;
}

/* ── GroupBox (worksheet sections) ── */
QGroupBox {
    font-size: 12px;
    font-weight: bold;
    color: #7CC8FF;
    border: 1px solid #3D4A5C;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 12px;
    background-color: #1E2535;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: #1E2535;
    color: #7CC8FF;
}

/* ── Buttons ── */
QPushButton {
    background-color: #1E5E8A;
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
    background-color: #0E3A5C;
}
QPushButton#btnCalculate {
    background-color: #1A6B3A;
    font-size: 13px;
    min-height: 34px;
    padding: 8px 24px;
}
QPushButton#btnCalculate:hover {
    background-color: #1E7F45;
}
QPushButton#btnSecondary {
    background-color: #1E2535;
    color: #4DA6FF;
    border: 1px solid #2E5070;
}
QPushButton#btnSecondary:hover {
    background-color: #252B3B;
}
QPushButton#btnDanger {
    background-color: #8B1A1A;
}
QPushButton#btnDanger:hover {
    background-color: #A93226;
}

/* ── Warning label ── */
QLabel#warningLabel {
    color: #FFD700;
    background-color: #2E2800;
    border: 1px solid #B8A000;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}
QLabel#errorLabel {
    color: #FF8080;
    background-color: #2E1010;
    border: 1px solid #8B1A1A;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}

/* ── Tab widget ── */
QTabWidget::pane {
    border: 1px solid #3D4A5C;
    background-color: #1E2535;
    border-radius: 0px 4px 4px 4px;
}
QTabBar::tab {
    background-color: #252B3B;
    color: #7899AA;
    padding: 8px 18px;
    border: 1px solid #3D4A5C;
    border-bottom: none;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #1E2535;
    color: #D0D8E8;
    font-weight: bold;
    border-top: 2px solid #4DA6FF;
}
QTabBar::tab:hover:!selected {
    background-color: #2A3145;
}

/* ── Table / session history ── */
QTableWidget {
    background-color: #1E2535;
    gridline-color: #2D3548;
    font-size: 12px;
    border: 1px solid #3D4A5C;
    color: #C0C8D8;
    alternate-background-color: #232A3A;
}
QTableWidget::item {
    color: #C0C8D8;
}
QTableWidget::item:selected {
    background-color: #1E3A5A;
    color: #7CC8FF;
}
QHeaderView::section {
    background-color: #0F1420;
    color: #9BAEC8;
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
    background: #1A1F2E;
}
QScrollBar::handle:vertical {
    background: #3D4A5C;
    border-radius: 4px;
    min-height: 20px;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #0F1420;
    color: #7899AA;
    font-size: 11px;
}

/* ── Menu bar ── */
QMenuBar {
    background-color: #1A1F2E;
    color: #C0C8D8;
}
QMenuBar::item:selected {
    background-color: #1E3A5A;
}
QMenu {
    background-color: #1E2535;
    color: #C0C8D8;
    border: 1px solid #3D4A5C;
}
QMenu::item:selected {
    background-color: #1E3A5A;
    color: #7CC8FF;
}

/* ── Toolbar / filter bars (scoped via objectName) ── */
QWidget#sessionsBar {
    background-color: #1A1F2E;
    border-bottom: 1px solid #2D3548;
}
QWidget#filterBar {
    background-color: #1A1F2E;
    border-bottom: 1px solid #2D3548;
}

/* ── Splitter handle ── */
QSplitter::handle {
    background-color: #2D3548;
}

/* ── SpinBox arrows ── */
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background-color: #3D4A5C;
    border: none;
}

/* ── Themed inline labels (must use objectName) ── */
QLabel#noteLabel {
    color: #D4A010;
    font-size: 11px;
    font-style: italic;
}
QLabel#infoLabel {
    color: #7CC8FF;
    font-size: 11px;
    margin-left: 8px;
}
QLabel#dimLabel {
    color: #7A8899;
    font-size: 11px;
    font-style: italic;
}
QLabel#infoNotice {
    background-color: #1A2E42;
    color: #7CC8FF;
    font-size: 11px;
    padding: 8px 16px;
    border-bottom: 1px solid #2E5070;
}
QLabel#posNote {
    color: #7CC8FF;
    background-color: #1A2E42;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}
QLabel#saveStatus {
    color: #6B7A8A;
    font-size: 10px;
    padding: 2px 10px;
}

/* ── Theme toggle button in header ── */
QPushButton#btnTheme {
    background-color: transparent;
    color: #C8D6E5;
    border: 1px solid #3D4A5C;
    border-radius: 14px;
    padding: 2px 8px;
    font-size: 16px;
    min-height: 28px;
    min-width: 36px;
    font-weight: normal;
}
QPushButton#btnTheme:hover {
    background-color: #252B3B;
    border-color: #4DA6FF;
}
"""
