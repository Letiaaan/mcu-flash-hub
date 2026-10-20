import json

import pytest

from flashdesk.catalog import PROFILES
from flashdesk.presets import PresetError, PresetStore, read_preset, validate_preset, write_preset


def project(profile, binary):
    return {"schema_version": 1, "name": "测试工程", "profile_id": profile.id, "firmware": str(binary.resolve()),
            "eeprom": "", "port": "COM9", "baud": 115200, "address": hex(profile.address), "timeout": 60, "options": {}}


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_project_roundtrip_and_relative_paths(tmp_path, binary, profile):
    data = project(profile, binary)
    file = tmp_path / "project" / "生产方案.json"
    write_preset(file, data)
    raw = json.loads(file.read_text(encoding="utf-8"))
    assert raw["firmware"].startswith("..")
    assert read_preset(file) == validate_preset(data)
    assert "argv" not in raw and "virtual" not in raw


@pytest.mark.parametrize("key,value", [("schema_version", 999), ("schema_version", True), ("profile_id", "unknown"),
    ("options", {"resetcmd": "calc.exe"}), ("options", {"erase_all": "false"}), ("baud", 42), ("timeout", 0),
    ("address", "invalid"), ("address", "-1"), ("name", ""), ("firmware", "a\0b"), ("eeprom", "unwanted.bin")])
def test_invalid_projects_rejected(binary, key, value):
    data = project(PROFILES[0], binary)
    data[key] = value
    with pytest.raises(PresetError):
        validate_preset(data)


def test_unknown_fields_and_truncated_json_rejected(binary, tmp_path):
    data = project(PROFILES[0], binary)
    data["tool_executable"] = "malicious.exe"
    with pytest.raises(PresetError):
        validate_preset(data)
    file = tmp_path / "bad.json"
    file.write_text("{bad", encoding="utf-8")
    with pytest.raises(PresetError):
        read_preset(file)


def test_local_store_save_update_and_bad_file_preservation(binary, tmp_path):
    store = PresetStore(tmp_path / "presets")
    data = project(PROFILES[0], binary)
    first = store.save(data)
    data["options"] = {"flash_mode": "dio"}
    store.save(data, first)
    assert len(store.list()) == 1
    assert store.list()[0][1]["options"]["flash_mode"] == "dio"
    bad = store.folder / "corrupt.json"
    bad.write_text("not json", encoding="utf-8")
    assert len(store.list()) == 1 and bad.read_text(encoding="utf-8") == "not json"
    with pytest.raises(PresetError):
        store.save(data, tmp_path / "outside.json")
