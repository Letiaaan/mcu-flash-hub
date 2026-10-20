"""Pure planning and validation. No hardware I/O happens in this module."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from intelhex import IntelHex

from .catalog import Profile, TOOL_EXECUTABLES, stc_protocol
from .options import OptionError, stc_hardware, flash_capacity, needs_serial, normalize_options


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Firmware:
    path: str
    size: int
    sha256: str
    format: str
    start: int
    end: int  # exclusive, relative for BIN, absolute for HEX


def inspect_firmware(path: str) -> Firmware:
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise ValidationError("请选择一个存在的固件文件。")
    fmt = file.suffix.lower()
    if fmt in (".ihx", ".ihex"):
        fmt = ".hex"
    if fmt not in (".bin", ".hex"):
        raise ValidationError("仅支持 BIN 和 Intel HEX（.hex / .ihx / .ihex）文件。")
    if file.stat().st_size > 64 * 1024**2:
        raise ValidationError("文件超过本版 64 MB 的检查上限。")
    data = file.read_bytes()
    if not data:
        raise ValidationError("固件是空文件，不能烧录。")
    if len(data) > 64 * 1024**2:
        raise ValidationError("文件超过本版 64 MB 的检查上限。")
    start, end = 0, len(data)
    if fmt == ".hex":
        try:
            records = [line.strip() for line in data.decode("ascii").splitlines() if line.strip()]
            if not records or records[-1].upper() != ":00000001FF":
                raise ValueError("缺少末尾 EOF 记录 :00000001FF")
            if any(line.upper() == ":00000001FF" for line in records[:-1]):
                raise ValueError("EOF 之后存在额外记录")
            image = IntelHex(str(file))
            if not image.addresses():
                raise ValueError("没有数据记录")
            start, end = image.minaddr(), image.maxaddr() + 1
        except Exception as exc:
            raise ValidationError(f"HEX 格式或校验和错误：{exc}") from exc
    return Firmware(str(file), len(data), hashlib.sha256(data).hexdigest(), fmt, start, end)


@dataclass(frozen=True)
class Request:
    profile: Profile
    firmware: Firmware
    port: str = ""
    baud: int = 115200
    address: int = 0
    timeout: int = 180
    options: dict = field(default_factory=dict)
    eeprom: Firmware | None = None


@dataclass(frozen=True)
class Plan:
    request: Request
    argv: tuple[str, ...]
    verification: str
    warnings: tuple[str, ...] = ()

    @property
    def display(self) -> str:
        return subprocess.list2cmdline(self.argv)

    def serializable(self) -> dict:
        return {"request": asdict(self.request), "argv": list(self.argv), "verification": self.verification,
                "warnings": list(self.warnings)}


def tool_command(key: str, overrides: dict[str, str]) -> list[str]:
    override = overrides.get(key, "").strip()
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise ValidationError(f"工具文件不存在：{path}")
        if path.suffix.lower() not in (".exe", ""):
            raise ValidationError("请选择工具的 EXE 文件，不要选择快捷方式或脚本。")
        return [str(path)]
    if key in ("esptool", "stcgal"):
        # Frozen app dispatches modules in the same exe, without opening a second GUI.
        if getattr(sys, "frozen", False):
            return [sys.executable, "--tool", key]
        return [sys.executable, "-m", key]
    name = TOOL_EXECUTABLES[key]
    found = shutil.which(name)
    if not found and key == "stm32cube":
        candidate = Path("C:/Program Files/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe")
        if candidate.is_file():
            found = str(candidate)
    if not found:
        raise ValidationError(f"未找到 {name}，请在「工具设置」中选择已安装的 EXE。")
    return [found]


def make_plan(request: Request, overrides: dict[str, str] | None = None, *, require_port: bool = True,
              resolve_tool: bool = True) -> Plan:
    p, fw = request.profile, request.firmware
    try:
        opts = normalize_options(p, request.options)
    except OptionError as exc:
        raise ValidationError(str(exc)) from exc
    request = replace(request, options=opts)
    capacity = flash_capacity(p, opts)
    warnings = []
    if fw.format not in p.formats:
        raise ValidationError(f"{p.name} 仅支持 {' / '.join(p.formats)}。")
    if request.baud not in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
        raise ValidationError("波特率不在支持列表中。")
    if not 5 <= request.timeout <= 3600:
        raise ValidationError("超时必须在 5–3600 秒之间。")
    if fw.format == ".bin":
        if request.address < p.base or request.address + fw.end > p.base + capacity:
            raise ValidationError("固件和起始地址超出所选芯片配置的 Flash 范围。")
        if p.tool in ("stcgal", "avrdude", "minipro") and request.address != 0:
            raise ValidationError("STC、AVR 和 MiniPro 的 BIN 文件必须从地址 0 写入。")
    elif fw.start < p.base or fw.end > p.base + capacity:
        raise ValidationError("HEX 中的地址超出所选芯片配置的 Flash 范围。")
    if p.tool == "stcgal" and fw.format == ".hex" and fw.start != 0:
        raise ValidationError("STC 的 HEX 代码必须从地址 0 开始，避免 stcgal 重定位数据。")
    if p.tool == "stcgal" and fw.format == ".hex" and Path(fw.path).suffix not in (".hex", ".ihx", ".ihex"):
        raise ValidationError("stcgal 区分扩展名大小写，请将 Intel HEX 扩展名改为小写 .hex / .ihx / .ihex。")
    if p.tool == "minipro" and fw.format == ".hex" and fw.start != 0:
        raise ValidationError("MiniPro 的 HEX 必须从地址 0 开始；本版不使用偏移重定位。")
    ee = request.eeprom
    if ee is not None:
        if not p.eeprom_capacity:
            raise ValidationError("所选芯片配置不支持单独的 EEPROM 文件。")
        if ee.start < 0 or ee.end > p.eeprom_capacity:
            raise ValidationError(f"EEPROM 数据超出容量 {p.eeprom_capacity} 字节。")
        if p.tool == "stcgal" and ee.start != 0:
            raise ValidationError("STC EEPROM 文件必须从地址 0 开始。")
        if p.tool == "stcgal" and ee.format == ".hex" and Path(ee.path).suffix not in (".hex", ".ihx", ".ihex"):
            raise ValidationError("stcgal EEPROM 的 Intel HEX 扩展名必须小写。")
        if p.tool == "avrdude" and opts["programmer"] in ("arduino", "wiring"):
            raise ValidationError("本版串口 Bootloader 不支持 EEPROM 文件，请使用 ISP 或清空 EEPROM。")
    if needs_serial(p, opts) and require_port:
        if not re.fullmatch(r"COM[1-9][0-9]*|/dev/[A-Za-z0-9_./-]+", request.port):
            raise ValidationError("请选择真实串口，例如 COM3；真实模式不接受网络串口。")
    cmd = tool_command(p.tool, overrides or {}) if resolve_tool else [
        TOOL_EXECUTABLES[p.tool] + ".exe" if p.tool in TOOL_EXECUTABLES else p.tool]
    file = fw.path
    if p.tool == "esptool":
        cmd += ["--chip", p.chip, "--port", request.port, "--baud", str(request.baud),
                "--before", opts["before"], "--after", opts["after"], "--connect-attempts", str(opts["connect_attempts"])]
        if opts["no_stub"]:
            cmd += ["--no-stub"]
        cmd += ["write-flash", "--flash-size", opts["flash_size"], "--flash-mode", opts["flash_mode"], "--flash-freq", opts["flash_freq"]]
        if opts["compression"] != "auto":
            cmd += ["--compress" if opts["compression"] == "yes" else "--no-compress"]
        if opts["erase_all"]:
            cmd += ["--erase-all"]
        cmd += [hex(request.address), file]
        verification = "esptool 写入后 MD5 校验"
    elif p.tool == "stm32cube":
        interface = opts["interface"]
        if interface in ("SWD", "JTAG"):
            cmd += ["-c", f"port={interface}", f"freq={opts['frequency']}", f"mode={opts['connect_mode']}", f"reset={opts['reset_mode']}"]
            cmd += [f"sn={opts['probe_serial']}"] if opts["probe_serial"] else [f"index={opts['probe_index']}"]
        elif interface == "UART":
            cmd += ["-c", f"port={request.port}", f"br={request.baud}", f"P={opts['parity']}"]
        else:
            cmd += ["-c", f"port=usb{opts['dfu_index']}"]
        if opts["erase_all"]:
            cmd += ["-e", "all"]
        cmd += ["-w", file]
        if fw.format == ".bin":
            cmd += [hex(request.address)]
        if opts["verify"]:
            cmd += ["-v"]
        if opts["reset_after"] and interface in ("SWD", "JTAG"):
            cmd += ["-rst"]
        verification = "STM32CubeProgrammer 读回校验 (-v)" if opts["verify"] else "用户关闭了读回校验"
    elif p.tool == "avrdude":
        fmt = "i" if fw.format == ".hex" else "r"
        cmd += ["-p", p.chip, "-c", opts["programmer"]]
        if opts["programmer"] in ("arduino", "wiring", "avrisp"):
            cmd += ["-P", request.port, "-b", str(request.baud)]
        elif opts["bitclock"] != "auto":
            cmd += ["-B", opts["bitclock"]]
        if opts["erase_policy"] == "noerase" or opts["programmer"] in ("arduino", "wiring"):
            cmd += ["-D"]
        if not opts["verify"]:
            cmd += ["-V"]
        if opts["verbose"]:
            cmd += ["-v"]
        cmd += ["-U", f"flash:w:{file}:{fmt}"]
        if ee:
            cmd += ["-U", f"eeprom:w:{ee.path}:{'i' if ee.format == '.hex' else 'r'}"]
        for key in ("lfuse", "hfuse", "efuse"):
            if opts.get(key):
                cmd += ["-U", f"{key}:w:{opts[key]}:m"]
                warnings.append(f"将写入 {key}={opts[key]}，错误熔丝可能使 ISP / 时钟不可用。")
        verification = "AVRDUDE 默认写入后读回校验" if opts["verify"] else "用户关闭了读回校验 (-V)"
    elif p.tool == "stcgal":
        cmd += ["-P", stc_protocol(p), "-p", request.port, "-b", str(request.baud), "-l", str(opts["handshake_baud"])]
        if opts.get("trim_frequency"):
            cmd += ["-t", str(opts["trim_frequency"])]
            warnings.append(f"将校准内部 RC 至 {opts['trim_frequency']} kHz，请核对目标频率与芯片规格。")
        if opts["autoreset"]:
            cmd += ["-a", "-A", opts["resetpin"]]
        if opts["debug"]:
            cmd += ["-D"]
        for setting in stc_hardware(p):
            if opts[setting.key] != "keep":
                cmd += ["-o", f"{setting.key}={opts[setting.key]}"]
                warnings.append(f"STC 硬件设置：{setting.label} = {opts[setting.key]}。")
        cmd += [file]
        if ee:
            cmd += [ee.path]
        verification = "stcgal 协议传输检查；本版未提供独立 Flash 读回校验"
    elif p.tool == "openocd":
        if fw.format == ".hex" and Path(file).suffix.lower() != ".hex":
            raise ValidationError("OpenOCD 按扩展名识别镜像，请将 Intel HEX 文件扩展名改为 .hex 后重试。")
        # OpenOCD program evaluates a nested Tcl list. Limit paths before bracing.
        tcl_path = Path(file).as_posix()
        if any(c in tcl_path for c in '{}[]$;\r\n"'):
            raise ValidationError("OpenOCD 固件路径不能含 Tcl 特殊字符（花括号、方括号、$、分号或引号）；请移动文件后重试。")
        cmd += ["-f", f"interface/{opts['adapter']}.cfg", "-c",
                "transport select " + ("hla_swd" if opts["adapter"] == "stlink" else "swd"),
                "-f", p.target_config, "-c", f"adapter speed {opts['frequency']}"]
        if opts["probe_serial"]:
            cmd += ["-c", f"adapter serial {opts['probe_serial']}"]
        for service in ("gdb", "tcl", "telnet"):
            cmd += ["-c", f"{service}_port disabled"]
        program = f"program {{{tcl_path}}}"
        if opts["verify"]:
            program += " verify"
        if opts["reset_after"]:
            program += " reset"
        program += " exit"
        if fw.format == ".bin":
            program += f" {hex(request.address)}"
        cmd += ["-c", program]
        warnings.append("OpenOCD 擦除固件涉及的整个 Flash 扇区，同扇区其他数据可能被清除。")
        verification = "OpenOCD verify_image 读回校验" if opts["verify"] else "用户关闭了读回校验"
    elif p.tool == "stm32flash":
        start = fw.start if fw.format == ".hex" else request.address
        length = fw.end - fw.start if fw.format == ".hex" else fw.end
        if start % 4:
            raise ValidationError("stm32flash 写入起始地址必须按 4 字节对齐。")
        cmd += ["-b", str(request.baud), "-m", opts["serial_mode"], "-n", str(opts["retries"])]
        # -e 0 must precede -S: upstream rejects -e after an address range.
        if opts["erase_policy"] == "none":
            cmd += ["-e", "0"]
            warnings.append("不擦除模式要求目标区域已可写，否则写入或校验可能失败。")
        cmd += ["-S", f"{hex(start)}:{length}", "-w", file]
        if fw.format == ".bin":
            cmd += ["-f"]
        if opts["verify"]:
            cmd += ["-v"]
        if opts["run_after"]:
            cmd += ["-g", "0"]
            warnings.append("完成后从 Flash 基址启动；偏移应用需有效引导程序。")
        cmd += [request.port]
        warnings.append("stm32flash 按地址范围涉及的整页 / 扇区擦除；范围内 HEX 空洞由后端填充，同页其他数据不保留。")
        verification = "stm32flash -v 读回校验" if opts["verify"] else "用户关闭了读回校验"
    elif p.tool == "minipro":
        if not opts["allow_short"] and fw.end != p.capacity:
            raise ValidationError("关闭短固件支持时，镜像必须覆盖至芯片容量末尾。")
        cmd += ["-p", opts["device_name"], "-w", file]
        if opts["allow_short"]:
            cmd += ["-s"]
        if not opts["verify"]:
            cmd += ["-v"]  # MiniPro -v disables verification, unlike stm32flash.
        warnings.append("MiniPro 编程可能擦除整颗芯片；请先核对设备数据库、封装和芯片座方向。")
        verification = "MiniPro 默认写后校验" if opts["verify"] else "用户关闭了读回校验 (-v)"
    else:
        raise ValidationError("未声明的烧录工具。")
    if opts.get("erase_all"):
        warnings.append("将先执行全片擦除，清除其他分区和数据。")
    if opts.get("verify") is False:
        warnings.append("读回校验已关闭，工具退出成功不能证明写入数据一致。")
    if ee:
        warnings.append(f"将额外写入 EEPROM 文件：{ee.path}。")
    return Plan(request, tuple(cmd), verification, tuple(warnings))


def check_unchanged(firmware: Firmware) -> None:
    current = inspect_firmware(firmware.path)
    if current != firmware:
        raise ValidationError("固件在预览后发生变化，请重新选择并检查。")
