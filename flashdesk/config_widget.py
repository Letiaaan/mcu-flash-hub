"""Render backend option schemas without duplicating validation logic."""
from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget

from .options import capability_note, option_groups, schema


class ConfigWidget(QWidget):
    changed = Signal()
    reset_done = Signal(str)

    def __init__(self, profile, values=None, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.specs = schema(profile)
        self.controls = {}
        self.rows = {}
        self.group_headers = {}
        self.reset_buttons = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        note = QLabel(capability_note(profile))
        note.setWordWrap(True)
        note.setObjectName("muted")
        top = QHBoxLayout()
        top.addWidget(note, 1)
        self.reset_page_button = QPushButton("重置本页")
        self.reset_page_button.setToolTip("恢复本芯片配置页的全部默认值；连接与固件页保持不变。")
        self.reset_page_button.clicked.connect(self.reset_defaults)
        top.addWidget(self.reset_page_button)
        layout.addLayout(top)
        self.form = QFormLayout()
        self.form.setVerticalSpacing(10)
        layout.addLayout(self.form)
        by_key = {spec.key: spec for spec in self.specs}
        ordered = []
        for group_id, title, keys in option_groups(profile):
            header = QWidget()
            row = QHBoxLayout(header)
            row.setContentsMargins(0, 8, 0, 0)
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: 600;")
            row.addWidget(title_label, 1)
            button = QPushButton("重置此分区")
            button.setToolTip(f"只将「{title}」恢复为默认值，包括暂时隐藏的选项。")
            button.clicked.connect(lambda checked=False, group=group_id: self.reset_defaults(group))
            row.addWidget(button)
            self.group_headers[group_id] = header
            self.reset_buttons[group_id] = button
            ordered.append((header, [by_key[key] for key in keys]))
        for header, specs in ordered:
            self.form.addRow(header)
            for spec in specs:
                self._add_option(spec, (values or {}).get(spec.key, spec.default))
        layout.addStretch()
        self.update_visibility()

    def _add_option(self, spec, value):
        if spec.kind == "choice":
            control = QComboBox()
            for val, text in spec.choices:
                control.addItem(text, val)
            control.setCurrentIndex(max(0, control.findData(value)))
            signal = control.currentIndexChanged
        elif spec.kind == "bool":
            control = QCheckBox("启用")
            control.setChecked(value)
            signal = control.toggled
        elif spec.kind == "int":
            control = QSpinBox()
            control.setRange(spec.minimum, spec.maximum)
            control.setValue(value)
            signal = control.valueChanged
        else:
            control = QLineEdit(value)
            control.setPlaceholderText("留空保持原值" if spec.kind == "hexbyte" else "留空使用索引")
            signal = control.textChanged
        control.setObjectName("option_" + spec.key)
        control.setToolTip(spec.help)
        self.controls[spec.key] = control
        title = QLabel(spec.label)
        title.setToolTip(spec.help)
        self.rows[spec.key] = self.form.rowCount()
        self.form.addRow(title, control)
        signal.connect(self._changed)

    def values(self):
        result = {}
        for spec in self.specs:
            widget = self.controls[spec.key]
            result[spec.key] = (widget.currentData() if spec.kind == "choice" else widget.isChecked() if spec.kind == "bool"
                                else widget.value() if spec.kind == "int" else widget.text().strip())
        return result

    def update_visibility(self):
        values = self.values()
        for spec in self.specs:
            self.form.setRowVisible(self.rows[spec.key], spec.active(values))
        by_key = {spec.key: spec for spec in self.specs}
        for group, _, keys in option_groups(self.profile):
            self.form.setRowVisible(self.group_headers[group], any(by_key[key].active(values) for key in keys))

    def reset_defaults(self, group=None):
        # QPushButton.clicked may pass a bool; no group means the entire page.
        if isinstance(group, bool):
            group = None
        groups = {key: (title, keys) for key, title, keys in option_groups(self.profile)}
        if group is not None and group not in groups:
            raise ValueError("Unknown configuration section")
        keys = set(groups[group][1]) if group else {s.key for s in self.specs}
        for spec in self.specs:
            if spec.key not in keys:
                continue
            widget = self.controls[spec.key]
            with QSignalBlocker(widget):
                if spec.kind == "choice":
                    widget.setCurrentIndex(widget.findData(spec.default))
                elif spec.kind == "bool":
                    widget.setChecked(spec.default)
                elif spec.kind == "int":
                    widget.setValue(spec.default)
                else:
                    widget.setText(spec.default)
        self.update_visibility()
        self.changed.emit()
        self.reset_done.emit(groups[group][0] if group else f"{self.profile.name} 配置页")

    def _changed(self, *_):
        self.update_visibility()
        self.changed.emit()
