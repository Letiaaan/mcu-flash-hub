# 配置接口依据（v0.3）

核对日期：2026-10-20。以下用于确认参数接口，不构成实物兼容性认证。

- esptool 5.1.0：本地执行 `python -m esptool --help` 及 `write-flash --help`，并用程序生成的带配置命令连接虚拟 ESP32 ROM，确认解析、写入与 MD5 校验。资料：https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html 。频率列表采用各配置支持的保守子集。
- stcgal 1.10：直接核对安装包的 `options.py::Stc89Option`、`frontend.py` 和 `models.py`。STC89 的 7 项硬件配置与上游选项集合一致；单元测试逐项调用真实 setter / getter。当前型号 `STC89C52RC/LE52RC` 的 code 为 8192、EEPROM 为 6144 字节。资料：https://github.com/grigorig/stcgal/blob/master/stcgal/options.py 。本版未修改后端源码。
- STM32CubeProgrammer：官方 MCU CLI 文档确认连接字段、调试接口及复位模式，按接口只下发适用字段；UR 与硬件复位的组合在应用中检查。资料：https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_Command_Lines.html 。当前机器未安装官方 CLI，因此仍需结合实际安装版本执行联调。
- 芯片接口区别：按 ST 的 AN2606 系统 Bootloader 说明，F103C8 不提供 ROM USB DFU，F401CC 可用 USB DFU；因此两个配置的接口列表不同。资料：https://www.st.com/resource/en/application_note/an2606-stm32microcontroller-system-memory-boot-mode-stmicroelectronics.pdf 。
- AVRDUDE：上游命令手册确认烧录器、端口、位时钟、校验、擦除与存储区写入语法，引用文件来自 https://raw.githubusercontent.com/avrdudes/avrdude/main/src/avrdude.1 。当前机器未安装 AVRDUDE；具体版本支持、驱动、Bootloader 和熔丝的真实结果仍需联调。

配置导入只接受已声明的字段和类型，拒绝任意命令、EXE 路径及跨后端选项。选项的存在只表示应用已提供适配；硬件效果需要后续芯片测试。

## v0.3 扩展依据

- STC12 / STC15 / STC8 / STC8G：核对已安装 stcgal 1.10 的 `models.py`、`frontend.py` 协议选择、`options.py` 中 Stc12Option / Stc15AOption / Stc15Option / Stc8Option。测试对全部新增硬件字段的每个可选值调用真实 setter / getter；虚拟流程使用对应寄存器类，初始 FF 仅为模型值。STC8G 的实验性状态、分区与精确后缀保留在界面说明。上游：https://github.com/grigorig/stcgal 。
- AVRDUDE 8.1：核对 https://github.com/avrdudes/avrdude/blob/v8.1/src/avrdude.conf.in 中 `89S51` / `89S52` 的真实 part ID、无 AVR 熔丝、正极性 RESET 及 USBasp 固件条件。上游注释列出串口 `avrisp` 测试方式；这不表示普通 USBasp 自动兼容。ATmega8 / 16 / 32 仅提供实际存在的低 / 高熔丝。
- OpenOCD 0.12.0：核对 https://github.com/openocd-org/openocd/blob/v0.12.0/src/flash/startup.tcl 的 `program filename [verify] [reset] [exit] [address]`；核对同版本 `tcl/interface/stlink.cfg`（HLA）、`cmsis-dap.cfg` 与 STM32 target 脚本。BIN 提供地址，HEX 省略偏移。文件路径以正斜杠与 Tcl 花括号处理，拒绝嵌套求值可能解释的特殊字符，关闭 GDB / Tcl / Telnet 监听。不开放任意命令或解锁。
- stm32flash：核对 https://github.com/stm32duino/stm32flash/blob/master/stm32flash.1 、`main.c` 与 `parsers/hex.c`。工具默认整片擦除；本版仅接 BIN，用 `-f` 强制二进制解析、`-S start:length` 限定范围。`-e 0` 必须位于 `-S` 之前，否则上游拒绝参数组合。页边界由后端处理，不能承诺同页数据保留。由于 HEX 解析器先生成线性数据，非零偏移 / 特殊记录顺序可能影响地址，本版暂不接入其 HEX 模式。
- MiniPro：项目 https://gitlab.com/DavidGriffith/minipro/ ，本次核对的可访问上游镜像为 https://github.com/whaslbeck/minipro ，其中 `man/minipro.1` 确认写入格式自动识别、`-s` 仅将大小不符降为警告、`-v` 关闭写后校验、`-y` 忽略 ID 错误。本应用从不添加 `-y`，不开放电压或锁定位。镜像 `infoic.xml` 确认 AT89C51 / C52 的 DIP40、PLCC44、TQFP44 名称；数据库可随版本变化，必须核对所安装版本。本包不含 MiniPro 可执行程序或数据库，也未执行其 Windows CLI。

这轮没有将 STC-ISP、FlyMCU、Keil 或厂商 GUI 虚构为 CLI。上述外部程序本机未安装、未执行，当前测试只验证应用声明的命令契约；上游资料核对不等于实际 CLI 或硬件验收。
