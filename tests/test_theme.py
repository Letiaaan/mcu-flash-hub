"""Regression for Windows dark palette leaking into the light configuration pages."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from flashdesk.app import SettingsDialog, Window, configure_application
from flashdesk.catalog import PROFILES
from flashdesk.theme import COLORS, THEME_KEY


@pytest.mark.parametrize("profile_id", ["esp32", "stc15f2k60s2", "at89c51"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_forms_and_settings_use_one_theme_after_dark_system_palette(app, profile_id, theme):
    app.setStyleSheet("")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window, QColor("#202020"))
    dark.setColor(QPalette.ColorRole.Base, QColor("#151515"))
    dark.setColor(QPalette.ColorRole.WindowText, QColor("#EEEEEE"))
    dark.setColor(QPalette.ColorRole.Text, QColor("#EEEEEE"))
    app.setPalette(dark)
    assert app.palette().color(QPalette.ColorRole.Window).lightness() < 50

    controller = configure_application(app, theme)
    window = Window()
    window.profiles.setCurrentRow(next(i for i, p in enumerate(PROFILES) if p.id == profile_id))
    window.show()
    app.processEvents()
    assert controller.effective == theme
    for tab in (0, 1):
        window.tabs.setCurrentIndex(tab)
        app.processEvents()
        body = window.tabs.widget(tab).widget()
        assert body.palette().color(QPalette.ColorRole.Window).name() == COLORS[theme]["window"].lower()
        # Inspect a rendered blank corner, so a palette value alone cannot hide a black viewport.
        pixels = body.grab().toImage()
        rendered_background = pixels.pixelColor(pixels.width() - 3, pixels.height() - 3)
        assert (rendered_background.lightness() > 200) if theme == "light" else (rendered_background.lightness() < 80)
    dialog = SettingsDialog({}, window)
    dialog.show()
    app.processEvents()
    assert dialog.palette().color(QPalette.ColorRole.Window).name() == COLORS[theme]["window"].lower()
    assert dialog.edits["openocd"].palette().color(QPalette.ColorRole.Base).name() == COLORS[theme]["base"].lower()
    assert dialog.edits["openocd"].palette().color(QPalette.ColorRole.Text).name() == COLORS[theme]["text"].lower()
    dialog.close()
    window.close()


def test_system_changes_are_followed_only_in_system_mode(app):
    controller = configure_application(app, "system")
    app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    assert controller.effective == "dark"
    assert app.palette().color(QPalette.ColorRole.Window).name() == "#141c27"
    app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Light)
    assert controller.effective == "light"
    controller.set_preference("dark")
    app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Light)
    assert controller.effective == "dark"
    controller.set_preference("light")
    app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    assert controller.effective == "light"
    controller.set_preference("system")


def test_theme_selector_saves_preference_without_changing_flash_configuration(app, binary, tmp_path):
    from PySide6.QtCore import QSettings
    configure_application(app, "light")
    window = Window()
    window.settings = QSettings(str(tmp_path / "appearance.ini"), QSettings.Format.IniFormat)
    window.file.setText(str(binary))
    window.port.setCurrentText("COM7")
    window.command.setPlainText("preserved command preview")
    before = window.capture_state()
    window.theme_combo.setCurrentIndex(window.theme_combo.findData("dark"))
    window.settings.sync()
    saved = QSettings(str(tmp_path / "appearance.ini"), QSettings.Format.IniFormat)
    assert saved.value(THEME_KEY) == "dark"
    assert window.appearance.effective == "dark"
    assert window.capture_state() == before and not window.runner.busy
    assert window.command.toPlainText() == "preserved command preview"
    window.theme_combo.setCurrentIndex(window.theme_combo.findData("system"))
    assert window.appearance.preference == "system"
    window.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_enabled_text_has_readable_contrast(theme):
    def luminance(value):
        color = QColor(value)
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    colors = COLORS[theme]
    for foreground, background in ((colors["text"], colors["window"]), (colors["text"], colors["base"]),
                                   (colors["muted"], colors["window"]), (colors["on_primary"], colors["primary"])):
        a, b = sorted((luminance(foreground), luminance(background)))
        assert (b + 0.05) / (a + 0.05) >= 4.5
