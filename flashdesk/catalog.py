from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    id: str
    family: str
    name: str
    tool: str
    chip: str
    capacity: int
    base: int
    address: int
    formats: tuple[str, ...]
    connection: str
    note: str
    eeprom_capacity: int = 0
    protocol: str = ""
    target_config: str = ""


PROFILES = (
    Profile("esp32", "Espressif", "ESP32", "esptool", "esp32", 4 * 1024**2, 0, 0x10000,
            (".bin",), "UART / USB 串口", "单文件应用镜像默认 0x10000，合并镜像按构建产物填写偏移；Flash 容量在芯片配置中选择。"),
    Profile("esp32c3", "Espressif", "ESP32-C3", "esptool", "esp32c3", 4 * 1024**2, 0, 0x10000,
            (".bin",), "UART / USB 串口", "请按工程烧录清单选择文件和地址，并在芯片配置中选择实际 Flash 容量。"),
    Profile("esp32s3", "Espressif", "ESP32-S3", "esptool", "esp32s3", 8 * 1024**2, 0, 0x10000,
            (".bin",), "UART / USB 串口", "一次写一个文件，完整工程请先生成合并镜像；Flash 容量在芯片配置中选择。"),
    Profile("stm32f103c8", "STMicroelectronics", "STM32F103C8", "stm32cube", "STM32F103C8", 64 * 1024,
            0x08000000, 0x08000000, (".bin", ".hex"), "ST-LINK / UART", "使用 STM32CubeProgrammer CLI；HEX 内嵌地址，BIN 默认 0x08000000。"),
    Profile("stm32f401cc", "STMicroelectronics", "STM32F401CC", "stm32cube", "STM32F401CC", 256 * 1024,
            0x08000000, 0x08000000, (".bin", ".hex"), "ST-LINK / UART / DFU", "在芯片配置中选择接口；ST-LINK 默认使用 SWD，请按实际连接选择参数。"),
    Profile("atmega328p", "Microchip AVR", "ATmega328P", "avrdude", "m328p", 32 * 1024, 0, 0,
            (".hex", ".bin"), "ISP / 串口 Bootloader", "默认 USBasp；可在芯片配置中选择烧录器，熔丝默认保持。", 1024),
    Profile("atmega2560", "Microchip AVR", "ATmega2560", "avrdude", "m2560", 256 * 1024, 0, 0,
            (".hex", ".bin"), "ISP / 串口 Bootloader", "默认 USBasp；Arduino Mega 使用 wiring 协议，目标板需正确供电。", 4096),
    Profile("stc89c52rc", "STC", "STC89C52RC", "stcgal", "STC89C52RC", 8 * 1024, 0, 0,
            (".hex", ".bin"), "UART / 冷启动", "串口连接后开始烧录，再给芯片上电；芯片型号由 stcgal 握手识别，人工核对日志中的型号。", 6144),
)

# Additional profiles are appended to preserve existing saved IDs and initial ordering.
PROFILES += (
    Profile("stc89c51rc", "51 / STC", "STC89C51RC", "stcgal", "STC89C51RC/LE51RC", 4096, 0, 0, (".bin", ".hex"), "UART / 冷启动", "经典 51 教学芯片；冷启动下载，默认保持硬件选项。", 10240, "stc89"),
    Profile("stc89c54rd", "51 / STC", "STC89C54RD+", "stcgal", "STC89C54RD+/LE54RD+", 16384, 0, 0, (".bin", ".hex"), "UART / 冷启动", "RD+ 与 RC 容量不同；按完整料号选择。", 47104, "stc89"),
    Profile("stc90c52rc", "51 / STC", "STC90C52RC", "stcgal", "STC90C52RC", 8192, 0, 0, (".bin", ".hex"), "UART / 冷启动", "STC90 串口下载；不可按 AT89C52 的并行编程方式连接。", 6144, "stc89"),
    Profile("stc12c5a60s2", "51 / STC", "STC12C5A60S2", "stcgal", "STC12C5A60S2", 61440, 0, 0, (".bin", ".hex"), "UART / 冷启动", "STC12 协议，配置项与 STC89 不同。", 2048, "stc12"),
    Profile("stc15f104e", "51 / STC", "STC15F104E", "stcgal", "STC15F104E", 4096, 0, 0, (".bin", ".hex"), "UART / 冷启动", "使用 stc15a 协议；不要选择 STC89 的 6T / XRAM 配置。", 1024, "stc15a"),
    Profile("stc15f2k60s2", "51 / STC", "STC15F2K60S2", "stcgal", "STC15F2K60S2", 61440, 0, 0, (".bin", ".hex"), "UART / 冷启动", "内置 RC 校准默认保持，不自动改时钟来源。", 1024, "stc15"),
    Profile("stc15w4k32s4", "51 / STC", "STC15W4K32S4", "stcgal", "STC15W4K32S4", 32768, 0, 0, (".bin", ".hex"), "UART / 冷启动", "固定使用本配置的代码 / EEPROM 分区，不开放动态重分区。", 27648, "stc15"),
    Profile("stc8a8k64s4a12", "51 / STC", "STC8A8K64S4A12", "stcgal", "STC8A8K64S4A12", 65024, 0, 0, (".bin", ".hex"), "UART / 冷启动", "上游可用代码区为 65024 字节，不能直接按 65536 字节写入。", 512, "stc8"),
    Profile("stc8g1k08", "51 / STC", "STC8G1K08 · 8PIN", "stcgal", "STC8G1K08-8PIN", 8192, 0, 0, (".bin", ".hex"), "UART / 冷启动", "STC8G 协议仍以上游实验性实现为准，需实物验证。", 4096, "stc8g"),
    Profile("at89s51", "51 / Atmel", "AT89S51 · ISP", "avrdude", "89S51", 4096, 0, 0, (".bin", ".hex"), "SPI ISP / 专用兼容编程器", "需 AVRDUDE 8.1+ 与支持 8051 正极性 RST 的编程器；普通 USBasp 固件不一定可用。"),
    Profile("at89s52", "51 / Atmel", "AT89S52 · ISP", "avrdude", "89S52", 8192, 0, 0, (".bin", ".hex"), "SPI ISP / 专用兼容编程器", "不是 USB-TTL 串口下载；需正确晶振、供电和 RST 极性，不提供 AVR 熔丝。"),
    Profile("at89c51", "51 / Atmel", "AT89C51 · 并行编程", "minipro", "AT89C51", 4096, 0, 0, (".bin", ".hex"), "TL866 / 芯片座", "需另装开源 minipro CLI 与兼容编程器；按 -l 列表确认精确封装名称，不是 STC 串口下载。"),
    Profile("at89c52", "51 / Atmel", "AT89C52 · 并行编程", "minipro", "AT89C52", 8192, 0, 0, (".bin", ".hex"), "TL866 / 芯片座", "需与芯片封装匹配的转接座；不得混淆 AT89S52、STC89C52。"),
    Profile("atmega8", "Microchip AVR", "ATmega8", "avrdude", "m8", 8192, 0, 0, (".bin", ".hex"), "ISP", "传统 AVR 教学芯片；仅低 / 高熔丝，无扩展熔丝。", 512),
    Profile("atmega16", "Microchip AVR", "ATmega16", "avrdude", "m16", 16384, 0, 0, (".bin", ".hex"), "ISP", "ISP 写入；不预设串口 Bootloader，无扩展熔丝。", 512),
    Profile("atmega32", "Microchip AVR", "ATmega32", "avrdude", "m32", 32768, 0, 0, (".bin", ".hex"), "ISP", "ISP 写入；不预设串口 Bootloader，无扩展熔丝。", 1024),
    Profile("attiny85", "Microchip AVR", "ATtiny85", "avrdude", "t85", 8192, 0, 0, (".bin", ".hex"), "ISP", "默认 USBasp ISP，不包含 Digispark USB Bootloader。", 512),
    Profile("esp8266", "Espressif", "ESP8266 / ESP-12", "esptool", "esp8266", 4 * 1024**2, 0, 0, (".bin",), "UART / 下载模式", "默认从 0 写入，实际偏移和 Flash 容量须按工程及模块选择。"),
    Profile("esp32c6", "Espressif", "ESP32-C6", "esptool", "esp32c6", 4 * 1024**2, 0, 0x10000, (".bin",), "UART / USB 串口", "单文件写入；不开放 eFuse / 加密配置。"),
    Profile("stm32f103c8-openocd", "STMicroelectronics", "STM32F103C8 · OpenOCD", "openocd", "STM32F103C8", 65536, 0x08000000, 0x08000000, (".bin", ".hex"), "SWD / 调试探针", "需 OpenOCD 0.12.x 及完整 scripts 目录；ST-LINK 或 CMSIS-DAP。", target_config="target/stm32f1x.cfg"),
    Profile("stm32f401cc-openocd", "STMicroelectronics", "STM32F401CC · OpenOCD", "openocd", "STM32F401CC", 262144, 0x08000000, 0x08000000, (".bin", ".hex"), "SWD / 调试探针", "OpenOCD 命令仅开放声明的参数，不导入任意 Tcl 脚本。", target_config="target/stm32f4x.cfg"),
    Profile("stm32f407vg-openocd", "STMicroelectronics", "STM32F407VG · OpenOCD", "openocd", "STM32F407VG", 1048576, 0x08000000, 0x08000000, (".bin", ".hex"), "SWD / 调试探针", "按 1 MB Flash 检查；不修改读保护与 Option Bytes。", target_config="target/stm32f4x.cfg"),
    Profile("stm32f103c8-uart", "STMicroelectronics", "STM32F103C8 · stm32flash", "stm32flash", "STM32F103C8", 65536, 0x08000000, 0x08000000, (".bin",), "UART / 系统 Bootloader", "需 USB-TTL 并手动设置 BOOT0 / 复位；本版仅接入 BIN，默认按固件涉及页擦除。"),
    Profile("stm32f401cc-uart", "STMicroelectronics", "STM32F401CC · stm32flash", "stm32flash", "STM32F401CC", 262144, 0x08000000, 0x08000000, (".bin",), "UART / 系统 Bootloader", "本版仅接入 BIN；需支持该目标的 stm32flash 版本，不要将 USB 直连当作 UART。"),
)
BY_ID = {p.id: p for p in PROFILES}
TOOL_LABELS = {"esptool": "esptool 5.1", "stm32cube": "STM32CubeProgrammer", "avrdude": "AVRDUDE", "stcgal": "stcgal 1.10",
               "openocd": "OpenOCD 0.12.x", "stm32flash": "stm32flash", "minipro": "MiniPro CLI"}
TOOL_EXECUTABLES = {"stm32cube": "STM32_Programmer_CLI", "avrdude": "avrdude", "openocd": "openocd", "stm32flash": "stm32flash", "minipro": "minipro"}
TOOL_URLS = {
    "esptool": "https://docs.espressif.com/projects/esptool/en/latest/esp32/",
    "stm32cube": "https://www.st.com/en/development-tools/stm32cubeprog.html",
    "avrdude": "https://github.com/avrdudes/avrdude/releases",
    "stcgal": "https://github.com/grigorig/stcgal",
    "openocd": "https://openocd.org/",
    "stm32flash": "https://sourceforge.net/projects/stm32flash/",
    "minipro": "https://gitlab.com/DavidGriffith/minipro/",
}


def is_8051(profile):
    return profile.tool in ("stcgal", "minipro") or profile.chip in ("89S51", "89S52")


def stc_protocol(profile):
    return profile.protocol or "stc89"
