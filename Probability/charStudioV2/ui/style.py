"""Centralized QSS and palette constants for ChartStudio."""

BG_BASE = "#121214"
BG_ELEVATED = "#1a1a1e"
BG_SUNKEN = "#0c0c0e"
BORDER = "#2a2a2f"
TEXT_PRIMARY = "#e8e8ea"
TEXT_SECONDARY = "#8a8a92"
TEXT_TERTIARY = "#5a5a62"
ACCENT = "#5ee0c0"
DANGER = "#c0524a"

FONT_UI = "Inter, -apple-system, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"

# Matplotlib-facing palette so figures match the app chrome.
PLOT_LINE_COLORS = ["#5ee0c0", "#7aa7e0", "#e0b85e", "#c0524a", "#a47de0", "#5ed0e0"]


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: {FONT_UI};
        font-size: 13px;
    }}

    QWidget#titleBar {{
        background-color: {BG_ELEVATED};
        border-bottom: 1px solid {BORDER};
    }}

    QWidget#elevatedPanel {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QWidget#sidePanel {{
        background-color: {BG_ELEVATED};
        border-right: 1px solid {BORDER};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QListWidget {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_PRIMARY};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}

    QListWidget::item {{
        padding: 4px 2px;
    }}

    QListWidget::item:selected {{
        background-color: {BG_ELEVATED};
        color: {ACCENT};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 16px;
        color: {TEXT_PRIMARY};
    }}

    QPushButton:hover {{
        background-color: #202024;
    }}

    QPushButton:pressed {{
        background-color: {BG_SUNKEN};
    }}

    QPushButton#primaryAction {{
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}

    QPushButton#destructiveAction {{
        border: 1px solid {DANGER};
        color: {DANGER};
    }}

    QLabel#sectionLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 600;
    }}

    QLabel#secondaryLabel {{
        color: {TEXT_SECONDARY};
    }}

    QLabel#tertiaryLabel {{
        color: {TEXT_TERTIARY};
        font-size: 11px;
    }}

    QLabel#monoLabel {{
        font-family: {FONT_MONO};
        color: {TEXT_PRIMARY};
    }}

    QCheckBox {{
        spacing: 6px;
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
    """
