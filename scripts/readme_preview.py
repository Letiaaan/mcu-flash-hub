"""Create path-free screenshots and an offline README layout preview."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from markdown_it import MarkdownIt
from flashdesk.app import configure_application, Window
from flashdesk.catalog import PROFILES

root = Path(__file__).resolve().parents[1]
images = root / "docs" / "images"
images.mkdir(parents=True, exist_ok=True)
app = QApplication([])
configure_application(app, "light")
for font in ("msyh.ttc", "msyhbd.ttc", "consola.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
window = Window()
window.overrides = {}
window.update_tool_status()
# Public images show actual controls with no user's saved project names, paths or logs.
window.preset_combo.blockSignals(True)
window.preset_combo.clear()
window.preset_combo.addItem("选择已保存的工程方案…", None)
window.preset_combo.blockSignals(False)
window.show()
app.processEvents()
window.grab().save(str(images / "workbench.png"))
window.profiles.setCurrentRow(7)
window.family_filter.setCurrentIndex(window.family_filter.findData("8051"))
window.tabs.setCurrentIndex(1)
app.processEvents()
header = window.config.group_headers["hardware"]
window.advanced_scroll.ensureWidgetVisible(header, 0, 0)
window.advanced_scroll.verticalScrollBar().setValue(max(0, header.y() - 12))
app.processEvents()
window.grab().save(str(images / "stc-settings.png"))
window.profiles.setCurrentRow(next(i for i, p in enumerate(PROFILES) if p.id == "stc15f2k60s2"))
app.processEvents()
header = window.config.group_headers["hardware"]
window.advanced_scroll.ensureWidgetVisible(header, 0, 0)
window.advanced_scroll.verticalScrollBar().setValue(max(0, header.y() - 12))
app.processEvents()
window.grab().save(str(images / "stc15-settings.png"))
configure_application(app, "dark")
app.processEvents()
window.grab().save(str(images / "dark-theme.png"))
window.close()

md = MarkdownIt("commonmark", {"html": True}).enable("table")
content = md.render((root / "README.md").read_text(encoding="utf-8"))
html = '''<!doctype html><html lang="zh-CN"><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlashDesk · README 本地预览</title><style>
:root { color-scheme:dark; } * { box-sizing:border-box; }
body { margin:0; padding:32px 20px 80px; background:#0d1117; color:#e6edf3; font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei UI",sans-serif; }
main { max-width:1000px; margin:auto; padding:32px; border:1px solid #30363d; border-radius:6px; }
.notice { max-width:1000px; margin:0 auto 16px; color:#919baa; font-size:13px; }
h1,h2,h3 { line-height:1.3; font-weight:600; } h1 { font-size:38px; } h2 { padding-bottom:10px; border-bottom:1px solid #30363d; margin-top:36px; font-size:24px; }
a { color:#58a6ff; text-decoration:none; } a:hover { text-decoration:underline; }
img { max-width:100%; height:auto; } p[align="center"] img { vertical-align:middle; margin:3px 2px; }
blockquote { border-left:4px solid #6e7681; margin-left:0; padding-left:16px; color:#a9b3bf; }
table { border-collapse:collapse; width:100%; display:block; overflow:auto; }
th,td { border:1px solid #30363d; padding:8px 12px; } tr:nth-child(2n) { background:#161b22; }
pre { overflow:auto; background:#161b22; padding:18px; border-radius:6px; line-height:1.5; }
code { font:13px/1.6 Consolas,monospace; background:#1d232d; border-radius:4px; padding:2px 5px; } pre code { padding:0; background:transparent; }
summary { cursor:pointer; color:#58a6ff; } @media(max-width:700px) { main { padding:20px 14px; } body { padding:16px 8px; } }
</style><div class="notice">README 本地排版预览 · GitHub 发布后以其实际渲染为准</div><main>'''+content+"</main></html>"
(root / "README-preview.html").write_text(html, encoding="utf-8")
print("Public screenshots and README-preview.html written.")
