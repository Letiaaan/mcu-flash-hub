# 烧录配置清单

目录包含 32 个芯片与工具组合，涉及 28 个不同目标料号、7 类工具；其中 14 个为 51 / 8051 配置。配置数包含同一 STM32 使用不同工具的条目，不代表同等数量的独立芯片。

**全部条目均未实物验收。** 内置 esptool / stcgal 已执行部分 CLI 测试；经典 ESP32 额外与有限 ROM 替身完成协议测试。5 个外部工具仅完成应用端命令与模型测试，尚未在本机执行对应 CLI。OpenOCD / stm32flash / MiniPro 为新增预览适配器；STC8G 为上游实验性协议。

| 配置 ID | 显示名 | 工具 | Flash（字节） | EEPROM（字节） | 固件格式 | 连接 |
|---|---|---|---:|---:|---|---|
| `esp32` | ESP32 | esptool 5.1 | 4194304 | — | .bin | UART / USB 串口 |
| `esp32c3` | ESP32-C3 | esptool 5.1 | 4194304 | — | .bin | UART / USB 串口 |
| `esp32s3` | ESP32-S3 | esptool 5.1 | 8388608 | — | .bin | UART / USB 串口 |
| `stm32f103c8` | STM32F103C8 | STM32CubeProgrammer | 65536 | — | .bin / .hex | ST-LINK / UART |
| `stm32f401cc` | STM32F401CC | STM32CubeProgrammer | 262144 | — | .bin / .hex | ST-LINK / UART / DFU |
| `atmega328p` | ATmega328P | AVRDUDE | 32768 | 1024 | .hex / .bin | ISP / 串口 Bootloader |
| `atmega2560` | ATmega2560 | AVRDUDE | 262144 | 4096 | .hex / .bin | ISP / 串口 Bootloader |
| `stc89c52rc` | STC89C52RC | stcgal 1.10 | 8192 | 6144 | .hex / .bin | UART / 冷启动 |
| `stc89c51rc` | STC89C51RC | stcgal 1.10 | 4096 | 10240 | .bin / .hex | UART / 冷启动 |
| `stc89c54rd` | STC89C54RD+ | stcgal 1.10 | 16384 | 47104 | .bin / .hex | UART / 冷启动 |
| `stc90c52rc` | STC90C52RC | stcgal 1.10 | 8192 | 6144 | .bin / .hex | UART / 冷启动 |
| `stc12c5a60s2` | STC12C5A60S2 | stcgal 1.10 | 61440 | 2048 | .bin / .hex | UART / 冷启动 |
| `stc15f104e` | STC15F104E | stcgal 1.10 | 4096 | 1024 | .bin / .hex | UART / 冷启动 |
| `stc15f2k60s2` | STC15F2K60S2 | stcgal 1.10 | 61440 | 1024 | .bin / .hex | UART / 冷启动 |
| `stc15w4k32s4` | STC15W4K32S4 | stcgal 1.10 | 32768 | 27648 | .bin / .hex | UART / 冷启动 |
| `stc8a8k64s4a12` | STC8A8K64S4A12 | stcgal 1.10 | 65024 | 512 | .bin / .hex | UART / 冷启动 |
| `stc8g1k08` | STC8G1K08 · 8PIN | stcgal 1.10 | 8192 | 4096 | .bin / .hex | UART / 冷启动 |
| `at89s51` | AT89S51 · ISP | AVRDUDE | 4096 | — | .bin / .hex | SPI ISP / 专用兼容编程器 |
| `at89s52` | AT89S52 · ISP | AVRDUDE | 8192 | — | .bin / .hex | SPI ISP / 专用兼容编程器 |
| `at89c51` | AT89C51 · 并行编程 | MiniPro CLI | 4096 | — | .bin / .hex | TL866 / 芯片座 |
| `at89c52` | AT89C52 · 并行编程 | MiniPro CLI | 8192 | — | .bin / .hex | TL866 / 芯片座 |
| `atmega8` | ATmega8 | AVRDUDE | 8192 | 512 | .bin / .hex | ISP |
| `atmega16` | ATmega16 | AVRDUDE | 16384 | 512 | .bin / .hex | ISP |
| `atmega32` | ATmega32 | AVRDUDE | 32768 | 1024 | .bin / .hex | ISP |
| `attiny85` | ATtiny85 | AVRDUDE | 8192 | 512 | .bin / .hex | ISP |
| `esp8266` | ESP8266 / ESP-12 | esptool 5.1 | 4194304 | — | .bin | UART / 下载模式 |
| `esp32c6` | ESP32-C6 | esptool 5.1 | 4194304 | — | .bin | UART / USB 串口 |
| `stm32f103c8-openocd` | STM32F103C8 · OpenOCD | OpenOCD 0.12.x | 65536 | — | .bin / .hex | SWD / 调试探针 |
| `stm32f401cc-openocd` | STM32F401CC · OpenOCD | OpenOCD 0.12.x | 262144 | — | .bin / .hex | SWD / 调试探针 |
| `stm32f407vg-openocd` | STM32F407VG · OpenOCD | OpenOCD 0.12.x | 1048576 | — | .bin / .hex | SWD / 调试探针 |
| `stm32f103c8-uart` | STM32F103C8 · stm32flash | stm32flash | 65536 | — | .bin | UART / 系统 Bootloader |
| `stm32f401cc-uart` | STM32F401CC · stm32flash | stm32flash | 262144 | — | .bin | UART / 系统 Bootloader |

## 参数与限制

- STC 容量取自 stcgal 1.10 的具体模型，分区固定；硬件项按协议分别提供，默认保持原值。EEPROM 区有独立边界检查。
- Intel HEX 可使用 `.hex` / `.ihx` / `.ihex`；stcgal 要求小写扩展名；OpenOCD 要求文件扩展名 `.hex`，请自行改名。stm32flash 当前仅接入 BIN，避免上游 HEX 解析器对基址和稀疏记录的处理差异。
- OpenOCD 面向 0.12.x 的 ST-LINK HLA / CMSIS-DAP，需完整脚本目录。擦除以扇区为单位，不能保证同扇区其他数据保留。
- stm32flash 使用 `-S 地址:长度` 限定 BIN 的地址范围，擦除仍以整页 / 扇区为单位。不擦除模式将 `-e 0` 放在 `-S` 之前，符合上游参数解析顺序。起始地址要求 4 字节对齐；不提供整片擦除或保护位操作。
- AVR 的 ATmega8 / 16 / 32 只提供低 / 高熔丝；AT89S51/S52 不提供任何 AVR 熔丝，需 AVRDUDE 8.1+ 和 8051 兼容编程器。
- MiniPro 设备预设为 `AT89C51@DIP40` / `AT89C52@DIP40`，可选 PLCC44 / TQFP44；精确可用名称以所装数据库为准。默认保持 ID 检查和写后校验；`-v` 在 MiniPro 中表示关闭校验。
- 工具零退出码与虚拟内存校验不能代替目标芯片的擦写、读回与程序运行验收。

每个配置的实际可用选项以 `flashdesk/options.py` 为准。连接说明见 [8051.md](8051.md)，上游依据见 [configuration-sources.md](configuration-sources.md)。
