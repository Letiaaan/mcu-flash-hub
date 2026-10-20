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
BY_ID = {p.id: p for p in PROFILES}
TOOL_LABELS = {"esptool": "esptool 5.1", "stm32cube": "STM32CubeProgrammer", "avrdude": "AVRDUDE", "stcgal": "stcgal 1.10"}
TOOL_URLS = {
    "esptool": "https://docs.espressif.com/projects/esptool/en/latest/esp32/",
    "stm32cube": "https://www.st.com/en/development-tools/stm32cubeprog.html",
    "avrdude": "https://github.com/avrdudes/avrdude/releases",
    "stcgal": "https://github.com/grigorig/stcgal",
}
