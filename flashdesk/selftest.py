"""Hardware-free smoke test of the actual GUI and its bundled subprocess."""
import json
import os
from pathlib import Path


def shutdown_checks(app, output, first_window):
    """Run the actual application event loop and close its primary window."""
    from PySide6.QtCore import QProcess, QTimer
    from .app import SettingsDialog, Window, run_window

    checks = []
    for mode in ("idle", "starting", "running", "settings"):
        window = first_window if mode == "idle" else Window()
        window.runner.report_dir = output / "shutdown-runs" / mode
        child_pids = []
        dialogs = []

        def close_running():
            child_pids.append(int(window.runner.process.processId()))
            QTimer.singleShot(30, window.close)

        def begin():
            if mode in ("starting", "running"):
                window.load_example()
                window.scenario.setCurrentIndex(window.scenario.findData("timeout"))
                if mode == "running":
                    window.runner.process.started.connect(close_running)
                window.start()
                if mode == "starting":
                    window.close()
            else:
                if mode == "settings":
                    dialog = SettingsDialog({}, window)
                    dialogs.append(dialog)
                    dialog.show()
                window.close()

        def abort():
            window.runner.shutdown(grace_ms=0)
            app.exit(99)

        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(abort)
        watchdog.start(10000)
        QTimer.singleShot(0, begin)
        code = run_window(app, window)
        watchdog.stop()
        stopped = window.runner.process.state() == QProcess.ProcessState.NotRunning
        result = window.last_report.get("result") if window.last_report else None
        checks.append({"mode": mode, "exit_code": code, "child_pids": child_pids,
                       "stopped": stopped, "visible": window.isVisible(), "result": result,
                       "dialogs_closed": all(not d.isVisible() for d in dialogs)})
    return checks


def run(output_dir: str) -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from .app import configure_application, Window
    from .catalog import PROFILES

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    configure_application(app)
    for font in ("msyh.ttc", "msyhbd.ttc", "consola.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    window = Window()
    window.runner.report_dir = output / "runs"
    window.show()
    results = []
    ee = output / "virtual-eeprom.bin"
    ee.write_bytes(b"FlashDesk virtual EEPROM")
    ids = ("esp32", "stm32f103c8", "atmega328p", "stc89c52rc", "stc15f2k60s2", "stc8g1k08",
           "at89s52", "at89c51", "stm32f103c8-openocd", "stm32f103c8-uart")
    for profile_id in ids:
        index = next(i for i, p in enumerate(PROFILES) if p.id == profile_id)
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
        if profile_id in ("stc15f2k60s2", "stc8g1k08"):
            control = window.config.controls["watchdog_por_enabled"]
            control.setCurrentIndex(control.findData("false"))
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
        if profile_id.startswith("stc") or profile_id.startswith("at89"):
            window.family_filter.setCurrentIndex(window.family_filter.findData("8051"))
        app.processEvents()
        window.grab().save(str(output / f"preview-{window.profile.id}.png"))
        window.family_filter.setCurrentIndex(0)
        window.tabs.setCurrentIndex(0)
    success = all(r.get("result") == "success" and r.get("mode") == "virtual" and
                  "内存读回校验通过" in r.get("log", "") for r in results)
    success = success and window.start_button.isEnabled() and window.export_button.isEnabled()
    themes = {}
    from PySide6.QtGui import QPalette
    for theme in ("light", "dark"):
        configure_application(app, theme)
        app.processEvents()
        window.grab().save(str(output / f"preview-theme-{theme}.png"))
        themes[theme] = window.tabs.widget(0).widget().palette().color(QPalette.ColorRole.Window).name()
    success = success and themes == {"light": "#f0f4f8", "dark": "#141c27"}
    shutdown = shutdown_checks(app, output, window)
    success = success and all(c["exit_code"] == 0 and c["stopped"] and not c["visible"] and c["dialogs_closed"]
                              and (c["result"] == "cancelled" if c["mode"] in ("starting", "running") else True)
                              for c in shutdown)
    summary = {"passed": success, "mode": "virtual", "hardware_acceptance": False,
               "run": results[0], "runs": results, "themes": themes, "shutdown": shutdown,
               "screenshot": str(output / "preview.png")}
    (output / "self-test.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": success, "report": str(output / "self-test.json")}, ensure_ascii=False))
    return 0 if success else 1
