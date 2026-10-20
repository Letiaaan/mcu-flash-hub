from dataclasses import replace
import subprocess

from intelhex import IntelHex
import pytest
from stcgal.options import Stc89Option

from esp32_rom import ESP32ROM
from flashdesk.catalog import BY_ID, PROFILES
from flashdesk.core import Request, ValidationError, inspect_firmware, make_plan
from flashdesk.options import OptionError, STC_HARDWARE, normalize_options, schema
from flashdesk.runner import Runner
from test_runner import wait_result


def plan_for(binary, profile_id, options=None, eeprom=None, port="COM7"):
    p = BY_ID[profile_id]
    return make_plan(Request(p, inspect_firmware(str(binary)), port, address=p.address,
                             options=options or {}, eeprom=eeprom), resolve_tool=False)


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_defaults_and_foreign_options(profile):
    values = normalize_options(profile, {})
    assert set(values) == {s.key for s in schema(profile)}
    with pytest.raises(OptionError, match="不支持"):
        normalize_options(profile, {"shell_command": "calc.exe"})


@pytest.mark.parametrize("setting", STC_HARDWARE, ids=lambda s: s.key)
def test_all_stc_hardware_options_match_installed_backend(binary, setting):
    actual_keys = {name for name, _, _ in Stc89Option(0xFF).options}
    assert actual_keys == {s.key for s in STC_HARDWARE}
    for value, _ in setting.choices:
        if value == "keep":
            continue
        plan = plan_for(binary, "stc89c52rc", {setting.key: value})
        assert f"{setting.key}={value}" in plan.argv
        assert plan.warnings
        register = Stc89Option(0xFF)
        register.set_option(setting.key, value)
        get = {key: getter for key, getter, _ in register.options}[setting.key]
        assert get() == (value == "true" if value in ("true", "false") else value)
    default = plan_for(binary, "stc89c52rc")
    assert "-o" not in default.argv


def test_stc_handshake_reset_and_logging(binary):
    plan = plan_for(binary, "stc89c52rc", {"handshake_baud": 4800, "autoreset": True, "resetpin": "rts", "debug": True})
    args = plan.argv
    assert args[args.index("-l") + 1] == "4800"
    assert "-a" in args and args[args.index("-A") + 1] == "rts" and "-D" in args


def test_stc_eeprom_and_register_model(app, binary, tmp_path):
    ee = tmp_path / "eeprom.bin"
    ee.write_bytes(b"\x01\x23\x45")
    plan = plan_for(binary, "stc89c52rc", {"cpu_6t_enabled": "true", "xram_enabled": "false"}, inspect_firmware(str(ee)))
    assert plan.argv[-1] == str(ee.resolve())
    runner = Runner(report_dir=tmp_path / "reports")
    report = wait_result(runner, lambda: runner.start(plan, True))
    assert report["result"] == "success", report["log"]
    assert "0xBE" in report["log"]  # FF with 6T bit 0 and XRAM bit 6 cleared by upstream Stc89Option
    assert "EEPROM 内存读回校验通过" in report["log"]
    assert report["plan"]["request"]["options"]["cpu_6t_enabled"] == "true"


def test_esp_capacity_selected_is_used_in_bounds_check(binary):
    plan = plan_for(binary, "esp32", {"flash_size": "16MB"})
    req = replace(plan.request, address=8 * 1024**2)
    make_plan(req, resolve_tool=False)
    with pytest.raises(ValidationError, match="Flash"):
        make_plan(replace(req, options={"flash_size": "4MB"}), resolve_tool=False)


def test_esp_configured_command_with_real_esptool(binary):
    with ESP32ROM() as rom:
        options = {"before": "no-reset", "after": "no-reset", "no_stub": True, "compression": "no",
                   "flash_mode": "dio", "flash_freq": "40m", "connect_attempts": 1}
        plan = make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), f"socket://127.0.0.1:{rom.port}",
                                 address=0x10000, options=options), require_port=False)
        proc = subprocess.run(plan.argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20, encoding="utf-8", errors="replace")
        assert proc.returncode == 0, proc.stdout
        assert "Hash of data verified" in proc.stdout
        assert "--no-compress" in plan.argv


@pytest.mark.parametrize("interface,expected", [("SWD", "port=SWD"), ("JTAG", "port=JTAG"), ("UART", "port=COM7"), ("DFU", "port=usb3")])
def test_stm_interfaces_emit_only_applicable_connection_parameters(binary, interface, expected):
    plan = plan_for(binary, "stm32f401cc" if interface == "DFU" else "stm32f103c8", {"interface": interface, "dfu_index": 3, "frequency": 950})
    assert expected in plan.argv
    assert ("freq=950" in plan.argv) == (interface in ("SWD", "JTAG"))
    assert ("P=EVEN" in plan.argv) == (interface == "UART")
    assert ("-rst" in plan.argv) == (interface in ("SWD", "JTAG"))


def test_stm_reset_and_probe_rules(binary):
    plan = plan_for(binary, "stm32f401cc", {"connect_mode": "UR", "reset_mode": "HWrst", "probe_serial": "003A123456"})
    assert "mode=UR" in plan.argv and "reset=HWrst" in plan.argv and "sn=003A123456" in plan.argv
    assert not any(arg.startswith("index=") for arg in plan.argv)
    with pytest.raises(ValidationError, match="HWrst"):
        plan_for(binary, "stm32f103c8", {"connect_mode": "UR"})
    with pytest.raises(ValidationError, match="连接接口"):
        plan_for(binary, "stm32f103c8", {"interface": "DFU"})


@pytest.mark.parametrize("profile_id,programmer", [("atmega328p", "arduino"), ("atmega2560", "wiring")])
def test_avr_serial_bootloader_configuration(binary, profile_id, programmer):
    plan = plan_for(binary, profile_id, {"programmer": programmer})
    assert programmer in plan.argv and "-P" in plan.argv and "COM7" in plan.argv and "-D" in plan.argv
    assert "-B" not in plan.argv
    with pytest.raises(ValidationError, match="熔丝"):
        plan_for(binary, profile_id, {"programmer": programmer, "lfuse": "0x62"})


def test_avr_isp_fuses_eeprom_and_verify(binary, tmp_path):
    ee = tmp_path / "设备数据.hex"
    image = IntelHex()
    image.frombytes(b"hello", offset=8)
    image.write_hex_file(str(ee))
    options = {"programmer": "avrisp2", "bitclock": "8", "lfuse": "0x62", "hfuse": "0xd9", "efuse": "0xff", "verify": False, "verbose": True}
    plan = plan_for(binary, "atmega328p", options, inspect_firmware(str(ee)))
    assert "-B" in plan.argv and "8" in plan.argv and "-V" in plan.argv and "-v" in plan.argv
    assert "hfuse:w:0xD9:m" in plan.argv and f"eeprom:w:{ee.resolve()}:i" in plan.argv
    assert len(plan.warnings) >= 5


@pytest.mark.parametrize("profile_id,options", [("esp32", {"erase_all": True}), ("stm32f103c8", {"erase_all": True, "verify": False})])
def test_full_erase_and_disabled_verification_are_explicit(binary, profile_id, options):
    plan = plan_for(binary, profile_id, options)
    assert "--erase-all" in plan.argv if profile_id == "esp32" else "-e" in plan.argv
    assert any("全片擦除" in w for w in plan.warnings)
    if options.get("verify") is False:
        assert "-v" not in plan.argv and "关闭" in plan.verification


@pytest.mark.parametrize("profile_id,options", [("esp32", {"flash_size": "999MB"}), ("esp32c3", {"flash_freq": "26m"}),
    ("esp32", {"erase_all": "false"}), ("esp32", {"connect_attempts": True}), ("stm32f103c8", {"probe_serial": "x -e all"}),
    ("atmega328p", {"lfuse": "0x100"}), ("atmega328p", {"hfuse": "0xAA:m -e"}), ("stc89c52rc", {"clock_gain": "max"})])
def test_invalid_or_injected_options_rejected(binary, profile_id, options):
    with pytest.raises(ValidationError):
        plan_for(binary, profile_id, options)


@pytest.mark.parametrize("profile_id", ["atmega328p", "stc89c52rc"])
def test_eeprom_overflow_rejected(binary, tmp_path, profile_id):
    p = BY_ID[profile_id]
    file = tmp_path / "too-big.bin"
    file.write_bytes(b"x" * (p.eeprom_capacity + 1))
    with pytest.raises(ValidationError, match="EEPROM"):
        plan_for(binary, profile_id, eeprom=inspect_firmware(str(file)))


def test_changed_eeprom_rejected_before_start(app, binary, tmp_path):
    file = tmp_path / "data.bin"
    file.write_bytes(b"123")
    plan = plan_for(binary, "atmega328p", eeprom=inspect_firmware(str(file)))
    file.write_bytes(b"456")
    runner = Runner(report_dir=tmp_path)
    with pytest.raises(ValidationError, match="变化"):
        runner.start(plan, True)
    assert not runner.busy
