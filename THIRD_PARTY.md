# 第三方工具与分发

本程序整合现有工具，没有重新实现芯片烧录算法。所有第三方软件保留原有许可。

| 组件 | 本版 | 来源 / 许可 |
|---|---|---|
| esptool | 5.1.0 | https://github.com/espressif/esptool / GPL-2.0-or-later |
| stcgal | 1.10 | https://github.com/grigorig/stcgal / MIT（以随包 LICENSE 为准） |
| PySide6 / Qt | 6.8.3 | https://www.qt.io/qt-for-python / LGPL-3.0、GPL-3.0 或商业许可，具体模块见随包许可 |
| pyserial | 3.5 | https://github.com/pyserial/pyserial / BSD |
| IntelHex | 2.3.0 | https://github.com/python-intelhex/intelhex / BSD |
| STM32CubeProgrammer | 用户安装 | https://www.st.com/en/development-tools/stm32cubeprog.html / ST 官方协议；本包不分发 |
| AVRDUDE | 用户安装 | https://github.com/avrdudes/avrdude / GPL；本包不分发 |
| OpenOCD | 用户安装，适配 0.12.x | https://openocd.org/ / GPL-2.0-or-later；本包不分发 |
| stm32flash | 用户安装 | https://sourceforge.net/projects/stm32flash/ / GPL-2.0-or-later；本包不分发 |
| MiniPro CLI | 用户安装 | https://gitlab.com/DavidGriffith/minipro/ / GPL-3.0-or-later；本包不分发 |

依赖的完整版本、来源与许可文本见发行目录 `third-party/`。`sources/` 保存本版未修改的 esptool 和 stcgal Python 源码，项目工作目录包含 FlashDesk 源码和打包脚本。Qt DLL 保存在独立目录中，可替换兼容版本；没有使用单文件封装。不要只复制 EXE，应保留完整目录及许可材料。

这是本地开发预览版本，尚未完成对外发布的分发材料审计。对外分发时应把本项目与构建依赖的对应源码、构建说明、所有适用许可和替换 Qt 的说明一并提供，并复核供应商工具的再分发条款。
