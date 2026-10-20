"""Typed backend capabilities. UI, imports and CLI planning share this schema."""
from dataclasses import dataclass
import re

from .catalog import Profile, stc_protocol


class OptionError(ValueError):
    pass


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    default: object
    kind: str = "choice"
    choices: tuple = ()  # (stored value, Chinese label)
    help: str = ""
    minimum: int = 0
    maximum: int = 100000
    when: tuple | None = None

    def active(self, values):
        return self.when is None or values[self.when[0]] in self.when[1]


def choices(*values):
    return tuple((v, str(v)) for v in values)


UNCHANGED = (("keep", "保持芯片原值"), ("true", "启用"), ("false", "禁用"))
STC_HARDWARE = (
    Option("cpu_6t_enabled", "CPU 6T 模式", "keep", choices=UNCHANGED, help="启用为 6T，禁用为 12T；会改变程序时序。"),
    Option("bsl_pindetect_enabled", "下载时检测 P1.0 / P1.1", "keep", choices=UNCHANGED, help="启用后下载受引脚条件约束，具体电平条件请核对芯片手册。"),
    Option("eeprom_erase_enabled", "下载时擦除用户 EEPROM", "keep", choices=UNCHANGED),
    Option("clock_gain", "振荡器增益", "keep", choices=(("keep", "保持芯片原值"), ("low", "低增益"), ("high", "高增益"))),
    Option("ale_enabled", "ALE 输出", "keep", choices=UNCHANGED, help="启用 ALE 功能，禁用时对应引脚作为普通 I/O，具体以芯片手册为准。"),
    Option("xram_enabled", "内部扩展 RAM", "keep", choices=UNCHANGED),
    Option("watchdog_por_enabled", "上电自动启动看门狗", "keep", choices=UNCHANGED, help="这是上电启用控制，不是「仅断电才能停止」选项。"),
)


def stc_hardware(profile):
    protocol = stc_protocol(profile)
    if protocol == "stc89":
        return STC_HARDWARE
    # Conservative subset verified against the installed upstream option setters.
    specs = [Option("reset_pin_enabled", "复位引脚功能", "keep", choices=UNCHANGED)]
    if protocol in ("stc12", "stc15"):
        specs += [Option("clock_source", "时钟来源", "keep", choices=(("keep", "保持芯片原值"), ("internal", "内部时钟"), ("external", "外部时钟")), help="外部时钟需有实际电路；错误选择可能导致程序无法运行。")]
    if protocol != "stc15a":
        specs += [Option("clock_gain", "振荡器增益", "keep", choices=(("keep", "保持芯片原值"), ("low", "低增益"), ("high", "高增益")))]
    specs += [
        Option("watchdog_por_enabled", "上电启动看门狗", "keep", choices=UNCHANGED),
        Option("watchdog_stop_idle", "空闲时停止看门狗", "keep", choices=UNCHANGED),
        Option("watchdog_prescale", "看门狗分频", "keep", choices=(("keep", "保持芯片原值"),) + choices("2", "4", "8", "16", "32", "64", "128", "256")),
        Option("low_voltage_reset", "低压复位", "keep", choices=UNCHANGED),
        Option("eeprom_erase_enabled", "下载时擦除用户 EEPROM", "keep", choices=UNCHANGED),
        Option("bsl_pindetect_enabled", "下载引脚条件检测", "keep", choices=UNCHANGED),
    ]
    return tuple(specs)


def stc_option_registers(profile):
    """Construct an upstream register model for offline checks, never a hardware read."""
    from stcgal.options import Stc89Option, Stc12Option, Stc15AOption, Stc15Option, Stc8Option
    protocol = stc_protocol(profile)
    if protocol == "stc89":
        return Stc89Option(0xFF)
    cls, length = {"stc12": (Stc12Option, 4), "stc15a": (Stc15AOption, 13),
                   "stc15": (Stc15Option, 5), "stc8": (Stc8Option, 5), "stc8g": (Stc8Option, 5)}[protocol]
    return cls(bytes([0xFF] * length))


def option_groups(profile: Profile):
    """Visible sections and their reset boundaries, including inactive child fields."""
    groups = {
        "esptool": (
            ("flash", "Flash 参数", ("flash_size", "flash_mode", "flash_freq")),
            ("connection", "连接与复位", ("before", "after", "connect_attempts")),
            ("write", "写入行为", ("no_stub", "compression", "erase_all")),
        ),
        "stm32cube": (
            ("connection", "连接与调试", ("interface", "frequency", "connect_mode", "reset_mode", "probe_serial", "probe_index", "parity", "dfu_index")),
            ("write", "写入与校验", ("verify", "reset_after", "erase_all")),
        ),
        "avrdude": (
            ("connection", "烧录器与时钟", ("programmer", "bitclock")),
            ("write", "写入与日志", ("erase_policy", "verify", "verbose")),
            ("fuses", "熔丝字节", ("lfuse", "hfuse", "efuse")),
        ),
        "stcgal": (
            ("connection", "握手与电源复位", ("handshake_baud", "autoreset", "resetpin", "debug", "trim_frequency")),
            ("hardware", "芯片硬件选项", tuple(s.key for s in stc_hardware(profile))),
        ),
        "openocd": (
            ("connection", "调试探针", ("adapter", "frequency", "probe_serial")),
            ("write", "写入与校验", ("verify", "reset_after")),
        ),
        "stm32flash": (
            ("connection", "串口握手", ("serial_mode", "retries")),
            ("write", "擦除与校验", ("erase_policy", "verify", "run_after")),
        ),
        "minipro": (
            ("device", "芯片封装", ("device_name",)),
            ("write", "写入与校验", ("verify", "allow_short")),
        ),
    }
    supported = {s.key for s in schema(profile)}
    return tuple((key, title, tuple(name for name in keys if name in supported))
                 for key, title, keys in groups[profile.tool] if any(name in supported for name in keys))


def schema(profile: Profile) -> tuple[Option, ...]:
    if profile.tool == "esptool":
        sizes = ("1MB", "2MB", "4MB", "8MB", "16MB") + (("32MB",) if profile.id == "esp32s3" else ())
        frequencies = ("keep", "80m", "40m", "26m", "20m") if profile.id == "esp32" else ("keep", "80m", "40m", "20m")
        return (
            Option("flash_size", "Flash 容量", f"{profile.capacity // 1024**2}MB", choices=choices(*sizes), help="按实际模块选择；用于地址范围检查和 esptool 参数，不会自动识别容量。"),
            Option("flash_mode", "Flash 访问模式", "keep", choices=choices("keep", "qio", "qout", "dio", "dout"), help="keep 保留镜像头；其余值修改适用镜像的 Flash 参数。"),
            Option("flash_freq", "Flash 频率", "keep", choices=choices(*frequencies)),
            Option("before", "连接前复位", "default-reset", choices=(("default-reset", "自动复位进入下载"), ("no-reset", "不复位，直接握手")) + ((("usb-reset", "USB 复位"),) if profile.id != "esp8266" else ())),
            Option("after", "完成后复位", "hard-reset", choices=(("hard-reset", "硬件复位运行"), ("soft-reset", "软件复位"), ("no-reset", "保持下载状态"))),
            Option("no_stub", "仅使用 ROM 下载器", False, "bool", help="不上传 RAM stub；速度及部分功能受限。"),
            Option("compression", "传输压缩", "auto", choices=(("auto", "跟随后端默认"), ("yes", "压缩"), ("no", "不压缩"))),
            Option("connect_attempts", "连接重试次数", 7, "int", minimum=1, maximum=30),
            Option("erase_all", "写入前全片擦除", False, "bool", help="会清除整个 Flash，包括其他分区数据。"),
        )
    if profile.tool == "stm32cube":
        debug = ("interface", ("SWD", "JTAG"))
        interfaces = (("SWD", "ST-LINK / SWD"), ("JTAG", "ST-LINK / JTAG"), ("UART", "串口 Bootloader"))
        if profile.id == "stm32f401cc":
            interfaces += (("DFU", "USB DFU"),)
        return (
            Option("interface", "连接接口", "SWD", choices=interfaces),
            Option("frequency", "调试频率 (kHz)", 4000, "int", minimum=5, maximum=24000, when=debug, help="实际频率由 ST-LINK 支持的档位决定。"),
            Option("connect_mode", "连接模式", "NORMAL", choices=(("NORMAL", "普通连接"), ("UR", "复位下连接（需 NRST）"), ("HOTPLUG", "热连接")), when=debug),
            Option("reset_mode", "连接复位方式", "SWrst", choices=(("SWrst", "系统软件复位"), ("HWrst", "NRST 硬件复位"), ("Crst", "内核复位")), when=debug, help="复位下连接必须选择 HWrst。"),
            Option("probe_serial", "ST-LINK 序列号", "", "text", when=debug, help="留空使用探针索引；填入时不再传索引。"),
            Option("probe_index", "ST-LINK 索引", 0, "int", minimum=0, maximum=255, when=debug),
            Option("parity", "UART 校验位", "EVEN", choices=choices("EVEN", "NONE", "ODD"), when=("interface", ("UART",))),
            Option("dfu_index", "DFU 设备编号", 1, "int", minimum=1, maximum=16, when=("interface", ("DFU",))),
            Option("verify", "写入后读回校验", True, "bool"),
            Option("reset_after", "写入后复位运行", True, "bool", when=debug, help="本版仅在 ST-LINK 接口下提供 -rst。"),
            Option("erase_all", "写入前全片擦除", False, "bool", help="会清除整个芯片的 Flash。"),
        )
    if profile.tool == "avrdude":
        boot = "arduino" if profile.id == "atmega328p" else "wiring"
        is51 = profile.chip in ("89S51", "89S52")
        programmers = (("usbasp", "USBasp / ISP"), ("usbtiny", "USBtinyISP"), ("avrisp2", "AVRISP mkII"))
        if is51:
            programmers = (("usbasp", "兼容 8051 固件的 USBasp"), ("avrisp", "串口 AVRISP（上游已列出）"))
        elif profile.id in ("atmega328p", "atmega2560"):
            programmers += ((boot, "Arduino 串口 Bootloader"),)
        isp = ("programmer", ("usbasp", "usbtiny", "avrisp2"))
        specs = (
            Option("programmer", "烧录器 / 协议", "usbasp", choices=programmers),
            Option("bitclock", "ISP 位时钟周期", "32" if is51 else "auto", choices=(("auto", "后端默认"),) + tuple((str(i), f"{i} μs") for i in (1, 2, 4, 8, 16, 32, 64)), when=isp),
            Option("erase_policy", "自动擦除策略", "auto", choices=(("auto", "按后端默认擦除"), ("noerase", "禁止自动擦除 (-D)")), help="串口 Bootloader 固定使用 -D；ISP 禁用擦除时需确保目标区域可写。"),
            Option("verify", "写入后读回校验", True, "bool"),
            Option("verbose", "详细工具日志", False, "bool"),
            Option("lfuse", "低熔丝字节", "", "hexbyte", when=isp, help="留空保持；0x00–0xFF。错误配置可能使 ISP 或时钟不可用。"),
            Option("hfuse", "高熔丝字节", "", "hexbyte", when=isp, help="留空保持；改变熔丝前请核对芯片手册。"),
            Option("efuse", "扩展熔丝字节", "", "hexbyte", when=isp, help="留空保持；保留位也需按芯片手册设置。"),
        )
        if is51:
            return tuple(s for s in specs if s.kind != "hexbyte")
        if profile.id in ("atmega8", "atmega16", "atmega32"):
            return tuple(s for s in specs if s.key != "efuse")
        return specs
    if profile.tool == "openocd":
        return (
            Option("adapter", "调试探针", "stlink", choices=(("stlink", "ST-LINK (HLA)"), ("cmsis-dap", "CMSIS-DAP"))),
            Option("frequency", "SWD 频率 (kHz)", 1000, "int", minimum=5, maximum=8000),
            Option("probe_serial", "探针序列号", "", "text"),
            Option("verify", "写入后读回校验", True, "bool"),
            Option("reset_after", "完成后复位运行", True, "bool"),
        )
    if profile.tool == "stm32flash":
        return (
            Option("serial_mode", "串口格式", "8e1", choices=choices("8e1", "8n1"), help="标准 STM32 Bootloader 通常为 8e1，需按目标确认。"),
            Option("retries", "失败写入重试次数", 10, "int", minimum=1, maximum=30),
            Option("erase_policy", "擦除范围", "image", choices=(("image", "按固件涉及页 / 扇区擦除"), ("none", "不擦除 (-e 0)"))),
            Option("verify", "写入后读回校验", True, "bool"),
            Option("run_after", "写入后启动程序", True, "bool"),
        )
    if profile.tool == "minipro":
        return (
            Option("device_name", "设备数据库名称", profile.chip + "@DIP40", choices=choices(profile.chip + "@DIP40", profile.chip + "@PLCC44", profile.chip + "@TQFP44"), help="先在所装 minipro 的 -l / -d 输出中确认精确设备与封装，名称随数据库版本变化。"),
            Option("verify", "写入后校验", True, "bool"),
            Option("allow_short", "允许小于芯片容量的固件", True, "bool", help="启用 -s；应用仍拒绝任何超出芯片地址范围的数据。"),
        )
    if profile.tool != "stcgal":
        raise OptionError("未声明的烧录工具。")
    connection = (
        Option("handshake_baud", "冷启动握手波特率", 2400, "int", minimum=1200, maximum=115200),
        Option("autoreset", "自动控制电源复位", False, "bool", help="需外部电源控制电路，串口 DTR / RTS 不是芯片供电输出。"),
        Option("resetpin", "电源控制引脚", "dtr", choices=choices("dtr", "rts"), when=("autoreset", (True,))),
        Option("debug", "详细协议日志", False, "bool"),
    )
    if stc_protocol(profile) != "stc89" and stc_protocol(profile) != "stc12":
        connection += (Option("trim_frequency", "内部 RC 校准频率 (kHz)", 0, "int", minimum=0, maximum=40000, help="0 表示不指定；仅在确有需要时改变内部 RC 校准频率。"),)
    return connection + stc_hardware(profile)


def normalize_options(profile: Profile, raw: dict | None) -> dict:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise OptionError("芯片配置必须是一个对象。")
    specs = schema(profile)
    unknown = set(raw) - {s.key for s in specs}
    if unknown:
        raise OptionError("所选芯片不支持这些配置：" + ", ".join(sorted(map(str, unknown))))
    result = {}
    for spec in specs:
        value = raw.get(spec.key, spec.default)
        if spec.kind == "choice":
            if type(value) is not str or value not in {v for v, _ in spec.choices}:
                raise OptionError(f"{spec.label} 的值无效。")
        elif spec.kind == "bool":
            if type(value) is not bool:
                raise OptionError(f"{spec.label} 必须为布尔值。")
        elif spec.kind == "int":
            if type(value) is not int or not spec.minimum <= value <= spec.maximum:
                raise OptionError(f"{spec.label} 必须在 {spec.minimum}–{spec.maximum} 之间。")
        elif spec.kind == "hexbyte":
            if type(value) is not str or (value and not re.fullmatch(r"0[xX][0-9A-Fa-f]{1,2}", value)):
                raise OptionError(f"{spec.label} 应留空或填写 0x00–0xFF。")
            value = f"0x{int(value, 16):02X}" if value else ""
        elif type(value) is not str or (value and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value)):
            raise OptionError(f"{spec.label} 只接受字母、数字、下划线和短横线。")
        result[spec.key] = value
    if profile.tool == "stm32cube" and result["interface"] in ("SWD", "JTAG"):
        if result["connect_mode"] == "UR" and result["reset_mode"] != "HWrst":
            raise OptionError("复位下连接 (UR) 需要将连接复位方式设为 HWrst。")
    if profile.tool == "avrdude" and result["programmer"] in ("arduino", "wiring"):
        if any(result.get(k) for k in ("lfuse", "hfuse", "efuse")):
            raise OptionError("串口 Bootloader 不支持熔丝写入，请清空熔丝配置或选择 ISP 烧录器。")
    return result


def needs_serial(profile: Profile, values: dict) -> bool:
    return (profile.tool in ("esptool", "stcgal", "stm32flash") or
            (profile.tool == "stm32cube" and values["interface"] == "UART") or
            (profile.tool == "avrdude" and values["programmer"] in ("arduino", "wiring", "avrisp")))


def flash_capacity(profile: Profile, values: dict) -> int:
    return int(values["flash_size"][:-2]) * 1024**2 if profile.tool == "esptool" else profile.capacity


def capability_note(profile: Profile) -> str:
    if profile.tool == "stcgal":
        if stc_protocol(profile) != "stc89":
            return "此型号使用 " + stc_protocol(profile) + " 协议，提供已核对的常用硬件选项，默认保持原值；未开放动态分区、保护位等设置。EEPROM 从地址 0 开始，烧录前需人工核对日志中的实际型号。"
        return "STC89 的 7 项硬件配置均可设置，默认保持原值。官方工具中的掉电才能停看门狗、添加 ID 等功能，stcgal 1.10 未提供对应选项。本版 EEPROM 文件必须从地址 0 开始。"
    if profile.tool == "stm32cube":
        dfu = "F401CC 可选 USB DFU。" if profile.id == "stm32f401cc" else "F103C8 的系统 Bootloader 不支持 USB DFU，因此不提供该选项。"
        return "支持 SWD / JTAG / UART 写入参数。" + dfu + "UART / DFU 需按芯片手册进入系统 Bootloader。读保护、Option Bytes、OTP 尚未接入。"
    if profile.tool == "avrdude":
        if profile.chip in ("89S51", "89S52"):
            return "AT89S51/S52 是 8051，不是 AVR：不提供低 / 高 / 扩展熔丝与 Arduino Bootloader。需 AVRDUDE 8.1+、正确晶振及支持正极性 RST 的编程器；普通 USBasp 固件不保证可用。"
        boot = "支持 ISP 和对应 Arduino Bootloader；" if profile.id in ("atmega328p", "atmega2560") else "仅接入 ISP；"
        return boot + "EEPROM 与熔丝写入限 ISP。锁定位与高压恢复尚未接入。默认保留熔丝，写入 EEPROM 前请核对 EESAVE。"
    if profile.tool == "openocd":
        return "需自行安装 OpenOCD 0.12.x，保留完整 scripts 目录。仅使用预设目标与探针配置，默认校验和复位，不开放任意 Tcl、解锁或保护位。"
    if profile.tool == "stm32flash":
        return "使用串口系统 Bootloader，需手动设置 BOOT0 和复位。本版仅接入 BIN，避免上游 HEX 解析器的重定位差异。默认擦除固件涉及的整页 / 扇区，不保留同页其他数据；不自动解锁保护位。"
    if profile.tool == "minipro":
        return "AT89C51/C52 需要并行编程器及对应芯片座，不支持 STC 串口下载。设备名称需按本机 minipro 数据库确认；默认保留芯片 ID 检查与写后校验，不设置电压或锁定位。"
    return "按实际模块选择 Flash 容量。keep 保留镜像头配置；本版一次写一个文件，不修改 eFuse、分区布局或加密配置。"
