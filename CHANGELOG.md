# 更新记录

## 0.3.0 · 2026-10-20

- 烧录配置由 8 个增至 32 个，工具由 4 类增至 7 类；14 个配置面向 51 / 8051。
- 增加 STC89C51RC、STC89C54RD+、STC90C52RC、STC12C5A60S2、STC15F104E / F2K60S2 / W4K32S4、STC8A8K64S4A12、STC8G1K08-8PIN。按具体协议提供选项并核对上游容量；STC8G 标记实验性支持。
- 增加 AT89S51/S52 的 AVRDUDE 8.1+ ISP 配置，排除 AVR 熔丝；增加 AT89C51/C52 的 MiniPro 并行编程配置。
- 增加 ATmega8 / 16 / 32、ATtiny85、ESP8266、ESP32-C6；老 AVR 按实际器件省略扩展熔丝。
- 增加 OpenOCD 与 stm32flash 外部适配器，覆盖 STM32F103C8 / F401CC，OpenOCD 另含 F407VG。stm32flash 本版只接 BIN，默认擦除固件涉及的页 / 扇区。
- 增加系列筛选与工具搜索、SDCC IHX / IHEX 检查、完整配置清单及 51 初学者说明。新增字段延续分区重置、独立草稿和工程方案功能。
- 扩展发行包自检，覆盖 7 类工具、10 个代表配置。

软件和虚拟测试不能代替硬件验收；5 类外部 CLI 尚未在本机联调，全部实物仍待验证。具体测试数量与发行 EXE 指纹见 [验收记录](docs/acceptance.md)。
