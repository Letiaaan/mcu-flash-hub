"""Exercise Windows first-run scripts without the developer venv or a packaged EXE."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows source launcher")


@pytest.fixture(scope="module")
def clean_source(tmp_path_factory):
    directory = tmp_path_factory.mktemp("source-startup") / "中文源码 & 空格"
    directory.mkdir()
    for name in ("flashdesk", "scripts", "examples"):
        shutil.copytree(ROOT / name, directory / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("main.py", "pyproject.toml", "setup.ps1", "启动工作台.cmd"):
        shutil.copy2(ROOT / name, directory / name)
    assert not (directory / ".venv").exists()
    assert not (directory / "dist").exists()
    return directory


def invoke_source(directory, *args, timeout=240):
    env = dict(os.environ, FLASHDESK_NO_PAUSE="1", PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
    # Invoke cmd from the checked-out directory so '&' in a parent path is never interpreted.
    return subprocess.run([os.environ["COMSPEC"], "/d", "/c", "启动工作台.cmd", *args], cwd=directory,
                          env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)


def test_clean_source_installs_and_runs_full_gui_selftest(clean_source):
    first = invoke_source(clean_source, "-CheckOnly")
    assert first.returncode == 0, first.stdout + first.stderr
    assert "Source environment OK" in first.stdout
    assert "Creating a local Python environment" in first.stdout
    assert (clean_source / "startup.log").is_file()
    source_python = clean_source / ".venv" / "Scripts" / "python.exe"
    assert source_python.is_file()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
    gui = subprocess.run([str(source_python), str(clean_source / "main.py"), "--self-test", str(clean_source / "evidence")],
                         cwd=clean_source, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    assert gui.returncode == 0, gui.stdout + gui.stderr
    evidence = json.loads((clean_source / "evidence" / "self-test.json").read_text(encoding="utf-8"))
    assert evidence["passed"] and len(evidence["runs"]) == 10 and not evidence["hardware_acceptance"]
    second = invoke_source(clean_source, "-CheckOnly")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "Installing dependencies" not in second.stdout
    assert "Source environment OK" in second.stdout


def test_setup_failure_is_visible_and_nonzero(tmp_path):
    for name in ("scripts",):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("setup.ps1", "启动工作台.cmd"):
        shutil.copy2(ROOT / name, tmp_path / name)
    result = invoke_source(tmp_path, "-CheckOnly", "-PythonPath", str(tmp_path / "missing-python.exe"), timeout=20)
    assert result.returncode != 0
    assert "Python executable not found" in result.stdout
    assert "FlashDesk could not start" in result.stdout
    log = (tmp_path / "startup.log").read_text(encoding="utf-8-sig")
    assert "Launch failed" in log and "Python executable not found" in log
