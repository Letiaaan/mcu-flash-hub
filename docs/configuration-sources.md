# 配置接口依据（v0.2）

核对日期：2026-10-20。以下用于确认参数接口，不构成实物兼容性认证。

- esptool 5.1.0：本地执行 `python -m esptool --help` 及 `write-flash --help`，并用程序生成的带配置命令连接虚拟 ESP32 ROM，确认解析、写入与 MD5 校验。资料：https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html 。频率列表采用各配置支持的保守子集。
- stcgal 1.10：直接核对安装包的 `options.py::Stc89Option`、`frontend.py` 和 `models.py`。STC89 的 7 项硬件配置与上游选项集合一致；单元测试逐项调用真实 setter / getter。当前型号 `STC89C52RC/LE52RC` 的 code 为 8192、EEPROM 为 6144 字节。资料：https://github.com/grigorig/stcgal/blob/master/stcgal/options.py 。本版未修改后端源码。
- STM32CubeProgrammer：官方 MCU CLI 文档确认连接字段、调试接口及复位模式，按接口只下发适用字段；UR 与硬件复位的组合在应用中检查。资料：https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_Command_Lines.html 。当前机器未安装官方 CLI，因此仍需结合实际安装版本执行联调。
- 芯片接口区别：按 ST 的 AN2606 系统 Bootloader 说明，F103C8 不提供 ROM USB DFU，F401CC 可用 USB DFU；因此两个配置的接口列表不同。资料：https://www.st.com/resource/en/application_note/an2606-stm32microcontroller-system-memory-boot-mode-stmicroelectronics.pdf 。
- AVRDUDE：上游命令手册确认烧录器、端口、位时钟、校验、擦除与存储区写入语法，引用文件来自 https://raw.githubusercontent.com/avrdudes/avrdude/main/src/avrdude.1 。当前机器未安装 AVRDUDE；具体版本支持、驱动、Bootloader 和熔丝的真实结果仍需联调。

配置导入只接受已声明的字段和类型，拒绝任意命令、EXE 路径及跨后端选项。选项的存在只表示应用已提供适配；硬件效果需要后续芯片测试。
