import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from flashdesk.app import SettingsDialog, Window
from flashdesk.catalog import PROFILES, TOOL_LABELS
from flashdesk.options import normalize_options, option_groups, schema
from flashdesk.presets import PresetStore


def modify_options(config):
    for spec in config.specs:
        widget = config.controls[spec.key]
        if spec.kind == "choice":
            widget.setCurrentIndex(next(i for i, (value, _) in enumerate(spec.choices) if value != spec.default))
        elif spec.kind == "bool":
            widget.setChecked(not spec.default)
        elif spec.kind == "int":
            widget.setValue(spec.minimum if spec.minimum != spec.default else spec.maximum)
        else:
            widget.setText("0xD9" if spec.kind == "hexbyte" else "PROBE123")


@pytest.mark.parametrize("index", range(len(PROFILES)), ids=lambda i: PROFILES[i].id)
def test_section_and_page_resets_leave_other_configuration_intact(app, binary, index):
    window = Window()
    window.profiles.setCurrentRow(index)
    window.file.setText(str(binary))
    window.port.setCurrentText("COM9")
    window.timeout.setValue(99)
    baseline = window.capture_state()
    groups = option_groups(window.profile)
    covered = [key for _, _, keys in groups for key in keys]
    assert len(covered) == len(set(covered)) == len(schema(window.profile))
    defaults = normalize_options(window.profile, {})
    for group, _, keys in groups:
        modify_options(window.config)
        before = window.config.values()
        # Emit an actual button click; visibility may depend on the selected protocol.
        window.config.reset_buttons[group].click()
        after = window.config.values()
        assert all(after[key] == defaults[key] for key in keys)
        assert all(after[key] == before[key] for key in after if key not in keys)
        state = window.capture_state()
        assert all(state[key] == value for key, value in baseline.items() if key != "options")
        assert not window.runner.busy
    modify_options(window.config)
    window.command.setPlainText("stale command")
    window.config.reset_page_button.click()
    assert window.config.values() == defaults
    assert window.command.toPlainText() == ""
    assert window.file.text() == str(binary) and window.port.currentText() == "COM9"
    assert window.timeout.value() == 99
    window.close()


def test_basic_reset_clears_only_its_page_and_recomputes_file_state(app, binary):
    window = Window()
    window.profiles.setCurrentRow(7)
    modify_options(window.config)
    before = window.config.values()
    window.file.setText(str(binary))
    window.eeprom.setText(str(binary))
    window.port.setCurrentText("COM7")
    window.address.setText("0x20")
    window.baud.setCurrentText("57600")
    window.timeout.setValue(20)
    window.scenario.setCurrentIndex(2)
    window.virtual.setChecked(False)
    window.command.setPlainText("stale command")
    window.reset_basic_button.click()
    state = window.capture_state()
    assert state["firmware"] == state["eeprom"] == state["port"] == ""
    assert state["address"] == hex(window.profile.address)
    assert state["baud"] == 115200 and state["timeout"] == 180
    assert window.scenario.currentData() == "success"
    assert window.config.values() == before
    assert not window.virtual.isChecked() and not window.runner.busy
    assert window.command.toPlainText() == "" and "选择文件后" in window.fw_info.text()
    window.close()


def test_reset_does_not_overwrite_saved_project_or_other_chip_draft(app, binary, tmp_path):
    window = Window()
    window.preset_store = PresetStore(tmp_path / "presets")
    window.file.setText(str(binary))
    control = window.config.controls["flash_mode"]
    control.setCurrentIndex(control.findData("dio"))
    saved = window.preset_store.save(window.project_data("保留方案"))
    before = saved.read_bytes()
    window.profiles.setCurrentRow(7)
    window.file.setText(str(binary))
    modify_options(window.config)
    window.reset_configuration()
    assert window.file.text() == ""
    assert window.config.values() == normalize_options(window.profile, {})
    assert saved.read_bytes() == before
    window.profiles.setCurrentRow(0)
    assert window.file.text() == str(binary)
    assert window.config.values()["flash_mode"] == "dio"
    window.profiles.setCurrentRow(7)
    assert window.file.text() == ""
    assert window.config.values() == normalize_options(window.profile, {})
    window.close()


def test_reset_buttons_are_disabled_while_a_task_is_active(app):
    window = Window()
    window.set_busy(True)
    assert not window.reset_basic_button.isEnabled()
    assert not window.config.reset_page_button.isEnabled()
    assert all(not button.isEnabled() for button in window.config.reset_buttons.values())
    window.set_busy(False)
    window.close()


@pytest.mark.parametrize("tool", tuple(TOOL_LABELS))
def test_each_tool_path_can_reset_without_changing_others(app, tool):
    paths = {key: f"C:/tools/{key}.exe" for key in TOOL_LABELS}
    dialog = SettingsDialog(paths)
    dialog.reset_buttons[tool].click()
    after = dialog.values()
    assert after[tool] == ""
    assert all(after[key] == value for key, value in paths.items() if key != tool)
    assert paths[tool]  # caller's saved configuration is untouched until Save
    dialog.reject()
