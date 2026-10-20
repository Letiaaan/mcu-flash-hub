from __future__ import annotations

import codecs
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from .core import Plan, check_unchanged


def data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FlashDesk"


class Runner(QObject):
    output = Signal(str)
    finished = Signal(dict)
    busy_changed = Signal(bool)

    def __init__(self, parent=None, report_dir: Path | None = None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timeout)
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self.process.kill)
        self.report_dir = report_dir or data_dir() / "runs"
        self.busy = False
        self.report = {}
        self.stop_reason = ""

    def start(self, plan: Plan, virtual: bool, scenario: str = "success") -> None:
        if self.busy:
            raise ValueError("已有任务正在执行。")
        check_unchanged(plan.request.firmware)
        if plan.request.eeprom:
            check_unchanged(plan.request.eeprom)
        if scenario not in ("success", "connection", "verify", "timeout"):
            raise ValueError("未知的虚拟场景。")
        argv = list(plan.argv)
        if virtual:
            spec = json.dumps({"request": plan.serializable()["request"], "scenario": scenario}, ensure_ascii=False)
            argv = ([sys.executable, "--simulate", spec] if getattr(sys, "frozen", False)
                    else [sys.executable, "-m", "flashdesk.simulator", spec])
        self.report = {"schema_version": 1, "id": uuid.uuid4().hex, "mode": "virtual" if virtual else "real",
                       "started_at": datetime.now(timezone.utc).isoformat(), "plan": plan.serializable(),
                       "executed_argv": argv, "log": "", "virtual_scenario": scenario if virtual else None,
                       "hardware_acceptance": False,
                       "scope": "虚拟内存流程测试" if virtual else "后端工具执行结果；实物验收需人工确认芯片与运行效果"}
        self.stop_reason = ""
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        env = self.process.processEnvironment()
        if env.isEmpty():
            from PySide6.QtCore import QProcessEnvironment
            env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("NO_COLOR", "1")
        self.process.setProcessEnvironment(env)
        self.process.setProgram(argv[0])
        self.process.setArguments(argv[1:])
        self.busy = True
        self.busy_changed.emit(True)
        self.timer.start(plan.request.timeout * 1000)
        self.process.start()

    def cancel(self) -> None:
        if self.busy and not self.stop_reason:
            self.stop_reason = "cancelled"
            self._append("\n任务已请求取消；真实设备可能需要重新烧录。\n")
            self.process.terminate()
            self.kill_timer.start(1500)

    def shutdown(self, grace_ms: int = 300, kill_ms: int = 1700) -> bool:
        """Stop this runner's child and persist its result before the GUI exits."""
        self.timer.stop()
        self.kill_timer.stop()
        if self.busy and not self.stop_reason:
            self.stop_reason = "cancelled"
            self._append("\n主界面关闭，正在停止工具并退出；真实设备可能需要重新烧录。\n")
        if self.process.state() == QProcess.ProcessState.Starting:
            self.process.waitForStarted(grace_ms)
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(grace_ms)
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(kill_ms)
        stopped = self.process.state() == QProcess.ProcessState.NotRunning
        if stopped and self.busy:
            # Failed starts do not always emit finished; keep the audit record complete.
            self._read()
            self._append(self.decoder.decode(b"", final=True))
            self._complete(self.process.exitCode(), self.stop_reason or "cancelled")
        return stopped

    def _timeout(self):
        if self.busy:
            self.stop_reason = "timeout"
            self._append("\n工具执行超时，正在停止。\n")
            self.process.kill()

    def _append(self, text: str):
        # Keep UI responsive even if an external CLI floods the pipe.
        limit = 4 * 1024 * 1024
        remaining = max(0, limit - len(self.report["log"]))
        self.report["log"] += text[:remaining]
        if len(text) > remaining:
            self.report["log_truncated"] = True
        self.output.emit(text[-65536:])

    def _read(self):
        self._append(self.decoder.decode(bytes(self.process.readAllStandardOutput())).replace("\r\n", "\n").replace("\r", "\n"))

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.busy:
            self._append(f"工具无法启动：{self.process.errorString()}\n")
            self._complete(-1, "failed")

    def _finished(self, code, status):
        if not self.busy:
            return
        self._read()
        self._append(self.decoder.decode(b"", final=True))
        success = code == 0 and status == QProcess.ExitStatus.NormalExit
        self._complete(code, self.stop_reason or ("success" if success else "failed"))

    def _complete(self, code: int, result: str):
        self.timer.stop()
        self.kill_timer.stop()
        self.report.update(exit_code=code, result=result, finished_at=datetime.now(timezone.utc).isoformat())
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            dest = self.report_dir / f"{self.report['id']}.json"
            temp = dest.with_suffix(".tmp")
            temp.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(dest)
            self.report["report_path"] = str(dest)
        except OSError as exc:
            self.report["report_error"] = str(exc)
        self.busy = False
        self.busy_changed.emit(False)
        self.finished.emit(dict(self.report))
