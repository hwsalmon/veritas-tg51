"""
main.py — Veritas TG-51 application entry point.

Launch:
    python -m veritas_tg51.main
    or
    python veritas_tg51/main.py
"""

import sys
import os

# Ensure the project root is on the path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from veritas_tg51.ui.main_window import MainWindow
from veritas_tg51.models.entities import init_db
from veritas_tg51.models import db as db_mod


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Veritas TG-51")
    app.setOrganizationName("Medical Physics")
    app.setApplicationVersion("1.0.0")
    _icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon.png")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # Initialise database
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "veritas.db")
    engine = init_db(db_path)
    db_mod.set_engine(engine)

    window = MainWindow()
    window.show()

    # Restore the most recently saved worksheet session on startup
    try:
        sessions = db_mod.fetch_worksheet_sessions(limit=1)
        if sessions:
            window._resume_worksheet_session(sessions[0])
    except Exception:
        pass  # don't block startup if restore fails

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
