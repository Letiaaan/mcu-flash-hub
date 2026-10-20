"""Record test evidence and the exact executable digest after a successful build."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flashdesk import __version__
from flashdesk.catalog import PROFILES, TOOL_LABELS, is_8051

suite = ET.parse(ROOT / "docs" / "test-results.xml").getroot()[0]
if any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
    raise SystemExit("Acceptance requires all tests, including package tests, to pass.")
counts = Counter(case.get("classname") for case in suite.iter("testcase"))
digest = hashlib.sha256((ROOT / "dist" / "FlashDesk" / "FlashDesk.exe").read_bytes()).hexdigest()
inventory = {
    "version": __version__, "tests": int(suite.get("tests")), "failures": 0, "errors": 0, "skipped": 0,
    "test_timestamp": suite.get("timestamp"), "executable_sha256": digest, "hardware_acceptance": False,
    "profile_count": len(PROFILES), "tool_count": len(TOOL_LABELS), "profiles_8051": sum(is_8051(p) for p in PROFILES),
    "external_cli_acceptance": False,
    "themes": ["light", "dark", "system"],
    "close_main_window_exits": True,
}
(ROOT / "docs" / "release.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
groups = (
    ("test_core", "固件与基础命令", "格式、HEX 校验和 / EOF、地址、中文路径、文件变化和参数错误"),
    ("test_configuration", "芯片配置与命令适配", "STC 全部 7 项对照真实后端 setter / getter，Flash 容量、STM32 接口、AVR Bootloader / 熔丝、EEPROM、故障注入与配置后 esptool 协议联调"),
    ("test_expansion", "新增型号与外部适配契约", "STC 型号容量、各协议真实 setter / getter、RC 校准、AT89S 无 AVR 熔丝、老 AVR 熔丝差异、OpenOCD Tcl 路径与地址、stm32flash 范围 / 不擦除顺序、MiniPro 校验 / ID、IHX、系列筛选"),
    ("test_presets", "工程方案", f"{len(PROFILES)} 个配置的往返、相对路径、非法类型 / 未知字段、损坏文件保留、保存更新"),
    ("test_gui", "界面", "动态字段、每芯片草稿、接口切换、保存 / 导入 / 导出、加载不自动执行、恢复默认、EEPROM 和命令预览"),
    ("test_resets", "分区重置", f"{len(PROFILES)} 个配置的各分组 / 配置页独立重置、基本页清空、其他芯片草稿和已保存方案保留、任务中禁用、{len(TOOL_LABELS)} 个工具路径独立重置"),
    ("test_runner", "进程管理", "全部配置虚拟写入、失败、超时、取消与重试、双文件指纹检查相关路径、报告、无串口 CLI 失败"),
    ("test_esptool_protocol", "真实 esptool / 虚拟 ROM", "SLIP、写入、MD5、损坏数据与错误芯片"),
    ("test_package", "实际发行包", "内置工具、真实 esptool 协议、子进程故障与取消、覆盖 7 类工具 / 10 个代表配置、EEPROM、STC89 / 15 / 8 选项的界面自检"),
    ("test_source_startup", "干净源码首次启动", "无 EXE / 无虚拟环境的中文及空格目录，从零安装依赖、Qt 和 10 配置界面自检、再次启动复用环境、安装错误及日志"),
    ("test_theme", "统一主题", "深色初始调色板、浅色 / 深色两页实际渲染与工具设置、系统主题信号、偏好保存、配置保持和文字对比度"),
    ("test_shutdown", "完整退出", "主窗口关闭信号、设置弹窗关闭、启动中 / 执行中的子进程终止、取消报告、计时器停止和重复清理"),
)
rows = "\n".join(f"| {label} | {counts['tests.' + key]} | {details} |" for key, label, details in groups)
document = f"""# FlashDesk v{__version__} 验收记录

日期：{suite.get('timestamp', '')[:10]}。结论：**软件与有限协议验收通过；未进行实物芯片验收。**

## 最终构建结果

Windows x64 / Python 3.11.9 / PySide6 6.8.3 / esptool 5.1.0 / stcgal 1.10 / PyInstaller 6.16.0。

最终 EXE 构建后执行 `./.venv/Scripts/python.exe -m pytest -q --junitxml=docs/test-results.xml`：**{suite.get('tests')} passed，0 failed，0 skipped**，耗时 {float(suite.get('time')):.1f} 秒。发行包测试实际执行，未跳过。原始记录见 `test-results.xml`。

| 测试组 | 数量 | 范围 |
|---|---:|---|
{rows}

对应 EXE SHA-256：`{digest}`。结构化记录在 `release.json`。

## 本次补齐的配置

本版提供 **{len(PROFILES)} 个芯片与工具组合、{len(TOOL_LABELS)} 类工具，其中 {sum(is_8051(p) for p in PROFILES)} 个为 51 / 8051 配置**。完整列表见 `SUPPORT.md`。界面加入系列筛选并与搜索组合。未知或跨后端选项会被拒绝；新增配置继续共用分区重置、工程方案和报告。

STC89 的 7 项硬件选项与 stcgal 1.10 的 Stc89Option 集合一致；STC12 / 15 / 8 按各自上游选项类提供保守子集，全部可选值逐项调用真实 setter / getter 核对，型号容量与上游数据库比对。默认保持原值，RC 校准默认不指定。STC8G 维持实验性标识，不宣称协议验收。EEPROM 文件单独检查容量与 SHA-256，预览后变化会在启动前被拒绝。

AT89S51/S52 使用 AVRDUDE 8.1 的精确 ID `89S51` / `89S52`，界面不提供 AVR 熔丝或 Arduino Bootloader，提示正极性 RST 和 8051 编程器条件。AT89C51/C52 使用 MiniPro 的封装设备名，默认保留 ID 检查和写后校验。ATmega8 / 16 / 32 不提供不存在的扩展熔丝。

新增 OpenOCD / stm32flash / MiniPro 的命令测试只验证本应用的适配契约，尚未执行这些外部 CLI。OpenOCD 固定脚本、拒绝危险 Tcl 路径字符；stm32flash 仅接 BIN，通过 `-S` 限定地址范围，`-e 0` 在范围参数之前；MiniPro 不传忽略 ID 或电压修改参数。擦除仍以页 / 扇区或器件为单位，应用不会承诺同页数据保留。

STM32 根据精确配置区分接口：F103C8 不提供 ROM USB DFU，F401CC 可选 DFU。UR 需要 HWrst，探针序列号和索引不同时下发。AVR 串口 Bootloader 不提供本版 EEPROM / 熔丝写入。ESP 地址范围以所选 Flash 容量检查。

本地工程方案可保存、更新、载入及导入导出；导入只包含数据，不携带工具路径或命令，载入后回到虚拟演练。不同芯片的未保存内容在当前窗口内各自保留。

v0.2.1 加入各页及分组重置：基本页恢复时清空文件 / 端口并复位本页参数；芯片页和各分组只复位各自的选项，包括隐藏的关联字段。顶部「重置全部」复位当前芯片的两个配置页。重置不写入芯片，不覆盖已保存方案、其他芯片草稿、工具路径或任务记录，执行任务时按钮禁用。工具设置可分别清空手动路径，保存后才生效。

## 虚拟验收的边界

界面增加浅色 / 深色 / 跟随系统，默认跟随系统；主题选择保存在应用外观设置，不进入烧录方案。测试向 Qt 注入深色初始调色板和系统主题变化信号，检查浅色 / 深色的实际渲染背景、表单、工具设置、文字对比度和偏好保存。发行包自检额外输出两种主题的截图与调色板值。自动测试没有操作 Windows 设置页面实际切换系统主题。

普通虚拟演练使用独立进程和有限 Flash / EEPROM 内存模型，按 BIN 地址或 HEX 段写入并计算哈希；故障场景会改变数据或返回错误。STC 配置寄存器模型调用上游 setter，但初始值只是模型值，并非从芯片读回。AVR 熔丝只记录模型字节，不模拟电气或时钟。演练为了自检始终核对内存，即使真实配置选择关闭校验，也不代表真实工具会进行校验。

经典 ESP32 额外使用真实 esptool，通过本地 TCP 与有限 ROM 协议替身通信。既有协议用例和新增的程序生成配置命令都实际执行。测试使用 no-stub / no-reset 模式，覆盖 SLIP、握手、块写入与 MD5；不覆盖 RAM stub、USB、硬件复位、CPU 指令执行、Flash 时序或固件运行，也不能推定 C3 / S3 已通过协议验收。

实际发行包的 `--self-test` 会启动完整 Qt 界面，覆盖 7 类工具的 10 个代表配置，含 AT89S、AT89C、STC89 / 15 / 8、EEPROM 和 STC 硬件项，输出 JSON 与各配置页截图。自检执行的是内置虚拟子进程，不是外部烧录 CLI。普通流程不访问真实串口，生产界面拒绝网络串口输入。

## 源码首次启动

主窗口关闭现在明确触发整个应用退出。关闭前同步停止当前工具，先请求结束、必要时强制结束，完成取消报告写入；应用 aboutToQuit 和事件循环结束路径另有兜底清理。源码和实际 EXE 自检都进入真实 QApplication 事件循环，验证空闲、子进程启动中、执行中和工具设置打开时的关闭；宿主测试等候父进程退出，并查询记录的子进程 PID，确认测试工具不再运行。测试没有对真实芯片进行烧录。

源码启动用例使用不含 `.venv` / `dist` 的独立副本，目录包含中文、空格及 `&`。通过实际 CMD / Windows PowerShell 5.1 启动器创建新虚拟环境、经 pip 安装依赖，再用新解释器完成 Qt 界面与 10 个配置的虚拟自检；第二次检查复用已有环境。失败用例验证错误退出码、控制台提示及 `startup.log` 中的安装详情，不依赖开发目录的 EXE 或虚拟环境。

首次安装需要系统 Python 和可访问的软件源。默认 PyPI 下载曾发生超时；本次成功测试显式使用 `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`。启动器允许用户自行通过 `-IndexUrl` 选择 HTTPS 软件源，不自动切换或修改系统 pip 配置。源码测试只覆盖本机 Python 3.11；启动脚本接受的 3.12 / 3.13 未逐版本验证。

## 尚待完成

- STM32CubeProgrammer、AVRDUDE、OpenOCD、stm32flash、MiniPro 的本机实际 CLI 联调与版本验证。本次核对官方 / 上游接口并测试应用端命令，但这 5 个外部程序未安装、未执行。
- 全部芯片的接线、电压、驱动、实际擦写 / EEPROM / 熔丝 / 硬件选项的效果，以及掉电恢复和最终程序启动。
- STM32 / STC 精确目标料号的强制比对；目前需人工核对后端日志。Bootloader 和分区保留区不由应用判断。
- STC 独立 Flash 读回、动态 EEPROM 重分区、STM32 Option Bytes / OTP / 读保护、AVR 锁定位及高压恢复、stm32flash 的 HEX 适配。这些功能未接入。

所有报告的 `hardware_acceptance` 保持 false；真实工具零退出码表示工具执行完成，不自动认定实物验收通过。参数来源和适配限制见 `configuration-sources.md`。
"""
(ROOT / "docs" / "acceptance.md").write_text(document, encoding="utf-8")
print(json.dumps(inventory, ensure_ascii=False))
