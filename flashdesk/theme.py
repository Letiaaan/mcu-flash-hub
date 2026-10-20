"""Application palettes and live Windows theme selection."""
import re

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QPalette

THEME_CHOICES = (("system", "主题：跟随系统"), ("light", "主题：浅色"), ("dark", "主题：深色"))
THEME_KEY = "appearance/theme"
COLORS = {
    "light": dict(window="#F0F4F8", text="#172D43", base="#FFFFFF", panel="#E6EDF5", muted="#576D83",
                  primary="#175CD3", on_primary="#FFFFFF", border="#BCCBD9", hover="#E4EDFD"),
    "dark": dict(window="#141C27", text="#E5EDF7", base="#202D3D", panel="#1B2735", muted="#A8B8CC",
                 primary="#2464C7", on_primary="#FFFFFF", border="#45566B", hover="#2B3D55"),
}
DARK_COLORS = {
    "#172D43": "#E5EDF7", "#F0F4F8": "#141C27", "#E6EDF5": "#1B2735", "#CFD9E4": "#314154",
    "#175CD3": "#84B5FF", "#576D83": "#A8B8CC", "#FFF3D6": "#3B321B", "#795100": "#F2D48A",
    "#BCCBD9": "#45566B", "#E4EDFD": "#2B3D55", "#EDF1F5": "#1B2532", "#8A9AAC": "#8493A6",
    "#104EB8": "#1D56B0", "#9AAFCB": "#334C6A", "#DCE5EF": "#29394D",
}


def stylesheet(light_style, effective):
    colors = COLORS[effective]
    sheet = light_style
    if effective == "dark":
        sheet = re.sub(r"#[0-9A-Fa-f]{6}", lambda m: DARK_COLORS.get(m.group().upper(), m.group()), sheet)
        sheet = sheet.replace("background: white", "background: #202D3D")
        # Links need a lighter blue than filled buttons to keep text contrast.
        sheet += """
QListWidget::item:selected, QPushButton#primary { background: #2464C7; color: white; border-color: #2464C7; }
QPushButton#primary:hover { background: #1D56B0; border-color: #1D56B0; }
QPushButton#primary:disabled { background: #334C6A; border-color: #334C6A; }
QProgressBar::chunk { background: #2464C7; }
"""
    sheet += f"""
QComboBox QAbstractItemView {{ background: {colors['base']}; color: {colors['text']};
    selection-background-color: {colors['primary']}; selection-color: {colors['on_primary']}; }}
QToolTip {{ background: {colors['base']}; color: {colors['text']}; border: 1px solid {colors['border']}; }}
"""
    return sheet


class ThemeController(QObject):
    preference_changed = Signal(str)

    def __init__(self, app, light_style, preference):
        super().__init__(app)
        self.app = app
        self.light_style = light_style
        self.preference = "system"
        self.effective = "light"
        self._updating = False
        app.setStyle("Fusion")
        app.styleHints().colorSchemeChanged.connect(self._system_changed)
        self.set_preference(preference)

    def set_preference(self, preference):
        if preference not in dict(THEME_CHOICES):
            raise ValueError("Unknown theme preference")
        self.preference = preference
        self._updating = True
        try:
            hints = self.app.styleHints()
            if preference == "system":
                hints.unsetColorScheme()
                effective = "dark" if hints.colorScheme() == Qt.ColorScheme.Dark else "light"
            else:
                hints.setColorScheme(Qt.ColorScheme.Dark if preference == "dark" else Qt.ColorScheme.Light)
                effective = preference
            self._render(effective)
        finally:
            self._updating = False
        self.preference_changed.emit(preference)

    def _system_changed(self, scheme):
        if self.preference == "system" and not self._updating:
            self._render("dark" if scheme == Qt.ColorScheme.Dark else "light")

    def _render(self, effective):
        colors = COLORS[effective]
        palette = self.app.style().standardPalette()
        for role, value in (
            (QPalette.ColorRole.Window, "window"), (QPalette.ColorRole.WindowText, "text"),
            (QPalette.ColorRole.Base, "base"), (QPalette.ColorRole.AlternateBase, "panel"),
            (QPalette.ColorRole.Text, "text"), (QPalette.ColorRole.Button, "base"),
            (QPalette.ColorRole.ButtonText, "text"), (QPalette.ColorRole.Highlight, "primary"),
            (QPalette.ColorRole.HighlightedText, "on_primary"), (QPalette.ColorRole.ToolTipBase, "base"),
            (QPalette.ColorRole.ToolTipText, "text"), (QPalette.ColorRole.PlaceholderText, "muted"),
        ):
            palette.setColor(role, QColor(colors[value]))
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(colors["muted"]))
        if effective == "dark":
            for role, color in ((QPalette.ColorRole.Light, "#45566B"), (QPalette.ColorRole.Midlight, "#314154"),
                                (QPalette.ColorRole.Mid, "#314154"), (QPalette.ColorRole.Dark, "#101722"),
                                (QPalette.ColorRole.Shadow, "#080D14")):
                palette.setColor(role, QColor(color))
        self.effective = effective
        self.app.setPalette(palette)
        self.app.setStyleSheet(stylesheet(self.light_style, effective))


def configure_theme(app, light_style, preference=None):
    controller = getattr(app, "_flashdesk_theme", None)
    if controller is None:
        stored = QSettings("FlashDesk", "FlashDesk").value(THEME_KEY, "system", str)
        chosen = preference if preference is not None else stored if stored in dict(THEME_CHOICES) else "system"
        controller = ThemeController(app, light_style, chosen)
        app._flashdesk_theme = controller
    elif preference is not None:
        controller.set_preference(preference)
    return controller
