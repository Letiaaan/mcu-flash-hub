"""Contracts for added adapters; these checks do not certify physical devices."""
from dataclasses import replace
from pathlib import Path

from intelhex import IntelHex
import pytest
from stcgal.models import MCUModelDatabase

from flashdesk.app import Window
from flashdesk.catalog import BY_ID, PROFILES, is_8051, stc_protocol
from flashdesk.core import Request, ValidationError, inspect_firmware, make_plan
from flashdesk.options import normalize_options, schema, stc_hardware, stc_option_registers
from flashdesk.simulator import run


def plan(binary, profile_id, **options):
    p = BY_ID[profile_id]
    return make_plan(Request(p, inspect_firmware(str(binary)), "COM7", address=p.address, options=options), resolve_tool=False)


@pytest.mark.parametrize("profile", [p for p in PROFILES if p.tool == "stcgal"], ids=lambda p: p.id)
def test_stc_catalog_sizes_and_hardware_against_installed_upstream(profile, binary, capsys):
    name = "STC89C52RC/LE52RC" if profile.id == "stc89c52rc" else profile.chip
    model = next(m for m in MCUModelDatabase.models if m.name == name)
    assert (profile.capacity, profile.eeprom_capacity) == (model.code, model.eeprom)
    default = plan(binary, profile.id)
    assert default.argv[default.argv.index("-P") + 1] == stc_protocol(profile)
    assert "-o" not in default.argv and "-t" not in default.argv
    for spec in stc_hardware(profile):
        for value, _ in spec.choices:
            if value == "keep":
                continue
            register = stc_option_registers(profile)
            register.set_option(spec.key, value)
            getter = {key: get for key, get, _ in register.options}[spec.key]
            expected = value == "true" if value in ("true", "false") else int(value) if value.isdigit() else value
            assert getter() == expected
            current = plan(binary, profile.id, **{spec.key: value})
            assert f"{spec.key}={value}" in current.argv
    # Also execute a nondefault register configuration through the virtual process entry point.
    changed = {s.key: next(v for v, _ in s.choices if v != "keep") for s in stc_hardware(profile)}
    import json
    assert run(json.dumps(plan(binary, profile.id, **changed).serializable())) == 0
    assert "不是实物读回" in capsys.readouterr().out


@pytest.mark.parametrize("profile_id", ["stc15f104e", "stc15f2k60s2", "stc8a8k64s4a12", "stc8g1k08"])
def test_stc_trim_is_opt_in(binary, profile_id):
    current = plan(binary, profile_id, trim_frequency=24000)
    assert current.argv[current.argv.index("-t") + 1] == "24000"


@pytest.mark.parametrize("profile_id,part", [("at89s51", "89S51"), ("at89s52", "89S52")])
def test_at89s_uses_8051_ids_and_excludes_avr_features(binary, profile_id, part):
    p = BY_ID[profile_id]
    current = plan(binary, profile_id)
    assert current.argv[current.argv.index("-p") + 1] == part
    assert current.argv[current.argv.index("-B") + 1] == "32"
    assert not {"lfuse", "hfuse", "efuse"} & {s.key for s in schema(p)}
    with pytest.raises(ValidationError):
        plan(binary, profile_id, programmer="arduino")
    current = plan(binary, profile_id, programmer="avrisp")
    assert "COM7" in current.argv and "-D" not in current.argv and "-B" not in current.argv
    with pytest.raises(ValidationError, match="EEPROM"):
        make_plan(replace(current.request, eeprom=inspect_firmware(str(binary))), resolve_tool=False)


@pytest.mark.parametrize("profile_id", ["atmega8", "atmega16", "atmega32"])
def test_legacy_avr_has_no_extended_fuse(binary, profile_id):
    assert "efuse" not in normalize_options(BY_ID[profile_id], {})
    assert "hfuse:w:0xD9:m" in plan(binary, profile_id, hfuse="0xd9").argv
    with pytest.raises(ValidationError):
        plan(binary, profile_id, efuse="0xff")


def test_openocd_cli_contract_and_hex_offset(binary, tmp_path):
    current = plan(binary, "stm32f103c8-openocd", adapter="cmsis-dap", frequency=500, probe_serial="ABC_123")
    assert "interface/cmsis-dap.cfg" in current.argv and "transport select swd" in current.argv
    assert "target/stm32f1x.cfg" in current.argv and "adapter serial ABC_123" in current.argv
    assert "gdb_port disabled" in current.argv
    assert current.argv[-1].endswith(" verify reset exit 0x8000000")
    assert "{" + binary.resolve().as_posix() + "}" in current.argv[-1]
    file = tmp_path / "firmware.hex"
    image = IntelHex()
    image.frombytes(b"test", offset=0x08001000)
    image.write_hex_file(str(file))
    current = plan(file, "stm32f401cc-openocd", verify=False, reset_after=False)
    assert current.argv[-1].endswith("} exit") and "0x8000000" not in current.argv[-1]
    assert "关闭" in current.verification


@pytest.mark.parametrize("name", ["firm$ware.bin", "firm;ware.bin", "firm[ware].bin", "firm{ware}.bin"])
def test_openocd_rejects_tcl_path_characters(tmp_path, name):
    file = tmp_path / name
    file.write_bytes(b"1234")
    with pytest.raises(ValidationError, match="Tcl"):
        plan(file, "stm32f103c8-openocd")


def test_stm32flash_preserves_bin_offset_limits_erase_and_verifies(binary):
    current = plan(binary, "stm32f103c8-uart")
    assert current.argv[current.argv.index("-S") + 1] == "0x8000000:2048"
    assert "-f" in current.argv and "-v" in current.argv and "-g" in current.argv
    assert current.argv[-1] == "COM7"
    current = plan(binary, "stm32f103c8-uart", erase_policy="none", verify=False, run_after=False)
    assert current.argv.index("-e") < current.argv.index("-S")
    assert "-v" not in current.argv and "-g" not in current.argv
    shifted = make_plan(replace(current.request, address=0x08001000), resolve_tool=False)
    assert "0x8001000:2048" in shifted.argv
    with pytest.raises(ValidationError, match="对齐"):
        make_plan(replace(current.request, address=0x08000001), resolve_tool=False)
    assert not {"-u", "-j", "-k"} & set(current.argv)


def test_minipro_keeps_id_check_and_verifies_by_default(binary):
    current = plan(binary, "at89c51")
    assert "AT89C51@DIP40" in current.argv and "-s" in current.argv
    assert not {"-y", "-x", "-v", "-f", "-o"} & set(current.argv)
    assert "-v" in plan(binary, "at89c51", verify=False).argv
    with pytest.raises(ValidationError, match="容量末尾"):
        plan(binary, "at89c51", allow_short=False)
    with pytest.raises(ValidationError, match="Flash"):
        make_plan(replace(current.request, firmware=replace(current.request.firmware, end=4097)), resolve_tool=False)


@pytest.mark.parametrize("extension", [".hex", ".ihx", ".ihex"])
def test_sdcc_intel_hex_aliases(extension, tmp_path):
    file = tmp_path / ("student" + extension)
    image = IntelHex()
    image.frombytes(b"\x02\x00\x10\x00", offset=0)
    image.write_hex_file(str(file))
    fw = inspect_firmware(str(file))
    assert fw.format == ".hex" and fw.start == 0 and fw.end == 4
    assert plan(file, "stc89c51rc").argv[-1] == str(file.resolve())
    assert plan(file, "at89s52").argv[-1].endswith(":i")


def test_backend_specific_hex_limits(tmp_path):
    file = tmp_path / "student.IHX"
    image = IntelHex()
    image.frombytes(b"test", offset=0)
    image.write_hex_file(str(file))
    with pytest.raises(ValidationError, match="大小写"):
        plan(file, "stc89c51rc")
    image = IntelHex()
    image.frombytes(b"test", offset=0x08000000)
    image.write_hex_file(str(file))
    with pytest.raises(ValidationError, match="扩展名"):
        plan(file, "stm32f103c8-openocd")
    with pytest.raises(ValidationError, match="仅支持"):
        plan(file, "stm32f103c8-uart")


def test_family_filter_combines_search_and_import_resets_it(app, binary):
    window = Window()
    window.family_filter.setCurrentIndex(window.family_filter.findData("8051"))
    shown = [p for i, p in enumerate(PROFILES) if not window.profiles.item(i).isHidden()]
    assert len(shown) == 14 and all(is_8051(p) for p in shown)
    window.search.setText("STC15")
    shown = [p for i, p in enumerate(PROFILES) if not window.profiles.item(i).isHidden()]
    assert len(shown) == 3
    from test_presets import project
    window.apply_project(project(BY_ID["stm32f401cc-openocd"], binary))
    assert window.family_filter.currentData() == "all" and not window.search.text()
    assert window.profile.id == "stm32f401cc-openocd"
    assert not window.profiles.currentItem().isHidden()
    window.close()
