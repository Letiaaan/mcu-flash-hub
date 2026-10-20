import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
import pytest

from flashdesk.catalog import BY_ID, PROFILES
from flashdesk.core import Plan, Request, inspect_firmware, make_plan
from flashdesk.runner import Runner


def wait_result(runner, start, cancel_after=None):
    loop = QEventLoop()
    result = []
    def done(report):
        result.append(report)
        loop.quit()
    runner.finished.connect(done)
    watchdog = QTimer()
    watchdog.setSingleShot(True)
    watchdog.timeout.connect(loop.quit)
    watchdog.start(14000)
    start()
    if cancel_after:
        QTimer.singleShot(cancel_after, runner.cancel)
    loop.exec()
    watchdog.stop()
    if not result:
        runner.process.kill()
        runner.process.waitForFinished(2000)
    assert result, "runner did not complete before watchdog"
    return result[0]


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_all_profiles_virtual_success_are_audited_as_virtual(app, binary, tmp_path, profile):
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(profile, inspect_firmware(str(binary)), address=profile.address), require_port=False, resolve_tool=False)
    report = wait_result(runner, lambda: runner.start(plan, True))
    assert report["result"] == "success" and report["exit_code"] == 0
    assert report["mode"] == "virtual" and report["hardware_acceptance"] is False
    assert "内存读回校验通过" in report["log"]
    persisted = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
    assert persisted["plan"]["request"]["firmware"]["sha256"] == plan.request.firmware.sha256


@pytest.mark.parametrize("scenario,expected,code", [("connection", "failed", 2), ("verify", "failed", 4), ("timeout", "timeout", None)])
def test_failures_are_not_reported_as_success(app, binary, tmp_path, scenario, expected, code):
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), address=0x10000, timeout=5), require_port=False, resolve_tool=False)
    report = wait_result(runner, lambda: runner.start(plan, True, scenario))
    assert report["result"] == expected
    if code is not None:
        assert report["exit_code"] == code
    assert not runner.busy


def test_cancel_and_rerun(app, binary, tmp_path):
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), address=0x10000), require_port=False, resolve_tool=False)
    report = wait_result(runner, lambda: runner.start(plan, True, "timeout"), cancel_after=300)
    assert report["result"] == "cancelled"
    assert runner.process.state() == runner.process.ProcessState.NotRunning
    report = wait_result(runner, lambda: runner.start(plan, True))
    assert report["result"] == "success"


def test_missing_executable_completes(app, binary, tmp_path):
    runner = Runner(report_dir=tmp_path / "reports")
    req = Request(BY_ID["esp32"], inspect_firmware(str(binary)), "COM9", address=0x10000)
    plan = Plan(req, (str(tmp_path / "missing.exe"),), "test only")
    report = wait_result(runner, lambda: runner.start(plan, False))
    assert report["result"] == "failed" and report["exit_code"] == -1


def test_real_esptool_missing_port_reports_failure(app, binary, tmp_path):
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), "COM9999", address=0x10000, timeout=10))
    report = wait_result(runner, lambda: runner.start(plan, False))
    assert report["result"] == "failed" and report["exit_code"] != 0
    assert "esptool" in report["log"]


def test_real_stcgal_missing_port_reports_failure(app, binary, tmp_path):
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(BY_ID["stc89c52rc"], inspect_firmware(str(binary)), "COM9999", address=0, timeout=10))
    report = wait_result(runner, lambda: runner.start(plan, False))
    assert report["result"] == "failed" and report["exit_code"] != 0


def test_duplicate_start_rejected(app, binary, tmp_path):
    runner = Runner(report_dir=tmp_path)
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), address=0x10000), require_port=False, resolve_tool=False)
    def start():
        runner.start(plan, True, "timeout")
        with pytest.raises(ValueError, match="已有"):
            runner.start(plan, True)
    report = wait_result(runner, start, cancel_after=100)
    assert report["result"] == "cancelled"
