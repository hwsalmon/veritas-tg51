"""
main_window.py — Veritas TG-51 main application window.

Layout:
  ┌────────────────────────────────────────────────────────┐
  │  Veritas TG-51                              [nav icons] │  ← top bar
  ├──────────┬─────────────────────────────────────────────┤
  │          │                                             │
  │ Sidebar  │   Content area (stacked pages)             │
  │          │                                             │
  └──────────┴─────────────────────────────────────────────┘
  │  Status bar                                            │
  └────────────────────────────────────────────────────────┘

Pages:
  0 — Photon Worksheet (Worksheet A)
  1 — Electron Worksheet (Worksheet B, 2024 Addendum)
  2 — Session History
  3 — Equipment / Machine Management
"""

from __future__ import annotations

import json
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from .pages.history_page import HistoryPage
from .pages.equipment_page import EquipmentPage
from .styles import MAIN_STYLESHEET, DARK_STYLESHEET

_SETTINGS_PATH = pathlib.Path.home() / ".config" / "veritas_tg51" / "settings.json"


NAV_ITEMS = [
    ("Current Session",  "Active calibration session"),
    ("Session History",  "Previous calibration records"),
    ("Configuration",    "Chambers, electrometers, machines"),
]

_SESSION_PAGE_IDX = 0


def _make_dark_palette() -> QPalette:
    """Build a QPalette that makes Fusion-style native rendering dark.

    Qt's Fusion style uses QPalette colours for painting widget frames,
    menu bars, scroll bars, and other chrome that stylesheets alone cannot
    fully override.  Setting this palette alongside DARK_STYLESHEET ensures
    consistent dark rendering across all widget types.
    """
    R = QPalette.ColorRole
    p = QPalette()
    roles = {
        R.Window:          "#1A1F2E",
        R.WindowText:      "#C0C8D8",
        R.Base:            "#1E2535",
        R.AlternateBase:   "#232A3A",
        R.ToolTipBase:     "#1E2535",
        R.ToolTipText:     "#C0C8D8",
        R.Text:            "#C0C8D8",
        R.Button:          "#1E2535",
        R.ButtonText:      "#FFFFFF",
        R.BrightText:      "#FFFFFF",
        R.Highlight:       "#1E5E8A",
        R.HighlightedText: "#FFFFFF",
        R.Light:           "#2A3040",
        R.Midlight:        "#242B3A",
        R.Dark:            "#141824",
        R.Mid:             "#1A1F2E",
        R.Shadow:          "#0A0F1C",
        R.Link:            "#4DA6FF",
        R.LinkVisited:     "#7CC8FF",
    }
    for role, hex_color in roles.items():
        p.setColor(role, QColor(hex_color))
    return p


def _make_light_palette() -> QPalette:
    """Return the default Fusion light palette."""
    from PySide6.QtWidgets import QApplication, QStyleFactory
    style = QStyleFactory.create("Fusion")
    return style.standardPalette() if style else QApplication.style().standardPalette()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Veritas TG-51  —  Absolute Dosimetry Calibration")
        self.setMinimumSize(1100, 750)
        self._dark_mode = self._load_setting("dark_mode", False)
        self._build_ui()
        self._build_menu()
        self._apply_theme()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header bar ──
        header = self._build_header()
        root.addWidget(header)

        # ── Splitter: sidebar + content ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.stack = QStackedWidget()

        # Index 0: session placeholder (replaced by SessionPage after wizard)
        self.session_placeholder = self._make_session_placeholder()
        self.stack.addWidget(self.session_placeholder)   # idx 0

        self.history_page = HistoryPage()
        self.equipment_page = EquipmentPage()

        for page in [self.history_page, self.equipment_page]:
            self.stack.addWidget(page)      # idx 1-2

        sidebar_container = self._build_sidebar()
        splitter.addWidget(sidebar_container)
        splitter.addWidget(self.stack)
        splitter.setSizes([210, 900])
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

        # ── Status bar ──
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready  —  Veritas TG-51  |  Protocol: TG-51 (1999) + WGTG51 Reports 374 & 385")

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("appHeader")
        header.setFixedHeight(48)
        header.setStyleSheet("QWidget#appHeader { background-color: #0D1B2E; }")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        lbl_logo = QLabel("VERITAS  <span style='color:#4DA6FF; font-weight:normal;'>TG-51</span>")
        lbl_logo.setTextFormat(Qt.RichText)
        font = QFont("Helvetica", 16, QFont.Bold)
        lbl_logo.setFont(font)
        lbl_logo.setStyleSheet("color: white;")
        layout.addWidget(lbl_logo)

        layout.addStretch()

        lbl_proto = QLabel(
            "AAPM TG-51 (1999)  ·  WGTG51 Report 374 (2022)  ·  WGTG51 Report 385 (2024)"
        )
        lbl_proto.setStyleSheet("color: #5D7FA3; font-size: 11px;")
        layout.addWidget(lbl_proto)

        layout.addSpacing(12)

        self._btn_theme = QPushButton("☾")
        self._btn_theme.setObjectName("btnTheme")
        self._btn_theme.setToolTip("Toggle dark / light mode  (Ctrl+Shift+D)")
        self._btn_theme.setFixedSize(36, 30)
        self._btn_theme.clicked.connect(self._toggle_dark_mode_btn)
        layout.addWidget(self._btn_theme)

        # Store references for theme switching
        self._header_widget = header
        self._lbl_proto = lbl_proto

        return header

    def _build_sidebar(self) -> QWidget:
        container = QWidget()
        container.setFixedWidth(210)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setSpacing(2)

        for name, tooltip in NAV_ITEMS:
            item = QListWidgetItem(name)
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)

        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.sidebar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #cccccc;")
        layout.addWidget(line)

        # New Session button
        self.btn_new_session = QPushButton("New Session…")
        self.btn_new_session.setObjectName("btnSecondary")
        self.btn_new_session.setToolTip("Save current session and start a new calibration")
        self.btn_new_session.setFixedHeight(34)
        self.btn_new_session.clicked.connect(self._start_new_session)
        layout.addWidget(self.btn_new_session)

        # Print Full Report button
        self.btn_full_report = QPushButton("Print Full Report")
        self.btn_full_report.setObjectName("btnCalculate")
        self.btn_full_report.setToolTip("Generate a complete PDF report for all calculated beams")
        self.btn_full_report.setFixedHeight(36)
        self.btn_full_report.clicked.connect(self._print_full_report)
        layout.addWidget(self.btn_full_report)

        return container

    def _make_session_placeholder(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)

        lbl = QLabel(
            "<b style='font-size:18px;'>Start a New Calibration Session</b><br><br>"
            "Select your site, treatment machine, ion chamber,<br>"
            "electrometer and operator — the worksheet will be built<br>"
            "automatically with one tab per configured beam energy."
        )
        lbl.setTextFormat(Qt.RichText)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #2C3E50;")
        lay.addWidget(lbl)

        btn = QPushButton("  Start New Session…")
        btn.setObjectName("btnCalculate")
        btn.setFixedWidth(220)
        btn.clicked.connect(self._start_new_session)
        lay.addSpacing(20)
        lay.addWidget(btn, alignment=Qt.AlignCenter)

        note = QLabel(
            "Equipment must be configured in the <b>Equipment</b> page first."
        )
        note.setTextFormat(Qt.RichText)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: #888; font-size: 11px;")
        lay.addSpacing(12)
        lay.addWidget(note)
        return w

    def _on_nav_changed(self, idx: int):
        _, tooltip = NAV_ITEMS[idx]
        self.status.showMessage(tooltip)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        act_new = QAction("New Calibration Session", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._new_session)
        file_menu.addAction(act_new)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Tools
        tools_menu = mb.addMenu("&Tools")
        act_session = QAction("New Session…", self)
        act_session.triggered.connect(self._start_new_session)
        tools_menu.addAction(act_session)

        tools_menu.addSeparator()

        act_history = QAction("Session History", self)
        act_history.triggered.connect(lambda: self._navigate(1))
        tools_menu.addAction(act_history)

        act_equip = QAction("Equipment Manager", self)
        act_equip.triggered.connect(lambda: self._navigate(2))
        tools_menu.addAction(act_equip)

        # View
        view_menu = mb.addMenu("&View")
        self.act_dark_mode = QAction("Dark Mode", self)
        self.act_dark_mode.setCheckable(True)
        self.act_dark_mode.setChecked(self._dark_mode)
        self.act_dark_mode.setShortcut("Ctrl+Shift+D")
        self.act_dark_mode.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(self.act_dark_mode)

        # Help
        help_menu = mb.addMenu("&Help")
        act_about = QAction("About Veritas TG-51", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        act_refs = QAction("Protocol References", self)
        act_refs.triggered.connect(self._show_references)
        help_menu.addAction(act_refs)

    # ------------------------------------------------------------------
    # Theme / settings
    # ------------------------------------------------------------------

    def _load_setting(self, key: str, default):
        try:
            if _SETTINGS_PATH.exists():
                data = json.loads(_SETTINGS_PATH.read_text())
                return data.get(key, default)
        except Exception:
            pass
        return default

    def _save_setting(self, key: str, value):
        try:
            _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if _SETTINGS_PATH.exists():
                try:
                    data = json.loads(_SETTINGS_PATH.read_text())
                except Exception:
                    pass
            data[key] = value
            _SETTINGS_PATH.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _apply_theme(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if self._dark_mode:
            app.setStyleSheet(DARK_STYLESHEET)
            app.setPalette(_make_dark_palette())
            self._update_header_for_dark(True)
        else:
            app.setStyleSheet(MAIN_STYLESHEET)
            app.setPalette(_make_light_palette())
            self._update_header_for_dark(False)

    def _update_header_for_dark(self, dark: bool):
        """Update header widget colors to match the current theme."""
        if dark:
            self._header_widget.setStyleSheet("QWidget#appHeader { background-color: #0A0F1C; }")
            self._lbl_proto.setStyleSheet("color: #3A5070; font-size: 11px;")
            if hasattr(self, '_btn_theme'):
                self._btn_theme.setText("☼")
                self._btn_theme.setToolTip("Switch to light mode  (Ctrl+Shift+D)")
        else:
            self._header_widget.setStyleSheet("QWidget#appHeader { background-color: #0D1B2E; }")
            self._lbl_proto.setStyleSheet("color: #5D7FA3; font-size: 11px;")
            if hasattr(self, '_btn_theme'):
                self._btn_theme.setText("☾")
                self._btn_theme.setToolTip("Switch to dark mode  (Ctrl+Shift+D)")

    def _toggle_dark_mode(self, checked: bool):
        self._dark_mode = checked
        self._save_setting("dark_mode", checked)
        if hasattr(self, 'act_dark_mode'):
            self.act_dark_mode.setChecked(checked)
        self._apply_theme()

    def _toggle_dark_mode_btn(self):
        self._toggle_dark_mode(not self._dark_mode)

    def _print_full_report(self):
        """Delegate to the current session page's print_full_report method."""
        page = self.stack.widget(0)
        from .pages.session_page import SessionPage
        if isinstance(page, SessionPage):
            page.print_full_report()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "No Session",
                "Start a calibration session first, then calculate at least one beam."
            )

    def _navigate(self, idx: int):
        self.sidebar.setCurrentRow(idx)
        self.stack.setCurrentIndex(idx)

    def _start_new_session(self):
        """Open the session setup wizard and build a SessionPage."""
        from PySide6.QtWidgets import QMessageBox
        try:
            from .dialogs.new_session_dialog import NewSessionDialog
            from .pages.session_page import SessionPage
            from ..models import db as db_mod

            if not db_mod.is_ready():
                QMessageBox.warning(
                    self, "Database Not Ready",
                    "The database is not initialised. Launch the application normally."
                )
                return

            # Save the current session before opening the wizard
            old = self.stack.widget(0)
            if hasattr(old, "_save_timer") and hasattr(old, "_do_autosave"):
                if old._save_timer.isActive():
                    old._save_timer.stop()
                old._do_autosave()

            dlg = NewSessionDialog(self)
            from PySide6.QtWidgets import QDialog
            if dlg.exec() != QDialog.Accepted or dlg.setup is None:
                return

            old = self.stack.widget(0)

            # Replace whatever is at stack index 0
            self.stack.removeWidget(old)
            old.deleteLater()

            session_page = SessionPage(dlg.setup, self)
            self.stack.insertWidget(0, session_page)
            self.sidebar.setCurrentRow(0)
            self.stack.setCurrentIndex(0)

            machine = dlg.setup.linac_name
            self.status.showMessage(f"Session: {machine}  ·  {dlg.setup.center_name}")

        except Exception as exc:
            import traceback
            QMessageBox.critical(
                self, "Session Error",
                f"Failed to build session:\n\n{exc}\n\n{traceback.format_exc()}"
            )

    def _new_session(self):
        self._start_new_session()

    def _resume_worksheet_session(self, ws):
        """Rebuild a SessionPage from a saved WorksheetSession and restore all fields."""
        from PySide6.QtWidgets import QMessageBox
        import json
        try:
            from .dialogs.new_session_dialog import SessionSetup
            from .pages.session_page import SessionPage
            import datetime

            # Reconstruct SessionSetup from the denormalized WorksheetSession fields
            sd = ws.session_date
            if isinstance(sd, datetime.datetime):
                sd = sd.date()
            elif isinstance(sd, str):
                sd = datetime.date.fromisoformat(sd[:10])

            setup = SessionSetup(
                center_id=ws.center_id or 0,
                center_name=ws.center_name,
                linac_id=ws.linac_id or 0,
                linac_name=ws.linac_name,
                linac_model=ws.linac_model,
                chamber_id=ws.chamber_id or 0,
                chamber_model=ws.chamber_model,
                chamber_sn=ws.chamber_sn,
                n_dw_gy_per_c=ws.n_dw_gy_per_c,
                r_cav_cm=ws.r_cav_cm,
                electrometer_id=ws.electrometer_id or 0,
                electrometer_model=ws.electrometer_model,
                electrometer_sn=ws.electrometer_sn,
                p_elec=ws.p_elec,
                physicist=ws.physicist or "",
                session_date=sd,
            )

            # Replace stack index 0 with a new SessionPage
            old = self.stack.widget(0)
            self.stack.removeWidget(old)
            old.deleteLater()

            session_page = SessionPage(setup, self, ws_id=ws.id)
            self.stack.insertWidget(0, session_page)
            self.sidebar.setCurrentRow(0)
            self.stack.setCurrentIndex(0)

            # Restore all field states
            beam_states = json.loads(ws.beam_states_json or "{}")
            session_page.restore_beam_states(beam_states)

            self.status.showMessage(
                f"Resumed session: {ws.linac_name}  ·  {ws.center_name}  "
                f"(saved {ws.updated_at.strftime('%Y-%m-%d %H:%M') if hasattr(ws.updated_at, 'strftime') else ws.updated_at})"
            )
        except Exception as exc:
            import traceback
            QMessageBox.critical(
                self, "Resume Error",
                f"Failed to resume session:\n\n{exc}\n\n{traceback.format_exc()}"
            )

    def _show_about(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About Veritas TG-51",
            "<b>Veritas TG-51</b><br>"
            "AAPM TG-51 Absolute Dosimetry Calibration Application<br><br>"
            "<b>Protocols implemented:</b><br>"
            "• TG-51 (1999) — Almond et al., Med. Phys. 26(9):1847–1870<br>"
            "• WGTG51-X Addendum (2014) — Photon / FFF beams<br>"
            "• WGTG51 Report 374 (2022) — Practical guidance<br>"
            "• WGTG51 Report 385 (2024) — Electron beam addendum<br><br>"
            "<b>Default chamber:</b> Standard Imaging Exradin A12<br>"
            "r_cav = 0.305 cm  |  C-552 wall  |  0.64 cc",
        )

    def _show_references(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Protocol References",
            "1. Almond PR et al. AAPM's TG-51 protocol for clinical reference dosimetry "
            "of high-energy photon and electron beams. "
            "Med. Phys. 1999;26(9):1847–1870.\n\n"
            "2. McEwen MR et al. Addendum to the AAPM's TG-51 protocol for clinical "
            "reference dosimetry of high-energy photon beams. "
            "Med. Phys. 2014;41:041501.\n\n"
            "3. Muir BR et al. AAPM WGTG51 Report 374: Guidance for TG-51 reference "
            "dosimetry. Med. Phys. 2022;49(9):6739–6764.\n\n"
            "4. Muir BR et al. AAPM WGTG51 Report 385: Addendum to the AAPM's TG-51 "
            "protocol for clinical reference dosimetry of high-energy electron beams. "
            "Med. Phys. 2024;51:5840–5857.",
        )
