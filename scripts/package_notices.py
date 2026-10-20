"""Keep license texts, inventory and unmodified GPL backend sources with the build."""
import importlib.metadata
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist" / "FlashDesk"
notices = DEST / "third-party"
notices.mkdir(parents=True, exist_ok=True)
inventory = []
for dist in importlib.metadata.distributions():
    name = dist.metadata["Name"]
    inventory.append({"name": name, "version": dist.version, "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", "See package license"),
                      "homepage": dist.metadata.get("Home-page", ""), "project_urls": dist.metadata.get_all("Project-URL") or []})
    for file in dist.files or []:
        if any(x in str(file).lower() for x in ("license", "copying", "notice")) and ".dist-info/" in str(file):
            src = Path(dist.locate_file(file))
            if src.is_file():
                target = notices / name / Path(*file.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
(notices / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
for name in ("esptool", "stcgal"):
    module = __import__(name)
    shutil.copytree(Path(module.__file__).parent, notices / "sources" / name,
                    ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
for file in ("README.md", "THIRD_PARTY.md", "CHANGELOG.md", "requirements-lock.txt"):
    shutil.copy2(ROOT / file, DEST / file)
shutil.copytree(ROOT / "examples", DEST / "examples", dirs_exist_ok=True)
docs = DEST / "docs"
docs.mkdir(exist_ok=True)
for name in ("acceptance.md", "test-results.xml", "configuration-sources.md", "release.json", "USAGE.md", "GITHUB.md", "SUPPORT.md", "8051.md"):
    source = ROOT / "docs" / name
    if source.exists():
        shutil.copy2(source, docs / name)
images = ROOT / "docs" / "images"
if images.exists():
    shutil.copytree(images, docs / "images", dirs_exist_ok=True)
print(f"Notices and backend sources included: {notices}")
