"""Virtual memory and configuration model; never opens serial ports."""
import hashlib
import json
import sys
import time
from pathlib import Path

from .catalog import BY_ID
from .options import stc_hardware, stc_option_registers, flash_capacity, normalize_options


def image_segments(firmware, bin_address):
    data = Path(firmware["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != firmware["sha256"]:
        raise ValueError("固件指纹不一致")
    if firmware["format"] == ".hex":
        from intelhex import IntelHex
        image = IntelHex(firmware["path"])
        return [(start, bytes(image.tobinarray(start=start, end=end - 1))) for start, end in image.segments()]
    return [(bin_address, data)]


def write_memory(firmware, address, base, capacity, corrupt=False):
    memory = bytearray(b"\xff" * capacity)
    segments = image_segments(firmware, address)
    for start, data in segments:
        offset = start - base
        if offset < 0 or offset + len(data) > capacity:
            raise ValueError("虚拟内存范围越界")
        memory[offset:offset + len(data)] = data
    if corrupt:
        memory[segments[0][0] - base] ^= 1
    for start, data in segments:
        actual = memory[start - base:start - base + len(data)]
        if hashlib.sha256(actual).digest() != hashlib.sha256(data).digest():
            raise ValueError("读回校验失败：注入的数据损坏已检出")


def run(payload: str) -> int:
    spec = json.loads(payload)
    request = spec["request"]
    profile = BY_ID[request["profile"]["id"]]
    opts = normalize_options(profile, request["options"])
    scenario = spec.get("scenario", "success")
    print("[虚拟设备] 软件流程演练，不代表实物芯片验收。", flush=True)
    if scenario == "timeout":
        print("[虚拟设备] 模拟工具无响应，等待超时终止。", flush=True)
        time.sleep(120)
        return 1
    time.sleep(0.08)
    if scenario == "connection":
        print("[虚拟设备] 连接失败：模拟端口未响应。", flush=True)
        return 2
    print(f"[虚拟设备] 已连接 {profile.name}，载入固件。", flush=True)
    print("[虚拟设备] 配置：" + json.dumps(opts, ensure_ascii=False, sort_keys=True), flush=True)
    if profile.tool == "stcgal":
        registers = stc_option_registers(profile)
        for option in stc_hardware(profile):
            if opts[option.key] != "keep":
                registers.set_option(option.key, opts[option.key])
        msr = registers.get_msr()
        value = f"{msr:02X}" if isinstance(msr, int) else bytes(msr).hex().upper()
        print(f"[虚拟设备] STC 配置寄存器模型：0x{value}（不是实物读回）", flush=True)
    if profile.tool == "avrdude":
        programmed = {key: opts[key] for key in ("lfuse", "hfuse", "efuse") if opts.get(key)}
        if programmed:
            print("[虚拟设备] 熔丝字节模型：" + json.dumps(programmed), flush=True)
    for percent in (10, 35, 65, 90, 100):
        print(f"[虚拟设备] 写入 {percent}%", flush=True)
        time.sleep(0.08)
    try:
        write_memory(request["firmware"], request["address"], profile.base, flash_capacity(profile, opts), scenario == "verify")
        if request.get("eeprom"):
            write_memory(request["eeprom"], 0, 0, profile.eeprom_capacity)
            print("[虚拟设备] EEPROM 内存读回校验通过。", flush=True)
    except (ValueError, OSError) as exc:
        print(f"[虚拟设备] {exc}。", flush=True)
        return 4
    print("[虚拟设备] 内存读回校验通过，演练完成（演练始终检查内存，真实校验由配置决定）。", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
