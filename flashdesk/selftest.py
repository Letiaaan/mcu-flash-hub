"""Hardware-free smoke test of the actual GUI and its bundled subprocess."""
import json
import os
from pathlib import Path


def run(output_dir: str) -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from .app import STYLE, Window

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    for font in ("msyh.ttc", "msyhbd.ttc", "consola.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    window = Window()
    window.runner.report_dir = output / "runs"
    window.show()
    results = []
    ee = output / "virtual-eeprom.bin"
    ee.write_bytes(b"FlashDesk virtual EEPROM")
    for index in (0, 3, 5, 7):
        window.profiles.setCurrentRow(index)
        window.load_example()
        window.timeout.setValue(5)
        if index == 0:
            control = window.config.controls["flash_mode"]
            control.setCurrentIndex(control.findData("dio"))
        if index in (5, 7):
            window.eeprom.setText(str(ee))
        if index == 7:
            control = window.config.controls["cpu_6t_enabled"]
            control.setCurrentIndex(control.findData("true"))
        loop = QEventLoop()
        window.runner.finished.connect(loop.quit)
        window.start()
        if window.runner.busy:
            loop.exec()
        window.runner.finished.disconnect(loop.quit)
        app.processEvents()
        result = window.last_report or {}
        results.append(result)
        if index == 0:
            window.grab().save(str(output / "preview.png"))
        window.tabs.setCurrentIndex(1)
        app.processEvents()
        window.grab().save(str(output / f"preview-{window.profile.id}.png"))
        window.tabs.setCurrentIndex(0)
    success = all(r.get("result") == "success" and r.get("mode") == "virtual" and
                  "内存读回校验通过" in r.get("log", "") for r in results)
    success = success and window.start_button.isEnabled() and window.export_button.isEnabled()
    summary = {"passed": success, "mode": "virtual", "hardware_acceptance": False,
               "run": results[0], "runs": results, "screenshot": str(output / "preview.png")}
    (output / "self-test.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    window.close()
    print(json.dumps({"passed": success, "report": str(output / "self-test.json")}, ensure_ascii=False))
    return 0 if success else 1
