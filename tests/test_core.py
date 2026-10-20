from dataclasses import replace
import sys

from intelhex import IntelHex
import pytest

from flashdesk.catalog import BY_ID, PROFILES
from flashdesk.core import Request, ValidationError, check_unchanged, inspect_firmware, make_plan


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_bin_plan_keeps_path_one_argument_and_enables_verification(profile, binary):
    fw = inspect_firmware(str(binary))
    req = Request(profile, fw, "COM7", address=profile.address)
    plan = make_plan(req, {profile.tool: sys.executable})
    if profile.tool == "avrdude":
        assert plan.argv[-1] == f"flash:w:{fw.path}:r"
        assert "-V" not in plan.argv and "-F" not in plan.argv
    elif profile.tool == "openocd":
        assert "{" + binary.resolve().as_posix() + "}" in plan.argv[-1]
    else:
        assert fw.path in plan.argv
    if profile.tool == "stm32cube":
        assert "-v" in plan.argv
    assert plan.verification
    assert "--force" not in plan.argv


@pytest.mark.parametrize("profile", [p for p in PROFILES if ".hex" in p.formats], ids=lambda p: p.id)
def test_hex_uses_embedded_address(profile, tmp_path):
    path = tmp_path / "test.hex"
    image = IntelHex()
    image.frombytes(b"\x12\x34\x56", offset=profile.base)
    image.write_hex_file(str(path))
    fw = inspect_firmware(str(path))
    plan = make_plan(Request(profile, fw, "COM8", address=profile.address), {profile.tool: sys.executable})
    assert fw.start == profile.base and fw.end == profile.base + 3
    if profile.tool == "stm32cube":
        assert hex(profile.address) not in plan.argv
    if profile.tool == "avrdude":
        assert plan.argv[-1].endswith(":i")


@pytest.mark.parametrize("content,extension", [(b"", ".bin"), (b"bad", ".hex"), (b":0300000012345600\n:00000001FF\n", ".hex"), (b"abc", ".elf")])
def test_bad_firmware_rejected(tmp_path, content, extension):
    file = tmp_path / ("bad" + extension)
    file.write_bytes(content)
    with pytest.raises(ValidationError):
        inspect_firmware(str(file))


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_range_overflow_rejected(profile, binary):
    fw = inspect_firmware(str(binary))
    req = Request(profile, fw, "COM1", address=profile.base + profile.capacity - 1)
    with pytest.raises(ValidationError, match="Flash"):
        make_plan(req, resolve_tool=False)


def test_hex_outside_selected_chip_rejected(tmp_path):
    file = tmp_path / "wrong.hex"
    image = IntelHex()
    image.frombytes(b"\x01", offset=0x08000000)
    image.write_hex_file(str(file))
    with pytest.raises(ValidationError, match="HEX"):
        make_plan(Request(BY_ID["atmega328p"], inspect_firmware(str(file))), resolve_tool=False)


@pytest.mark.parametrize("port", ["", "socket://127.0.0.1:42", "COM0", "COM3 & calc", "COM3\n"])
def test_real_mode_rejects_invalid_ports(binary, port):
    with pytest.raises(ValidationError, match="串口"):
        make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), port, address=0x10000))


def test_virtual_mode_does_not_require_installed_external_tools(binary):
    p = BY_ID["stm32f103c8"]
    plan = make_plan(Request(p, inspect_firmware(str(binary)), address=p.address), resolve_tool=False)
    assert plan.argv[0] == "STM32_Programmer_CLI.exe"


def test_changed_file_rejected(binary):
    fw = inspect_firmware(str(binary))
    binary.write_bytes(b"replacement")
    with pytest.raises(ValidationError, match="变化"):
        check_unchanged(fw)


@pytest.mark.parametrize("content", [":0100000001FE\n", ":00000001FF\n:0100000001FE\n:00000001FF\n"])
def test_incomplete_or_trailing_hex_rejected(tmp_path, content):
    file = tmp_path / "bad.hex"
    file.write_text(content, encoding="ascii")
    with pytest.raises(ValidationError, match="HEX"):
        inspect_firmware(str(file))


def test_missing_tool_is_actionable(binary, tmp_path):
    with pytest.raises(ValidationError, match="工具文件不存在"):
        make_plan(Request(BY_ID["esp32"], inspect_firmware(str(binary)), "COM1", address=0x10000),
                  {"esptool": str(tmp_path / "missing.exe")})


@pytest.mark.parametrize("field,value", [("timeout", 0), ("timeout", 3601), ("baud", 12345), ("address", -1)])
def test_invalid_options(binary, field, value):
    req = Request(BY_ID["esp32"], inspect_firmware(str(binary)), "COM1", address=0x10000)
    with pytest.raises(ValidationError):
        make_plan(replace(req, **{field: value}), resolve_tool=False)
