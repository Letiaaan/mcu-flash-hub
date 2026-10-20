"""Data-only project files; imported projects never select tools or execute tasks."""
import json
import os
import uuid
from pathlib import Path

from .catalog import BY_ID
from .options import OptionError, normalize_options


class PresetError(ValueError):
    pass


FIELDS = {"schema_version", "name", "profile_id", "firmware", "eeprom", "port", "baud", "address", "timeout", "options"}


def validate_preset(data: dict) -> dict:
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise PresetError("方案字段不完整或包含不支持的字段；请使用本程序导出的 JSON。")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise PresetError("不支持这个方案版本。")
    for key in ("name", "profile_id", "firmware", "eeprom", "port", "address"):
        if not isinstance(data[key], str) or len(data[key]) > 4096 or "\0" in data[key]:
            raise PresetError(f"方案字段 {key} 无效。")
    if not data["name"].strip() or len(data["name"]) > 80:
        raise PresetError("方案名称应为 1–80 个字符。")
    if data["profile_id"] not in BY_ID:
        raise PresetError("方案中的芯片尚未接入。")
    if type(data["baud"]) is not int or data["baud"] not in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
        raise PresetError("方案中的波特率不受支持。")
    if type(data["timeout"]) is not int or not 5 <= data["timeout"] <= 3600:
        raise PresetError("方案中的超时应为 5–3600 秒。")
    try:
        address = int(data["address"], 0)
    except ValueError as exc:
        raise PresetError("方案中的 BIN 地址无效。") from exc
    if not 0 <= address <= 0xFFFFFFFF:
        raise PresetError("方案中的 BIN 地址超出 32 位范围。")
    profile = BY_ID[data["profile_id"]]
    if data["eeprom"] and not profile.eeprom_capacity:
        raise PresetError("此芯片不支持独立 EEPROM 文件。")
    try:
        options = normalize_options(profile, data["options"])
    except OptionError as exc:
        raise PresetError(str(exc)) from exc
    return dict(data, options=options)


def read_preset(path: Path) -> dict:
    if path.stat().st_size > 256 * 1024:
        raise PresetError("方案文件超过 256 KB。")
    try:
        data = validate_preset(json.loads(path.read_text(encoding="utf-8-sig")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PresetError("方案不是有效的 UTF-8 JSON 文件。") from exc
    for key in ("firmware", "eeprom"):
        if data[key]:
            value = Path(data[key]).expanduser()
            data[key] = str((path.parent / value).resolve() if not value.is_absolute() else value.resolve())
    return data


def write_preset(path: Path, data: dict) -> None:
    data = validate_preset(data)
    # Relative file references make a project folder portable. Never copy firmware implicitly.
    for key in ("firmware", "eeprom"):
        if data[key]:
            try:
                data[key] = os.path.relpath(Path(data[key]).resolve(), path.parent.resolve())
            except ValueError:  # different Windows drive
                data[key] = str(Path(data[key]).resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


class PresetStore:
    def __init__(self, folder: Path):
        self.folder = folder

    def list(self):
        result = []
        if self.folder.exists():
            for path in self.folder.glob("*.json"):
                try:
                    result.append((path, read_preset(path)))
                except (OSError, PresetError):
                    continue
        return sorted(result, key=lambda pair: (pair[1]["name"].casefold(), pair[0].name))

    def save(self, data, path: Path | None = None):
        if path is not None and path.resolve().parent != self.folder.resolve():
            raise PresetError("保存目标不在本地方案目录中。")
        dest = path or self.folder / (uuid.uuid4().hex + ".json")
        write_preset(dest, data)
        return dest
