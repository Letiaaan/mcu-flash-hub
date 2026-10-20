from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QSplitter,
    QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)
from serial.tools import list_ports

from .catalog import BY_ID, PROFILES, TOOL_LABELS, TOOL_URLS, is_8051
from .core import Request, ValidationError, inspect_firmware, make_plan, tool_command
from .runner import Runner, data_dir
from .config_widget import ConfigWidget
from .options import flash_capacity, needs_serial, normalize_options, schema
from .presets import PresetError, PresetStore, read_preset, validate_preset, write_preset
from . import __version__


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI'; font-size: 13px; color: #172D43; }
QMainWindow, QDialog { background: #F0F4F8; }
QFrame#sidebar { background: #E6EDF5; border-right: 1px solid #CFD9E4; }
QLabel#brand { font-size: 26px; font-weight: 700; color: #175CD3; }
QLabel#title { font-size: 24px; font-weight: 700; }
QLabel#muted { color: #576D83; }
QLabel#notice { background: #FFF3D6; color: #795100; padding: 10px 12px; border-radius: 5px; }
QLabel#status { font-size: 15px; font-weight: 600; padding: 6px 0; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 11px 8px; border-radius: 5px; margin: 2px 0; }
QListWidget::item:selected { background: #175CD3; color: white; }
QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #BCCBD9; border-radius: 4px; padding: 7px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid #175CD3; }
QLineEdit:disabled, QComboBox:disabled { background: #E6EDF5; color: #576D83; }
QPushButton { background: white; border: 1px solid #BCCBD9; border-radius: 5px; padding: 9px 14px; }
QPushButton:hover { background: #E4EDFD; border-color: #175CD3; }
QPushButton:focus { border: 2px solid #175CD3; }
QPushButton:disabled { color: #8A9AAC; background: #EDF1F5; }
QPushButton#primary { background: #175CD3; color: white; border-color: #175CD3; font-weight: 600; }
QPushButton#primary:hover { background: #104EB8; }
QPushButton#primary:disabled { background: #9AAFCB; border-color: #9AAFCB; }
QPlainTextEdit { background: white; border: 1px solid #CFD9E4; border-radius: 5px; padding: 8px; font-family: Consolas; font-size: 12px; }
QProgressBar { background: #DCE5EF; border: none; border-radius: 3px; max-height: 5px; }
QProgressBar::chunk { background: #175CD3; border-radius: 3px; }
QCheckBox { spacing: 8px; }
QSplitter::handle { background: #CFD9E4; height: 1px; }
QTabWidget::pane { border: 1px solid #CFD9E4; background: #F0F4F8; }
QTabBar::tab { padding: 8px 18px; background: #E6EDF5; border: 1px solid #CFD9E4; }
QTabBar::tab:selected { background: white; color: #175CD3; border-bottom-color: #175CD3; }
QScrollArea { border: none; background: transparent; }
"""


def chip_icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#175CD3"))
    painter.setBrush(QColor("#175CD3"))
    painter.drawRoundedRect(14, 14, 36, 36, 5, 5)
    for i in (21, 31, 41):
        painter.drawRect(i, 6, 3, 8)
        painter.drawRect(i, 50, 3, 8)
        painter.drawRect(6, i, 8, 3)
        painter.drawRect(50, i, 8, 3)
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Consolas", 21, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "F")
    painter.end()
    return QIcon(pix)


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


class SettingsDialog(QDialog):
    def __init__(self, overrides, parent=None):
        super().__init__(parent)
        self.setWindowTitle("烧录工具设置")
        self.resize(820, 600)
        layout = QVBoxLayout(self)
        layout.addWidget(label("esptool 与 stcgal 已集成；其余工具需单独安装并选择 EXE。", wrap=True))
        layout.addWidget(label("留空时自动查找。请保留外部工具的配置、数据库、DLL 和 scripts 目录；AT89S 需 AVRDUDE 8.1+。", "muted", True))
        self.edits = {}
        self.reset_buttons = {}
        form = QFormLayout()
        for key, name in TOOL_LABELS.items():
            row = QHBoxLayout()
            edit = QLineEdit(overrides.get(key, ""))
            edit.setPlaceholderText("内置工具" if key in ("esptool", "stcgal") else "自动查找 / 选择 EXE")
            browse = QPushButton("选择")
            browse.clicked.connect(lambda checked=False, e=edit: self.browse(e))
            reset = QPushButton("重置")
            reset.setToolTip("恢复此工具的内置 / 自动查找方式；保存后生效。")
            reset.clicked.connect(edit.clear)
            self.reset_buttons[key] = reset
            docs = QPushButton("官方说明")
            docs.clicked.connect(lambda checked=False, k=key: QDesktopServices.openUrl(QUrl(TOOL_URLS[k])))
            row.addWidget(edit, 1)
            row.addWidget(browse)
            row.addWidget(reset)
            row.addWidget(docs)
            form.addRow(name, row)
            self.edits[key] = edit
        content = QWidget()
        content.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse(self, edit):
        path, _ = QFileDialog.getOpenFileName(self, "选择烧录工具", "", "可执行文件 (*.exe)")
        if path:
            edit.setText(path)

    def values(self):
        return {key: edit.text().strip() for key, edit in self.edits.items()}


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashDesk · 单片机烧录工作台")
        self.setWindowIcon(chip_icon())
        self.resize(1180, 940)
        self.setMinimumSize(1000, 780)
        self.settings = QSettings("FlashDesk", "FlashDesk")
        self.overrides = {key: self.settings.value(f"tools/{key}", "", str) for key in TOOL_LABELS}
        self.runner = Runner(self)
        self.runner.output.connect(self.append_log)
        self.runner.finished.connect(self.completed)
        self.runner.busy_changed.connect(self.set_busy)
        self.last_report = None
        self.profile = PROFILES[0]
        self._drafts = {}
        self._active_id = None
        self._loading = False
        self.preset_store = PresetStore(data_dir() / "presets")
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 24, 16, 20)
        side.addWidget(label("▣  FlashDesk", "brand"))
        side.addWidget(label("单片机烧录工作台", "muted"))
        side.addSpacing(24)
        self.search = QLineEdit()
        self.search.setPlaceholderText("查找芯片 / 厂商")
        self.search.textChanged.connect(self.filter_profiles)
        side.addWidget(self.search)
        self.family_filter = QComboBox()
        for title, value in (("全部系列", "all"), ("51 / 8051", "8051"), ("STM32", "stm32"), ("AVR", "avr"), ("ESP", "esp")):
            self.family_filter.addItem(title, value)
        self.family_filter.currentIndexChanged.connect(self.filter_profiles)
        side.addWidget(self.family_filter)
        self.profiles = QListWidget()
        for p in PROFILES:
            item = QListWidgetItem(f"{p.name}\n{p.family}")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.profiles.addItem(item)
        self.profiles.currentItemChanged.connect(self.select_profile)
        side.addWidget(self.profiles, 1)
        self.settings_button = QPushButton("工具设置")
        self.settings_button.clicked.connect(self.edit_settings)
        side.addWidget(self.settings_button)
        history = QPushButton("打开任务记录")
        history.clicked.connect(self.open_history)
        side.addWidget(history)
        side.addWidget(label(f"v{__version__}   /   Windows\n{len(PROFILES)} 个烧录配置 · {len(TOOL_LABELS)} 个工具", "muted"))
        outer.addWidget(sidebar)

        main = QVBoxLayout()
        main.setContentsMargins(28, 22, 28, 20)
        main.setSpacing(12)
        outer.addLayout(main, 1)
        header = QHBoxLayout()
        self.title = label(self.profile.name, "title")
        header.addWidget(self.title)
        header.addStretch()
        self.virtual = QCheckBox("虚拟演练")
        self.virtual.setChecked(True)
        self.virtual.toggled.connect(self.mode_changed)
        header.addWidget(self.virtual)
        main.addLayout(header)
        self.project_panel = QWidget()
        projects = QHBoxLayout(self.project_panel)
        projects.setContentsMargins(0, 0, 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(180)
        self.preset_combo.currentIndexChanged.connect(self.load_selected_preset)
        projects.addWidget(self.preset_combo, 1)
        for text, callback in (("保存方案", self.save_project), ("导入", self.import_project),
                               ("导出", self.export_project), ("重置全部", self.reset_configuration)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            projects.addWidget(button)
        main.addWidget(self.project_panel)
        self.notice = label("虚拟演练只操作内存模型，不连接硬件。通过演练不代表芯片已通过实物验收。", "notice", True)
        main.addWidget(self.notice)

        self.form_panel = QWidget()
        panel = QVBoxLayout(self.form_panel)
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setSpacing(10)
        self.profile_note = label("", "muted", True)
        panel.addWidget(self.profile_note)
        self.tabs = QTabWidget()
        self.tabs.setFixedHeight(350)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        basic_header = QWidget()
        basic_header_layout = QHBoxLayout(basic_header)
        basic_header_layout.setContentsMargins(0, 0, 0, 0)
        basic_header_layout.addWidget(label("连接与固件参数"), 1)
        self.reset_basic_button = QPushButton("重置本页")
        self.reset_basic_button.setToolTip("清空本页文件和端口，恢复默认地址、波特率、超时与演练场景；芯片配置页保持不变。")
        self.reset_basic_button.clicked.connect(self.reset_basic)
        basic_header_layout.addWidget(self.reset_basic_button)
        form.addRow(basic_header)
        self.connection = label("")
        form.addRow("连接方式", self.connection)
        self.tool_status = label("", wrap=True)
        form.addRow("烧录工具", self.tool_status)
        row = QHBoxLayout()
        self.port = QComboBox()
        self.port.setEditable(True)
        self.port.setMinimumWidth(170)
        refresh = QPushButton("刷新串口")
        refresh.clicked.connect(self.refresh_ports)
        self.baud = QComboBox()
        self.baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud.setCurrentText("115200")
        row.addWidget(self.port, 1)
        row.addWidget(refresh)
        row.addSpacing(12)
        row.addWidget(label("波特率"))
        row.addWidget(self.baud)
        self.serial_row = QWidget()
        serial_layout = QHBoxLayout(self.serial_row)
        serial_layout.setContentsMargins(0, 0, 0, 0)
        serial_layout.addLayout(row)
        form.addRow("串口", self.serial_row)
        self.file = QLineEdit()
        self.file.setPlaceholderText("选择 .bin / .hex / .ihx 固件")
        browse = QPushButton("选择固件")
        browse.clicked.connect(self.browse_firmware)
        self.example_button = QPushButton("演练固件")
        self.example_button.clicked.connect(self.load_example)
        file_row = QHBoxLayout()
        file_row.addWidget(self.file, 1)
        file_row.addWidget(browse)
        file_row.addWidget(self.example_button)
        form.addRow("固件文件", file_row)
        self.fw_info = label("选择文件后显示大小、地址范围和 SHA-256。", "muted", True)
        self.fw_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("文件检查", self.fw_info)
        self.eeprom = QLineEdit()
        self.eeprom.setPlaceholderText("可选；留空不单独写入 EEPROM")
        ee_browse = QPushButton("选择 EEPROM")
        ee_browse.clicked.connect(self.browse_eeprom)
        ee_clear = QPushButton("清空")
        ee_clear.clicked.connect(self.eeprom.clear)
        self.eeprom_row = QWidget()
        ee_row = QHBoxLayout(self.eeprom_row)
        ee_row.setContentsMargins(0, 0, 0, 0)
        ee_row.addWidget(self.eeprom, 1)
        ee_row.addWidget(ee_browse)
        ee_row.addWidget(ee_clear)
        form.addRow("EEPROM", self.eeprom_row)
        self.basic_form = form
        self.address = QLineEdit("0x10000")
        self.address.setMaximumWidth(190)
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 3600)
        self.timeout.setValue(180)
        self.timeout.setSuffix(" 秒")
        options = QHBoxLayout()
        options.addWidget(self.address)
        options.addStretch()
        options.addWidget(label("任务超时"))
        options.addWidget(self.timeout)
        form.addRow("BIN 起始地址", options)
        self.scenario = QComboBox()
        for name, value in (("正常写入与校验", "success"), ("连接失败", "connection"), ("读回校验失败", "verify"), ("工具无响应（测试超时）", "timeout")):
            self.scenario.addItem(name, value)
        form.addRow("演练场景", self.scenario)
        basic = QWidget()
        basic.setLayout(form)
        basic_scroll = QScrollArea()
        basic_scroll.setWidgetResizable(True)
        basic_scroll.setWidget(basic)
        self.tabs.addTab(basic_scroll, "连接与固件")
        self.advanced_scroll = QScrollArea()
        self.advanced_scroll.setWidgetResizable(True)
        self.tabs.addTab(self.advanced_scroll, "芯片配置")
        self.config = ConfigWidget(self.profile)
        self.advanced_scroll.setWidget(self.config)
        panel.addWidget(self.tabs)
        self.config_summary = label("", "muted", True)
        panel.addWidget(self.config_summary)
        main.addWidget(self.form_panel)

        buttons = QHBoxLayout()
        self.preview_button = QPushButton("检查并预览命令")
        self.preview_button.clicked.connect(self.preview)
        self.start_button = QPushButton("开始虚拟演练")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("取消任务")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.runner.cancel)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch()
        main.addLayout(buttons)
        self.command = QPlainTextEdit()
        self.command.setReadOnly(True)
        self.command.setMaximumHeight(70)
        self.command.setPlaceholderText("检查固件后在这里预览命令；虚拟演练不会执行此硬件命令。")
        main.addWidget(self.command)
        status_row = QHBoxLayout()
        self.status = label("等待选择固件", "status")
        status_row.addWidget(self.status, 1)
        self.export_button = QPushButton("导出本次报告")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_report)
        status_row.addWidget(self.export_button)
        main.addLayout(status_row)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        main.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(125)
        self.log.setMaximumBlockCount(6000)
        self.log.setPlaceholderText("工具的原始输出会显示在这里。任务会自动记录模式、命令、固件指纹和退出状态。")
        main.addWidget(self.log, 1)
        main.addWidget(label("当前配置仅完成软件与虚拟验收。真实工具返回成功后，仍需检查目标芯片的实际运行。", "muted", True))
        self.file.editingFinished.connect(self.file_changed)
        for field in (self.file, self.address, self.eeprom):
            field.textChanged.connect(self.invalidate_preview)
        self.port.currentTextChanged.connect(self.invalidate_preview)
        self.baud.currentTextChanged.connect(self.invalidate_preview)
        self.timeout.valueChanged.connect(self.invalidate_preview)
        self.profiles.setCurrentRow(0)
        self.refresh_ports()
        self.refresh_presets()

    def invalidate_preview(self, *_):
        self.command.clear()

    def filter_profiles(self, *_):
        value = self.search.text().strip().lower()
        family = self.family_filter.currentData()
        for i in range(self.profiles.count()):
            item = self.profiles.item(i)
            profile = BY_ID[item.data(Qt.ItemDataRole.UserRole)]
            matches = {"all": True, "8051": is_8051(profile), "stm32": profile.chip.startswith("STM32"),
                       "avr": profile.family == "Microchip AVR", "esp": profile.tool == "esptool"}[family]
            item.setHidden(not matches or value not in (item.text() + " " + TOOL_LABELS[profile.tool]).lower())

    def select_profile(self, item, previous=None):
        if item is None:
            return
        if self._active_id and not self._loading:
            self._drafts[self._active_id] = self.capture_state()
        self.profile = BY_ID[item.data(Qt.ItemDataRole.UserRole)]
        self._active_id = self.profile.id
        p = self.profile
        self.title.setText(p.name)
        self.profile_note.setText(p.note)
        self.connection.setText(f"{p.connection}  /  Flash {p.capacity // 1024:,} KB")
        self.restore_state(self._drafts.get(p.id, self.default_state()))
        self.update_tool_status()
        self.invalidate_preview()
        self.file_changed(silent=True)

    def default_state(self):
        return {"firmware": "", "eeprom": "", "port": self.port.currentText(), "baud": 115200,
                "address": hex(self.profile.address), "timeout": 180, "options": {}}

    def capture_state(self):
        return {"firmware": self.file.text().strip(), "eeprom": self.eeprom.text().strip(),
                "port": self.port.currentText().strip(), "baud": int(self.baud.currentText()),
                "address": self.address.text().strip(), "timeout": self.timeout.value(), "options": self.config.values()}

    def restore_state(self, state):
        self.file.setText(state["firmware"])
        self.eeprom.setText(state["eeprom"])
        self.port.setCurrentText(state["port"])
        self.baud.setCurrentText(str(state["baud"]))
        self.address.setText(state["address"])
        self.timeout.setValue(state["timeout"])
        old = self.advanced_scroll.takeWidget()
        if old:
            old.deleteLater()
        self.config = ConfigWidget(self.profile, state["options"])
        self.advanced_scroll.setWidget(self.config)
        self.config.changed.connect(self.configuration_changed)
        self.config.reset_done.connect(lambda name: self.status.setText(f"「{name}」已恢复初始默认值 · 尚未保存方案"))
        self.basic_form.setRowVisible(self.eeprom_row, bool(self.profile.eeprom_capacity))
        self.tabs.setTabText(1, f"{self.profile.name} 配置")
        self.configuration_changed()
        self.file_changed(silent=True)

    def configuration_changed(self):
        values = self.config.values()
        self.serial_row.setEnabled(needs_serial(self.profile, values))
        capacity = flash_capacity(self.profile, values)
        self.connection.setText(f"{self.profile.connection}  /  Flash {capacity // 1024:,} KB")
        changed = [s.label for s in schema(self.profile) if s.active(values) and values[s.key] != s.default]
        text = "、".join(changed[:3]) + (f" 等 {len(changed)} 项" if len(changed) > 3 else "")
        self.config_summary.setText(f"已修改配置：{text}" if changed else "芯片配置使用默认值；硬件选项保持原值。")
        self.invalidate_preview()

    def reset_configuration(self):
        state = dict(self.default_state(), port="")
        self.restore_state(state)
        self.scenario.setCurrentIndex(0)
        self.status.setText("当前芯片的两个配置页已重置 · 尚未保存方案")

    def reset_basic(self):
        self.file.clear()
        self.eeprom.clear()
        self.port.setCurrentText("")
        self.address.setText(hex(self.profile.address))
        self.baud.setCurrentText("115200")
        self.timeout.setValue(180)
        self.scenario.setCurrentIndex(0)
        self.file_changed(silent=True)
        self.invalidate_preview()
        self.status.setText("「连接与固件」已恢复初始默认值 · 芯片配置保持不变")

    def project_data(self, name):
        return validate_preset(dict(self.capture_state(), schema_version=1, name=name, profile_id=self.profile.id))

    def refresh_presets(self, selected=None):
        with QSignalBlocker(self.preset_combo):
            self.preset_combo.clear()
            self.preset_combo.addItem("选择已保存的工程方案…", None)
            for path, data in self.preset_store.list():
                self.preset_combo.addItem(f"{data['name']}  /  {BY_ID[data['profile_id']].name}", str(path))
            if selected:
                self.preset_combo.setCurrentIndex(max(0, self.preset_combo.findData(str(selected))))

    def apply_project(self, data):
        # Validate the entire document before touching widgets. Importing always returns to virtual mode.
        data = validate_preset(data)
        if self._active_id:
            self._drafts[self._active_id] = self.capture_state()
        self._drafts[data["profile_id"]] = data
        self._loading = True
        try:
            index = next(i for i, p in enumerate(PROFILES) if p.id == data["profile_id"])
            self.search.clear()
            self.family_filter.setCurrentIndex(0)
            with QSignalBlocker(self.profiles):
                self.profiles.setCurrentRow(index)
            self.select_profile(self.profiles.item(index))
            self.virtual.setChecked(True)
        finally:
            self._loading = False
        self.status.setText(f"已载入方案「{data['name']}」· 请检查固件后执行")

    def load_selected_preset(self, *_):
        value = self.preset_combo.currentData()
        if value:
            try:
                self.apply_project(read_preset(Path(value)))
            except (PresetError, OSError) as exc:
                QMessageBox.warning(self, "无法载入方案", str(exc))

    def save_project(self):
        current = self.preset_combo.currentData()
        old = None
        if current:
            try:
                old = read_preset(Path(current))
            except (PresetError, OSError):
                pass
        suggested = old["name"] if old and old["profile_id"] == self.profile.id else self.profile.name + " 工程"
        name, ok = QInputDialog.getText(self, "保存工程方案", "方案名称", text=suggested)
        if ok:
            try:
                data = self.project_data(name.strip())
                path = None
                if old and old["name"] == data["name"] and old["profile_id"] == data["profile_id"]:
                    path = Path(current)
                dest = self.preset_store.save(data, path)
                self.refresh_presets(dest)
                self.status.setText(f"已保存方案「{name.strip()}」")
            except (PresetError, OSError) as exc:
                QMessageBox.warning(self, "方案保存失败", str(exc))

    def import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入工程方案", "", "FlashDesk 方案 (*.json)")
        if path:
            try:
                data = read_preset(Path(path))
                self.apply_project(data)
                self.refresh_presets(self.preset_store.save(data))
            except (PresetError, OSError) as exc:
                QMessageBox.warning(self, "方案导入失败", str(exc))

    def export_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出工程方案", f"{self.profile.id}-方案.json", "FlashDesk 方案 (*.json)")
        if path:
            try:
                write_preset(Path(path), self.project_data(Path(path).stem))
                self.status.setText("工程方案已导出；固件文件需另行携带")
            except (PresetError, OSError) as exc:
                QMessageBox.warning(self, "方案导出失败", str(exc))

    def update_tool_status(self):
        try:
            cmd = tool_command(self.profile.tool, self.overrides)
            self.tool_status.setText(f"{TOOL_LABELS[self.profile.tool]}  ·  {'已集成' if len(cmd) > 1 else cmd[0]}")
        except ValidationError as exc:
            self.tool_status.setText(str(exc))

    def refresh_ports(self):
        current = self.port.currentText()
        self.port.clear()
        for port in list_ports.comports():
            self.port.addItem(port.device)
            self.port.setItemData(self.port.count() - 1, port.description, Qt.ItemDataRole.ToolTipRole)
        if current:
            self.port.setCurrentText(current)
        self.port.setPlaceholderText("未检测到串口，可手动输入 COM3")

    def browse_firmware(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择固件", "", "固件文件 (*.bin *.hex *.ihx *.ihex);;所有文件 (*)")
        if path:
            self.file.setText(path)
            self.file_changed()

    def browse_eeprom(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 EEPROM 数据", "", "EEPROM 数据 (*.bin *.hex *.ihx *.ihex)")
        if path:
            self.eeprom.setText(path)

    def load_example(self):
        root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        self.file.setText(str(root / "examples" / "演练固件.bin"))
        self.file_changed()

    def file_changed(self, silent=False):
        is_hex = Path(self.file.text()).suffix.lower() in (".hex", ".ihx", ".ihex")
        self.address.setEnabled(not is_hex and self.profile.tool not in ("avrdude", "stcgal", "minipro"))
        if not self.file.text().strip():
            self.fw_info.setText("选择文件后显示大小、地址范围和 SHA-256。")
            return
        try:
            fw = inspect_firmware(self.file.text())
            bounds = f"  /  HEX 地址 {hex(fw.start)}–{hex(fw.end - 1)}" if is_hex else ""
            self.fw_info.setText(f"{fw.size:,} 字节{bounds}\nSHA-256  {fw.sha256}")
        except (ValidationError, OSError) as exc:
            self.fw_info.setText(str(exc))

    def mode_changed(self, virtual):
        self.start_button.setText("开始虚拟演练" if virtual else "开始真实烧录")
        self.notice.setText("虚拟演练只操作内存模型，不连接硬件。通过演练不代表芯片已通过实物验收。" if virtual
                            else "真实烧录将写入所选设备。请核对芯片、连接、供电及固件；任务中断后可能需要重新烧录。")
        self.scenario.setEnabled(virtual)
        self.example_button.setEnabled(virtual)
        self.invalidate_preview()

    def build_plan(self):
        fw = inspect_firmware(self.file.text())
        try:
            address = self.profile.address if fw.format == ".hex" else int(self.address.text().strip(), 0)
        except ValueError as exc:
            raise ValidationError("地址应为 0x08000000 这样的十六进制数，或十进制整数。") from exc
        ee = inspect_firmware(self.eeprom.text().strip()) if self.eeprom.text().strip() else None
        request = Request(self.profile, fw, self.port.currentText().strip(), int(self.baud.currentText()), address,
                          self.timeout.value(), self.config.values(), ee)
        virtual = self.virtual.isChecked()
        return make_plan(request, self.overrides, require_port=not virtual, resolve_tool=not virtual)

    def preview(self):
        try:
            plan = self.build_plan()
            self.command.setPlainText(plan.display)
            if plan.warnings:
                self.command.appendPlainText("\n" + "\n".join(plan.warnings))
            self.command.moveCursor(QTextCursor.MoveOperation.Start)
            self.file_changed()
            self.status.setText("检查通过 · 虚拟演练就绪" if self.virtual.isChecked() else "检查通过 · 真实烧录就绪")
            return plan
        except (ValidationError, OSError) as exc:
            self.status.setText("检查未通过")
            QMessageBox.warning(self, "请检查烧录参数", str(exc))
            return None

    def start(self):
        plan = self.preview()
        if plan is None:
            return
        virtual = self.virtual.isChecked()
        if not virtual:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("确认真实烧录")
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setText(f"将向 {self.profile.name} 写入固件。\n{plan.request.firmware.path}\n\n{plan.verification}")
            dialog.setInformativeText("\n".join(plan.warnings) or "请确认目标设备与芯片型号正确。底层工具可能擦除相关 Flash 页面。")
            details = plan.display + "\n程序 SHA-256: " + plan.request.firmware.sha256
            if plan.request.eeprom:
                details += "\nEEPROM SHA-256: " + plan.request.eeprom.sha256
            dialog.setDetailedText(details)
            dialog.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if dialog.exec() != QMessageBox.StandardButton.Ok:
                return
        self.log.clear()
        self.status.setText("虚拟演练执行中" if virtual else "真实烧录执行中")
        try:
            self.runner.start(plan, virtual, self.scenario.currentData())
        except (ValidationError, ValueError, OSError) as exc:
            self.status.setText("任务未启动")
            QMessageBox.warning(self, "无法启动", str(exc))

    def set_busy(self, busy):
        for widget in (self.form_panel, self.project_panel, self.profiles, self.search, self.virtual, self.settings_button, self.preview_button, self.start_button):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.progress.setRange(0, 0 if busy else 1)
        self.progress.setValue(0)

    def append_log(self, value):
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(value)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def completed(self, report):
        self.last_report = report
        self.export_button.setEnabled(True)
        names = {"success": "完成", "failed": "失败，请检查日志", "cancelled": "已取消", "timeout": "超时，已停止"}
        prefix = "虚拟演练" if report["mode"] == "virtual" else "真实工具执行"
        self.status.setText(f"{prefix} · {names[report['result']]}")
        if report["result"] == "success":
            self.progress.setValue(1)
        self.append_log(f"\n任务结果：{report['result']}；退出码：{report['exit_code']}\n")
        if report.get("report_path"):
            self.append_log(f"记录已保存：{report['report_path']}\n")
        else:
            self.append_log(f"记录保存失败，请手动导出：{report.get('report_error')}\n")

    def edit_settings(self):
        dialog = SettingsDialog(self.overrides, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.overrides = dialog.values()
            for key, value in self.overrides.items():
                self.settings.setValue(f"tools/{key}", value)
            self.update_tool_status()
            self.invalidate_preview()

    def open_history(self):
        folder = data_dir() / "runs"
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def export_report(self):
        if not self.last_report:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出本次任务报告", f"FlashDesk-{self.last_report['id'][:8]}.json", "JSON 报告 (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps(self.last_report, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "导出失败", str(exc))

    def closeEvent(self, event):
        if self.runner.busy:
            QMessageBox.information(self, "任务执行中", "请先取消任务，等待工具停止后再关闭窗口。")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(chip_icon())
    window = Window()
    window.show()
    return app.exec()
