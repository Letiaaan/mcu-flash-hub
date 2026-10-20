import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def binary(tmp_path):
    path = tmp_path / "中文固件 & 空格.bin"
    path.write_bytes(bytes(range(256)) * 8)
    return path
