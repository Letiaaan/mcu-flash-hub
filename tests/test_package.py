"""Optional acceptance of the actual distributable, after running build.ps1."""
import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
import pytest

from esp32_rom import ESP32ROM
from flashdesk.catalog import BY_ID
from flashdesk.core import Request, inspect_firmware, make_plan
from flashdesk.runner import Runner
from test_runner import wait_result

EXE = Path(__file__).resolve().parents[1] / "dist" / "FlashDesk" / "FlashDesk.exe"
pytestmark = pytest.mark.skipif(not EXE.is_file(), reason="Run build.ps1 to test the distributable")


@pytest.mark.parametrize("tool,args,expected", [("esptool", ["version"], "5.1.0"), ("stcgal", ["-V"], "1.10")])
def test_bundled_tools_launch(tool, args, expected):
    proc = subprocess.run([str(EXE), "--tool", tool, *args], capture_output=True, encoding="utf-8", timeout=15)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert expected in proc.stdout


@pytest.mark.parametrize("scenario", ["success", "corrupt", "wrong_chip"])
def test_bundled_esptool_actual_rom_protocol(binary, scenario):
    with ESP32ROM(corrupt=scenario == "corrupt", wrong_chip=scenario == "wrong_chip") as rom:
        proc = subprocess.run([str(EXE), "--tool", "esptool", "--chip", "esp32", "--port", f"socket://127.0.0.1:{rom.port}",
                               "--before", "no-reset", "--after", "no-reset", "--no-stub", "write-flash", "--flash-size", "4MB",
                               "0x10000", str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              encoding="utf-8", errors="replace", timeout=20)
        if scenario == "success":
            assert proc.returncode == 0, proc.stdout
            assert "Hash of data verified" in proc.stdout
            assert rom.memory[0x10000:0x10000 + binary.stat().st_size] == binary.read_bytes()
        else:
            assert proc.returncode != 0, proc.stdout
            if scenario == "wrong_chip":
                assert 0x03 not in rom.commands
            else:
                assert "does not match" in proc.stdout


@pytest.mark.parametrize("scenario,expected", [("success", "success"), ("verify", "failed"), ("timeout", "timeout"), ("connection", "failed")])
def test_packaged_subprocesses_through_runner(app, binary, tmp_path, monkeypatch, scenario, expected):
    monkeypatch.setattr(sys, "executable", str(EXE))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    runner = Runner(report_dir=tmp_path / "reports")
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), address=0x10000, timeout=5), require_port=False)
    report = wait_result(runner, lambda: runner.start(plan, True, scenario))
    assert report["result"] == expected, report["log"]
    assert report["executed_argv"][0] == str(EXE)
    if scenario == "success":
        assert "内存读回校验通过" in report["log"]


def test_packaged_child_cancellation(app, binary, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "executable", str(EXE))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    runner = Runner(report_dir=tmp_path)
    plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), address=0x10000), require_port=False)
    report = wait_result(runner, lambda: runner.start(plan, True, "timeout"), cancel_after=300)
    assert report["result"] == "cancelled"


def test_actual_packaged_gui_and_child(tmp_path):
    proc = subprocess.run([str(EXE), "--self-test", str(tmp_path)], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=20)
    assert proc.returncode == 0, proc.stdout
    result = json.loads((tmp_path / "self-test.json").read_text(encoding="utf-8"))
    assert result["passed"] is True and result["mode"] == "virtual"
    assert len(result["runs"]) == 4
    stc = result["runs"][-1]
    assert stc["plan"]["request"]["options"]["cpu_6t_enabled"] == "true"
    assert "EEPROM 内存读回校验通过" in stc["log"]
    assert (tmp_path / "preview.png").stat().st_size > 10000
