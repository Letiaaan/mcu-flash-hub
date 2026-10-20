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

suite = ET.parse(ROOT / "docs" / "test-results.xml").getroot()[0]
if any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
    raise SystemExit("Acceptance requires all tests, including package tests, to pass.")
counts = Counter(case.get("classname") for case in suite.iter("testcase"))
digest = hashlib.sha256((ROOT / "dist" / "FlashDesk" / "FlashDesk.exe").read_bytes()).hexdigest()
inventory = {
    "version": __version__, "tests": int(suite.get("tests")), "failures": 0, "errors": 0, "skipped": 0,
    "test_timestamp": suite.get("timestamp"), "executable_sha256": digest, "hardware_acceptance": False,
}
(ROOT / "docs" / "release.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
groups = (
    ("test_core", "固件与基础命令", "格式、HEX 校验和 / EOF、地址、中文路径、文件变化和参数错误"),
    ("test_configuration", "芯片配置与命令适配", "STC 全部 7 项对照真实后端 setter / getter，Flash 容量、STM32 接口、AVR Bootloader / 熔丝、EEPROM、故障注入与配置后 esptool 协议联调"),
    ("test_presets", "工程方案", "8 个配置的往返、相对路径、非法类型 / 未知字段、损坏文件保留、保存更新"),
    ("test_gui", "界面", "动态字段、每芯片草稿、接口切换、保存 / 导入 / 导出、加载不自动执行、恢复默认、EEPROM 和命令预览"),
    ("test_resets", "分区重置", "8 个芯片的各分组 / 配置页独立重置、基本页清空、其他芯片草稿和已保存方案保留、任务中禁用、各工具路径独立重置"),
    ("test_runner", "进程管理", "全部配置虚拟写入、失败、超时、取消与重试、双文件指纹检查相关路径、报告、无串口 CLI 失败"),
    ("test_esptool_protocol", "真实 esptool / 虚拟 ROM", "SLIP、写入、MD5、损坏数据与错误芯片"),
    ("test_package", "实际发行包", "内置工具、真实 esptool 协议、子进程故障与取消、四系列界面 + EEPROM + STC 选项的完整自检"),
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

四系列使用独立的配置能力声明，共用界面、导入校验和命令适配；未知或跨后端选项会被拒绝。STC89 的 7 项硬件选项与 stcgal 1.10 的 Stc89Option 集合一致；默认不下发修改。AVR 的三个熔丝字节默认留空。EEPROM 文件单独检查容量与 SHA-256，预览后变化会在启动前被拒绝。

STM32 根据精确配置区分接口：F103C8 不提供 ROM USB DFU，F401CC 可选 DFU。UR 需要 HWrst，探针序列号和索引不同时下发。AVR 串口 Bootloader 不提供本版 EEPROM / 熔丝写入。ESP 地址范围以所选 Flash 容量检查。

本地工程方案可保存、更新、载入及导入导出；导入只包含数据，不携带工具路径或命令，载入后回到虚拟演练。不同芯片的未保存内容在当前窗口内各自保留。

v0.2.1 加入各页及分组重置：基本页恢复时清空文件 / 端口并复位本页参数；芯片页和各分组只复位各自的选项，包括隐藏的关联字段。顶部「重置全部」复位当前芯片的两个配置页。重置不写入芯片，不覆盖已保存方案、其他芯片草稿、工具路径或任务记录，执行任务时按钮禁用。工具设置可分别清空手动路径，保存后才生效。

## 虚拟验收的边界

普通虚拟演练使用独立进程和有限 Flash / EEPROM 内存模型，按 BIN 地址或 HEX 段写入并计算哈希；故障场景会改变数据或返回错误。STC 配置寄存器模型调用上游 setter，但初始值只是模型值，并非从芯片读回。AVR 熔丝只记录模型字节，不模拟电气或时钟。演练为了自检始终核对内存，即使真实配置选择关闭校验，也不代表真实工具会进行校验。

经典 ESP32 额外使用真实 esptool，通过本地 TCP 与有限 ROM 协议替身通信。既有协议用例和新增的程序生成配置命令都实际执行。测试使用 no-stub / no-reset 模式，覆盖 SLIP、握手、块写入与 MD5；不覆盖 RAM stub、USB、硬件复位、CPU 指令执行、Flash 时序或固件运行，也不能推定 C3 / S3 已通过协议验收。

实际发行包的 `--self-test` 会启动完整 Qt 界面并依次演练 ESP、STM32、AVR、STC，含 EEPROM 和 STC 硬件项，输出 JSON 与各配置页截图。普通流程不访问真实串口，生产界面拒绝网络串口输入。

## 尚待完成

- STM32CubeProgrammer、AVRDUDE 的本机实际 CLI 联调与版本验证。本次核对官方 / 上游接口并测试命令，但这两个外部程序未安装、未执行。
- 全部芯片的接线、电压、驱动、实际擦写 / EEPROM / 熔丝 / 硬件选项的效果，以及掉电恢复和最终程序启动。
- STM32 / STC 精确目标料号的强制比对；目前需人工核对后端日志。Bootloader 和分区保留区不由应用判断。
- STC 独立 Flash 读回、STM32 Option Bytes / OTP / 读保护、AVR 锁定位及高压恢复。这些界面未假装提供。

所有报告的 `hardware_acceptance` 保持 false；真实工具零退出码表示工具执行完成，不自动认定实物验收通过。参数来源和适配限制见 `configuration-sources.md`。
"""
(ROOT / "docs" / "acceptance.md").write_text(document, encoding="utf-8")
print(json.dumps(inventory, ensure_ascii=False))
