<h1 align="center">FlashDesk</h1>

<p align="center"><strong>单片机烧录工作台</strong></p>
<p align="center">整合成熟烧录工具，让芯片选择、参数配置、固件检查和任务记录在一个窗口里完成。</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.1-175CD3?style=flat-square" alt="Version 0.2.1">
  <img src="https://img.shields.io/badge/platform-Windows_x64-175CD3?style=flat-square" alt="Windows x64">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/status-development_preview-D69E2E?style=flat-square" alt="Development preview">
</p>

<p align="center">
  <a href="#开始使用">开始使用</a> ·
  <a href="docs/USAGE.md">详细使用说明</a> ·
  <a href="docs/acceptance.md">验收记录</a> ·
  <a href="THIRD_PARTY.md">第三方工具</a>
</p>

> 当前为开发预览版：已完成软件与有限协议测试，尚未进行实物芯片验收。芯片预设不等于已认证的硬件兼容清单。

## 一个工作台，多种芯片

- **按芯片显示配置**：ESP32、STM32、AVR、STC 各自提供适用参数，接口变化时自动调整字段。
- **分区独立重置**：连接、Flash、写入、熔丝、STC 硬件选项可以分别恢复默认值。
- **工程方案复用**：保存、更新、导入和导出配置；切换芯片保留当前窗口中的各自草稿。
- **写入前检查**：BIN / Intel HEX、地址范围、HEX 校验和、固件指纹，以及独立 EEPROM 文件检查。
- **过程可追溯**：命令预览、原始日志、取消、超时和任务报告。
- **没有开发板也能演练**：在内存模型中验证流程，并测试连接失败、校验失败和工具超时。

## 实际界面

![FlashDesk 烧录工作台](docs/images/workbench.png)

<details>
<summary>查看 STC89 分区配置与重置按钮</summary>

![STC89 配置页](docs/images/stc-settings.png)

</details>

## 芯片与工具

| 系列 | 当前预设 | 后端 | 配置示例 |
|---|---|---|---|
| ESP32 | ESP32、ESP32-C3、ESP32-S3 | 内置 esptool 5.1.0 | Flash 容量 / 模式 / 频率、压缩、连接复位 |
| STM32 | STM32F103C8、STM32F401CC | 外部 STM32CubeProgrammer CLI | 调试接口、频率、探针、复位、校验；F401CC 可选 DFU |
| AVR | ATmega328P、ATmega2560 | 外部 AVRDUDE | 烧录器、ISP 时钟、EEPROM、熔丝字节 |
| STC | STC89C52RC | 内置 stcgal 1.10 | 7 项后端硬件选项、握手、电源复位、EEPROM |

STM32CubeProgrammer 和 AVRDUDE 需自行安装，再到「工具设置」选择 EXE。本项目没有重新实现或替代厂商全部功能。[配置范围与限制](docs/USAGE.md)

## 开始使用

### Windows 程序

使用完整的构建目录，运行 `FlashDesk.exe`；在本项目工作目录中也可双击 `启动工作台.cmd`。不要只复制 EXE，需保留 `_internal`、`examples`、`third-party` 等配套目录。

第一次使用：保持「虚拟演练」勾选，点击「演练固件」，再点击「开始虚拟演练」。示例是测试数据，没有可执行功能，不应写入实物。

选择真实固件后，可在芯片配置页调整参数。准备连接硬件时再切换真实模式，检查最终命令和确认窗口。

### 从源码运行

需要 Windows x64 和 Python 3.11，在项目根目录执行：

```powershell
./setup.ps1
./.venv/Scripts/python.exe main.py
```

## 重置规则

| 按钮 | 作用 |
|---|---|
| 连接与固件页「重置本页」 | 清空文件与端口，恢复本页地址、波特率、超时及演练场景 |
| 芯片配置页「重置本页」 | 恢复该配置页全部选项，保留连接与固件页内容 |
| 各分组「重置此分区」 | 只恢复本分组，包括暂时隐藏的关联参数 |
| 顶部「重置全部」 | 将当前芯片的两个配置页恢复初始值，其他芯片草稿保持不变 |
| 工具设置每行「重置」 | 恢复该工具的内置 / 自动查找方式，保存后生效 |

重置只修改界面草稿，不操作芯片，不自动覆盖工程方案。STC 硬件默认是「保持芯片原值」，AVR 熔丝默认为空；这不是给芯片恢复出厂设置。

## 开发与测试

```powershell
# 构建 Windows 程序
./build.ps1

# 含实际发行包的自动化验收
./.venv/Scripts/python.exe -m pytest -q --junitxml=docs/test-results.xml

# 记录测试结果和 EXE 指纹
./.venv/Scripts/python.exe scripts/record_acceptance.py

# 更新发行目录中的文档与许可材料
./.venv/Scripts/python.exe scripts/package_notices.py
```

发行程序也可执行 `FlashDesk.exe --self-test <输出目录>`，生成四类配置的虚拟流程报告和截图。

真实 esptool 已与有限虚拟 ESP32 ROM 完成握手、写入和 MD5 测试；这不覆盖物理接线、USB / 复位时序、RAM stub 或固件运行。STM32CubeProgrammer、AVRDUDE 的实际 CLI 和全部实物仍待联调。[完整验收记录](docs/acceptance.md)

## 文档与贡献

- [使用说明、参数和数据位置](docs/USAGE.md)
- [参数接口依据](docs/configuration-sources.md)
- [如何制作这样的 GitHub README](docs/GITHUB.md)
- [第三方许可与分发说明](THIRD_PARTY.md)

反馈兼容性问题时，请提供芯片完整料号、烧录器型号、工具版本和可公开的日志。新增芯片应同时补充参数、地址规则、失败处理与测试记录。

项目自身的 LICENSE 尚未选定，第三方组件继续遵守各自许可。当前没有在 README 中宣称 MIT 许可或已完成对外分发审计。
