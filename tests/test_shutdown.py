"""Closing the UI must cancel its own tool and leave no live QProcess behind."""
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QProcess

from flashdesk.app import SettingsDialog, Window
from flashdesk.catalog import BY_ID
from flashdesk.core import Request, inspect_firmware, make_plan
from flashdesk.runner import Runner


@pytest.mark.parametrize("wait_started", [False, True])
def test_shutdown_stops_starting_or_running_child_and_persists_cancel(app, binary, tmp_path, wait_started):
    runner = Runner(report_dir=tmp_path)
    p = BY_ID["esp32"]
    plan = make_plan(Request(p, inspect_firmware(str(binary)), address=p.address), require_port=False, resolve_tool=False)
    runner.start(plan, True, "timeout")
    if wait_started:
        assert runner.process.waitForStarted(2000)
    assert runner.shutdown()
    assert not runner.busy and runner.process.state() == QProcess.ProcessState.NotRunning
    assert not runner.timer.isActive() and not runner.kill_timer.isActive()
    report = json.loads(Path(runner.report["report_path"]).read_text(encoding="utf-8"))
    assert report["result"] == "cancelled" and report["hardware_acceptance"] is False
    assert runner.shutdown()  # Cleanup is safe to call again from aboutToQuit / finally.


def test_main_window_close_stops_child_without_a_blocking_dialog(app, binary, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: pytest.fail("Close must not block on a dialog"))
    window = Window()
    window.runner.report_dir = tmp_path
    window.file.setText(str(binary))
    window.scenario.setCurrentIndex(window.scenario.findData("timeout"))
    window.show()
    window.start()
    assert window.runner.process.waitForStarted(2000)
    requested = []
    window.exit_requested.connect(lambda: requested.append(True))
    assert window.close()
    assert requested == [True] and not window.isVisible()
    assert not window.runner.busy
    assert window.runner.process.state() == QProcess.ProcessState.NotRunning
    assert window.last_report["result"] == "cancelled"


def test_idle_main_window_close_also_closes_settings_and_requests_exit(app):
    window = Window()
    settings = SettingsDialog({}, window)
    window.show()
    settings.show()
    app.processEvents()
    requested = []
    window.exit_requested.connect(lambda: requested.append(True))
    assert window.close()
    assert requested == [True] and not window.isVisible() and not settings.isVisible()
