"""Render our own Qt widget tree for visual QA, without desktop interaction."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from flashdesk.app import configure_application, Window

root = Path(__file__).resolve().parents[1]
app = QApplication([])
for font in ("msyh.ttc", "msyhbd.ttc", "consola.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
configure_application(app, "light")
window = Window()
window.runner.report_dir = root / "docs" / "sample-reports"
window.file.setText(str(root / "examples" / "演练固件.bin"))
window.file_changed()
window.show()
loop = QEventLoop()
window.runner.finished.connect(loop.quit)
window.start()
QTimer.singleShot(10000, loop.quit)
loop.exec()
app.processEvents()
window.grab().save(str(root / "docs" / "preview.png"))
window.close()
