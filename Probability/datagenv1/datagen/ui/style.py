"""Palette constants and the single application stylesheet."""

BG_BASE = "#121214"
BG_ELEVATED = "#1a1a1e"
BG_SUNKEN = "#0c0c0e"
BG_HOVER = "#202024"
BORDER = "#2a2a2f"
TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#8a8a92"
TEXT_TERTIARY = "#5a5a62"
ACCENT = "#5ee0c0"
DANGER = "#c0524a"

FONT_UI = "Inter, -apple-system, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: {FONT_UI};
        font-size: 13px;
    }}

    QWidget:disabled {{
        color: {TEXT_TERTIARY};
    }}

    QLabel {{
        background: transparent;
    }}

    QWidget#rootContainer {{
        border: 1px solid {BORDER};
    }}

    QWidget#titleBar {{
        background-color: {BG_ELEVATED};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}

    QWidget#titleBar QLabel {{
        background: transparent;
        color: {TEXT_SECONDARY};
    }}

    QLineEdit, QSpinBox, QComboBox {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_PRIMARY};
        selection-background-color: {BORDER};
    }}

    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}

    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
        color: {TEXT_TERTIARY};
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0px;
        border: none;
    }}

    QComboBox {{
        padding-right: 28px;
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox::down-arrow {{
        image: none;
        width: 0px;
        height: 0px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        selection-background-color: {BG_HOVER};
        selection-color: {ACCENT};
        color: {TEXT_PRIMARY};
        outline: 0;
        padding: 4px;
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 16px;
        color: {TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: {BG_HOVER};
    }}

    QPushButton:pressed {{
        background-color: {BG_SUNKEN};
    }}

    QPushButton:disabled {{
        color: {TEXT_TERTIARY};
    }}

    QPushButton#primaryAction {{
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}

    QPushButton#destructiveAction {{
        border: 1px solid {DANGER};
        color: {DANGER};
    }}

    QLabel#secondaryLabel {{
        color: {TEXT_SECONDARY};
    }}

    QLabel#tertiaryLabel {{
        color: {TEXT_TERTIARY};
        font-size: 11px;
    }}

    QLabel#statusLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QLabel#statusLabel[state="error"] {{
        color: {DANGER};
    }}

    QLabel#statusLabel[state="ok"] {{
        color: {ACCENT};
    }}

    QProgressBar {{
        background-color: {BG_SUNKEN};
        border: none;
        border-radius: 2px;
        max-height: 4px;
        min-height: 4px;
    }}

    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 2px;
    }}

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background-color: {BG_BASE};
        width: 10px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 4px 8px;
    }}
    """
