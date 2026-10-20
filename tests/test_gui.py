from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from flashdesk.app import STYLE, Window
from flashdesk.catalog import PROFILES
from flashdesk.presets import PresetStore, read_preset, write_preset
from test_runner import wait_result


def test_window_virtual_workflow_and_chip_selection(app, binary, tmp_path):
    app.setStyleSheet(STYLE)
    window = Window()
    window.runner.report_dir = tmp_path / "reports"
    window.show()
    app.processEvents()
    assert window.virtual.isChecked()
    window.search.setText("stm32")
    assert not window.profiles.item(3).isHidden()
    assert window.profiles.item(0).isHidden()
    window.search.clear()
    window.profiles.setCurrentRow(3)
    assert window.profile.id == "stm32f103c8"
    assert not window.serial_row.isEnabled()
    window.profiles.setCurrentRow(0)
    window.file.setText(str(binary))
    window.file_changed()
    plan = window.preview()
    assert plan is not None
    assert "write-flash" in window.command.toPlainText()
    report = wait_result(window.runner, window.start)
    app.processEvents()
    assert report["result"] == "success"
    assert window.start_button.isEnabled()
    assert window.export_button.isEnabled()
    assert "虚拟演练" in window.status.text()
    assert "内存读回校验通过" in window.log.toPlainText()
    window.virtual.setChecked(False)
    assert window.start_button.text() == "开始真实烧录"
    assert not window.scenario.isEnabled()
    window.close()


def select_value(control, value):
    index = control.findData(value)
    assert index >= 0
    control.setCurrentIndex(index)


def test_chip_configuration_drafts_and_conditional_controls(app, binary):
    window = Window()
    window.show()
    window.file.setText(str(binary))
    window.address.setText("0x20000")
    select_value(window.config.controls["flash_size"], "16MB")
    select_value(window.config.controls["flash_mode"], "dio")
    window.profiles.setCurrentRow(7)
    assert "cpu_6t_enabled" in window.config.controls
    assert "flash_mode" not in window.config.controls
    select_value(window.config.controls["cpu_6t_enabled"], "true")
    window.profiles.setCurrentRow(0)
    assert window.file.text() == str(binary)
    assert window.address.text() == "0x20000"
    assert window.config.values()["flash_size"] == "16MB"
    assert "16,384" in window.connection.text()
    window.profiles.setCurrentRow(7)
    assert window.config.values()["cpu_6t_enabled"] == "true"
    window.reset_configuration()
    assert window.config.values()["cpu_6t_enabled"] == "keep"
    window.profiles.setCurrentRow(3)
    assert not window.serial_row.isEnabled()
    select_value(window.config.controls["interface"], "UART")
    assert window.serial_row.isEnabled()
    assert window.config.controls["frequency"].isHidden()
    assert not window.config.controls["parity"].isHidden()
    window.profiles.setCurrentRow(5)
    assert not window.serial_row.isEnabled()
    select_value(window.config.controls["programmer"], "arduino")
    assert window.serial_row.isEnabled()
    assert window.config.controls["lfuse"].isHidden()
    window.close()


def test_save_import_export_actual_project_workflow(app, binary, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QInputDialog
    window = Window()
    window.preset_store = PresetStore(tmp_path / "local")
    window.refresh_presets()
    window.file.setText(str(binary))
    select_value(window.config.controls["flash_mode"], "dio")
    suggested = []
    def enter_name(*args, **kwargs):
        suggested.append(kwargs["text"])
        return "我的工程", True
    monkeypatch.setattr(QInputDialog, "getText", enter_name)
    window.save_project()
    saved = window.preset_combo.currentData()
    window.save_project()
    assert suggested[-1] == "我的工程"
    assert window.preset_combo.currentData() == saved
    assert len(window.preset_store.list()) == 1
    assert window.preset_combo.currentData()
    exported = tmp_path / "share" / "工程.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(exported), ""))
    window.export_project()
    assert read_preset(exported)["options"]["flash_mode"] == "dio"
    window.profiles.setCurrentRow(7)
    window.virtual.setChecked(False)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(exported), ""))
    window.import_project()
    assert window.profile.id == "esp32"
    assert window.virtual.isChecked()
    assert window.config.values()["flash_mode"] == "dio"
    assert window.file.text() == str(binary.resolve())
    assert window.build_plan().request.options["flash_mode"] == "dio"
    window.close()


def test_invalid_project_does_not_change_current_form(app):
    import pytest
    from flashdesk.presets import PresetError
    window = Window()
    before = window.capture_state()
    bad = window.project_data("bad")
    bad["options"] = {"cpu_6t_enabled": "true"}
    with pytest.raises(PresetError):
        window.apply_project(bad)
    assert window.capture_state() == before
    window.close()


def test_eeprom_and_dangerous_options_are_visible_in_final_preview(app, binary, tmp_path):
    window = Window()
    window.profiles.setCurrentRow(5)
    window.file.setText(str(binary))
    ee = tmp_path / "data.bin"
    ee.write_bytes(b"123")
    window.eeprom.setText(str(ee))
    window.config.controls["hfuse"].setText("0xD9")
    plan = window.preview()
    assert plan.request.eeprom.path == str(ee.resolve())
    assert "hfuse:w:0xD9:m" in window.command.toPlainText()
    assert "错误熔丝" in window.command.toPlainText()
    window.profiles.setCurrentRow(0)
    assert window.eeprom_row.isHidden()
    assert window.eeprom.text() == ""
    window.close()
