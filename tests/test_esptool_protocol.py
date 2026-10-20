import subprocess
import sys

import pytest

from esp32_rom import ESP32ROM


@pytest.mark.parametrize("scenario", ["success", "corrupt", "wrong_chip"])
def test_real_esptool_rom_protocol(binary, scenario, tmp_path):
    with ESP32ROM(corrupt=scenario == "corrupt", wrong_chip=scenario == "wrong_chip") as rom:
        argv = [sys.executable, "-m", "esptool", "--chip", "esp32", "--port", f"socket://127.0.0.1:{rom.port}",
                "--before", "no-reset", "--after", "no-reset", "--no-stub", "write-flash", "--flash-size", "4MB",
                "0x10000", str(binary)]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20,
                              encoding="utf-8", errors="replace")
        assert 0x08 in rom.commands
        if scenario == "success":
            assert proc.returncode == 0, proc.stdout
            assert "Hash of data verified" in proc.stdout
            assert rom.memory[0x10000:0x10000 + binary.stat().st_size] == binary.read_bytes()
            assert 0x03 in rom.commands and 0x13 in rom.commands
        elif scenario == "corrupt":
            assert proc.returncode != 0, proc.stdout
            assert "does not match" in proc.stdout
            assert 0x13 in rom.commands
        else:
            assert proc.returncode != 0, proc.stdout
            assert 0x03 not in rom.commands
