"""Check source runtime versions and DLL imports without opening the GUI."""
from importlib import import_module, metadata
from pathlib import Path
import sys
import tomllib


def check():
    root = Path(__file__).resolve().parents[1]
    requirements = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    for requirement in requirements:
        name, expected = requirement.split("==")
        actual = metadata.version(name)
        if actual != expected:
            raise RuntimeError(f"{name}: expected {expected}, found {actual}")
    for module in ("PySide6.QtWidgets", "serial", "intelhex", "esptool", "stcgal.frontend"):
        import_module(module)
    print("[Environment] Runtime dependencies and Qt imports OK.")


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:
        print(f"[Environment] {type(exc).__name__}: {exc}")
        sys.exit(1)
