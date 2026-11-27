"""Theme-aware QSS and palette constants for ChartStudio.

Two themes are shipped:

- "studio_dark" -- the original dark theme: flat panels, soft rounding,
  a mint accent.
- "drafting_sheet" -- a light theme modeled on technical drafting paper
  and blueprint annotation: an off-white page, ink-black text, hairline
  rules instead of soft rounded cards, square corners, and a single
  cobalt-ink accent used only for the primary action and data lines.

Call `set_theme(name)` to switch; it updates every module-level
constant in place (BG_BASE, TEXT_PRIMARY, PLOT_LINE_COLORS, ...) so
existing `from ui import style; style.BG_BASE` call sites keep working
after a switch -- they just see the new values.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Theme:
    name: str
    display_name: str

    bg_base: str
    bg_elevated: str
    bg_sunken: str
    border: str
    text_primary: str
    text_secondary: str
    text_tertiary: str
    accent: str
    danger: str

    font_ui: str
    font_mono: str

    radius: int  # corner radius in px used across inputs/buttons/panels
    plot_colors: list[str] = field(default_factory=list)


STUDIO_DARK = Theme(
    name="studio_dark",
    display_name="Studio Dark",
    bg_base="#121214",
    bg_elevated="#1a1a1e",
    bg_sunken="#0c0c0e",
    border="#2a2a2f",
    text_primary="#e8e8ea",
    text_secondary="#8a8a92",
    text_tertiary="#5a5a62",
    accent="#5ee0c0",
    danger="#c0524a",
    font_ui="Inter, -apple-system, Segoe UI, sans-serif",
    font_mono="JetBrains Mono, Consolas, monospace",
    radius=8,
    plot_colors=["#5ee0c0", "#7aa7e0", "#e0b85e", "#c0524a", "#a47de0", "#5ed0e0"],
)

# "Drafting Sheet": off-white graph-paper ground, ink-black text, a
# single cobalt accent (technical-pen ink), hairline square-cornered
# rules instead of soft rounded cards. No rounding on panels/lists;
# a small 3px radius survives only on inputs and buttons so they read
# as controls rather than drafted lines.
DRAFTING_SHEET = Theme(
    name="drafting_sheet",
    display_name="Drafting Sheet",
    bg_base="#f7f6f2",
    bg_elevated="#fbfaf7",
    bg_sunken="#efeee8",
    border="#c9c6bb",
    text_primary="#1c1b18",
    text_secondary="#5c594f",
    text_tertiary="#938f82",
    accent="#2d4f8f",
    danger="#a13d33",
    font_ui="Inter, -apple-system, Segoe UI, sans-serif",
    font_mono="JetBrains Mono, Consolas, monospace",
    radius=3,
    plot_colors=["#2d4f8f", "#a13d33", "#8a6d1f", "#3f7d5c", "#6a4f8f", "#1f7a8c"],
)

THEMES = {STUDIO_DARK.name: STUDIO_DARK, DRAFTING_SHEET.name: DRAFTING_SHEET}

_current: Theme = STUDIO_DARK


def _sync_module_constants() -> None:
    globals()["BG_BASE"] = _current.bg_base
    globals()["BG_ELEVATED"] = _current.bg_elevated
    globals()["BG_SUNKEN"] = _current.bg_sunken
    globals()["BORDER"] = _current.border
    globals()["TEXT_PRIMARY"] = _current.text_primary
    globals()["TEXT_SECONDARY"] = _current.text_secondary
    globals()["TEXT_TERTIARY"] = _current.text_tertiary
    globals()["ACCENT"] = _current.accent
    globals()["DANGER"] = _current.danger
    globals()["FONT_UI"] = _current.font_ui
    globals()["FONT_MONO"] = _current.font_mono
    globals()["RADIUS"] = _current.radius
    globals()["PLOT_LINE_COLORS"] = _current.plot_colors


def current_theme() -> Theme:
    return _current


def set_theme(name: str) -> Theme:
    global _current
    if name not in THEMES:
        raise ValueError(f"Unknown theme: {name}")
    _current = THEMES[name]
    _sync_module_constants()
    return _current


def toggle_theme() -> Theme:
    other = DRAFTING_SHEET.name if _current.name == STUDIO_DARK.name else STUDIO_DARK.name
    return set_theme(other)


_sync_module_constants()  # populate BG_BASE, TEXT_PRIMARY, etc. at import time


def build_stylesheet() -> str:
    t = _current
    r = t.radius
    input_radius = max(r, 4)  # inputs/buttons always keep a minimum tactile radius

    return f"""
    QWidget {{
        background-color: {t.bg_base};
        color: {t.text_primary};
        font-family: {t.font_ui};
        font-size: 13px;
    }}

    QWidget#titleBar {{
        background-color: {t.bg_elevated};
        border-bottom: 1px solid {t.border};
    }}

    QWidget#elevatedPanel {{
        background-color: {t.bg_elevated};
        border: 1px solid {t.border};
        border-radius: {r}px;
    }}

    QWidget#sidePanel {{
        background-color: {t.bg_elevated};
        border-right: 1px solid {t.border};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QListWidget {{
        background-color: {t.bg_sunken};
        border: 1px solid {t.border};
        border-radius: {input_radius}px;
        padding: 6px 10px;
        color: {t.text_primary};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {t.accent};
    }}

    QListWidget::item {{
        padding: 4px 2px;
    }}

    QListWidget::item:selected {{
        background-color: {t.bg_base};
        color: {t.accent};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QPushButton {{
        background-color: {t.bg_elevated};
        border: 1px solid {t.border};
        border-radius: {input_radius}px;
        padding: 8px 16px;
        color: {t.text_primary};
    }}

    QPushButton:hover {{
        background-color: {t.bg_sunken if t.name == "drafting_sheet" else "#202024"};
    }}

    QPushButton:pressed {{
        background-color: {t.bg_sunken};
    }}

    QPushButton#primaryAction {{
        border: 1px solid {t.accent};
        color: {t.accent};
    }}

    QPushButton#destructiveAction {{
        border: 1px solid {t.danger};
        color: {t.danger};
    }}

    QLabel#sectionLabel {{
        color: {t.text_secondary};
        font-size: 11px;
        font-weight: 600;
    }}

    QLabel#secondaryLabel {{
        color: {t.text_secondary};
    }}

    QLabel#tertiaryLabel {{
        color: {t.text_tertiary};
        font-size: 11px;
    }}

    QLabel#monoLabel {{
        font-family: {t.font_mono};
        color: {t.text_primary};
    }}

    QCheckBox {{
        spacing: 6px;
    }}

    QScrollBar:vertical {{
        background-color: {t.bg_base};
        width: 10px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {t.border};
        border-radius: {min(r, 5)}px;
        min-height: 24px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
