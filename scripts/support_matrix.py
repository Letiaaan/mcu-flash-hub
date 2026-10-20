"""Build the public support matrix from the same catalog used by the GUI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flashdesk.catalog import PROFILES, TOOL_LABELS, is_8051

rows = []
for p in PROFILES:
    fmt = " / ".join(p.formats)
    eeprom = str(p.eeprom_capacity) if p.eeprom_capacity else "—"
    rows.append(f"| `{p.id}` | {p.name} | {TOOL_LABELS[p.tool]} | {p.capacity} | {eeprom} | {fmt} | {p.connection} |")

text = f"""# 烧录配置清单

目录包含 {len(PROFILES)} 个芯片与工具组合，涉及 {len({p.chip for p in PROFILES})} 个不同目标料号、{len(TOOL_LABELS)} 类工具；其中 {sum(is_8051(p) for p in PROFILES)} 个为 51 / 8051 配置。配置数包含同一 STM32 使用不同工具的条目，不代表同等数量的独立芯片。

**全部条目均未实物验收。** 内置 esptool / stcgal 已执行部分 CLI 测试；经典 ESP32 额外与有限 ROM 替身完成协议测试。5 个外部工具仅完成应用端命令与模型测试，尚未在本机执行对应 CLI。OpenOCD / stm32flash / MiniPro 为新增预览适配器；STC8G 为上游实验性协议。

| 配置 ID | 显示名 | 工具 | Flash（字节） | EEPROM（字节） | 固件格式 | 连接 |
|---|---|---|---:|---:|---|---|
""" + "\n".join(rows) + """

## 参数与限制

- STC 容量取自 stcgal 1.10 的具体模型，分区固定；硬件项按协议分别提供，默认保持原值。EEPROM 区有独立边界检查。
- Intel HEX 可使用 `.hex` / `.ihx` / `.ihex`；stcgal 要求小写扩展名；OpenOCD 要求文件扩展名 `.hex`，请自行改名。stm32flash 当前仅接入 BIN，避免上游 HEX 解析器对基址和稀疏记录的处理差异。
- OpenOCD 面向 0.12.x 的 ST-LINK HLA / CMSIS-DAP，需完整脚本目录。擦除以扇区为单位，不能保证同扇区其他数据保留。
- stm32flash 使用 `-S 地址:长度` 限定 BIN 的地址范围，擦除仍以整页 / 扇区为单位。不擦除模式将 `-e 0` 放在 `-S` 之前，符合上游参数解析顺序。起始地址要求 4 字节对齐；不提供整片擦除或保护位操作。
- AVR 的 ATmega8 / 16 / 32 只提供低 / 高熔丝；AT89S51/S52 不提供任何 AVR 熔丝，需 AVRDUDE 8.1+ 和 8051 兼容编程器。
- MiniPro 设备预设为 `AT89C51@DIP40` / `AT89C52@DIP40`，可选 PLCC44 / TQFP44；精确可用名称以所装数据库为准。默认保持 ID 检查和写后校验；`-v` 在 MiniPro 中表示关闭校验。
- 工具零退出码与虚拟内存校验不能代替目标芯片的擦写、读回与程序运行验收。

每个配置的实际可用选项以 `flashdesk/options.py` 为准。连接说明见 [8051.md](8051.md)，上游依据见 [configuration-sources.md](configuration-sources.md)。
"""
(ROOT / "docs" / "SUPPORT.md").write_text(text, encoding="utf-8")
print(f"Support matrix: {len(PROFILES)} profiles")
