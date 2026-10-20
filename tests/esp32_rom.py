"""Small ESP32 ROM protocol test double, not an instruction-set emulator.

Only local TCP is bound. Implements SLIP frames, register reads, block writes
and MD5 against actual in-memory flash. No monkeypatching of esptool is used.
"""
import hashlib
import socket
import struct
import threading


def slip(data):
    return b"\xc0" + data.replace(b"\xdb", b"\xdb\xdd").replace(b"\xc0", b"\xdb\xdc") + b"\xc0"


class ESP32ROM:
    def __init__(self, corrupt=False, wrong_chip=False):
        self.memory = bytearray(b"\xff" * (4 * 1024 * 1024))
        self.corrupt = corrupt
        self.wrong_chip = wrong_chip
        self.commands = []
        self.errors = []
        self.regs = {0x40001000: 0xFFF0C101 if wrong_chip else 0x00F01D83,
                     0x3FF40014: 347, 0x3FF5A004: 0x12345678, 0x3FF5A008: 0x00000200}
        self.offset = 0
        self.block_size = 1024
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.server.settimeout(15)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.close()
        self.thread.join(timeout=2)

    def serve(self):
        try:
            connection, _ = self.server.accept()
            with connection:
                connection.settimeout(15)
                buffer = b""
                while True:
                    data = connection.recv(16384)
                    if not data:
                        break
                    buffer += data
                    while b"\xc0" in buffer:
                        raw, buffer = buffer.split(b"\xc0", 1)
                        if not raw:
                            continue
                        frame = raw.replace(b"\xdb\xdc", b"\xc0").replace(b"\xdb\xdd", b"\xdb")
                        connection.sendall(self.handle(frame))
        except (ConnectionError, OSError) as exc:
            self.errors.append(str(exc))

    def handle(self, frame):
        direction, op, length, checksum = struct.unpack("<BBHI", frame[:8])
        data = frame[8:]
        assert direction == 0 and len(data) == length
        self.commands.append(op)
        value, payload, status = 0, b"", b"\0\0\0\0"
        copies = 1
        if op == 0x08:  # SYNC emits eight ROM responses
            value, copies = 0x20120707, 8
        elif op == 0x0A:  # READ_REG
            addr, = struct.unpack("<I", data)
            if addr == 0x3FF42000:  # SPI_CMD clears immediately
                value = 0
            elif addr == 0x3FF42080:  # JEDEC ID, after SPI RDID
                value = 0x1640EF if self.regs.get(0x3FF42024, 0) & 0xFF == 0x9F else 0
            else:
                value = self.regs.get(addr, 0)
        elif op == 0x09:  # WRITE_REG
            addr, value, mask, _ = struct.unpack("<IIII", data)
            self.regs[addr] = (self.regs.get(addr, 0) & ~mask) | (value & mask)
            value = 0
        elif op == 0x02:  # FLASH_BEGIN
            size, blocks, self.block_size, self.offset = struct.unpack("<IIII", data[:16])
            self.memory[self.offset:self.offset + size] = b"\xff" * size
        elif op == 0x03:  # FLASH_DATA
            size, sequence, _, _ = struct.unpack("<IIII", data[:16])
            block = data[16:]
            expected = 0xEF
            for byte in block:
                expected ^= byte
            assert checksum == expected and len(block) == size
            offset = self.offset + sequence * self.block_size
            self.memory[offset:offset + size] = block
        elif op == 0x13:  # SPI_FLASH_MD5
            addr, size, _, _ = struct.unpack("<IIII", data)
            if self.corrupt:
                self.memory[addr] ^= 1
            payload = hashlib.md5(self.memory[addr:addr + size]).hexdigest().encode("ascii")
        elif op not in (0x04, 0x0B, 0x0D, 0x0F):
            # ESP32 ROM doesn't implement GET_SECURITY_INFO.
            status = b"\x01\x05\x00\x00"
        response = struct.pack("<BBHI", 1, op, len(payload) + 4, value) + payload + status
        return slip(response) * copies
