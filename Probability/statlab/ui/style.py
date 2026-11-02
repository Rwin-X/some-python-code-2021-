"""Centralized QSS stylesheet and palette constants for StatLab."""

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

    QWidget#sidebar {{
        background-color: {BG_ELEVATED};
        border-right: 1px solid {BORDER};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_PRIMARY};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {ACCENT};
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

    QPushButton:disabled {{
        color: {TEXT_TERTIARY};
        border: 1px solid {BORDER};
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

    QLabel#monoLabel {{
        font-family: {FONT_MONO};
        color: {TEXT_PRIMARY};
    }}

    QLabel#sectionHeading {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 600;
    }}

    QListWidget, QTableWidget, QTreeWidget {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        gridline-color: {BORDER};
        selection-background-color: #243530;
        selection-color: {ACCENT};
    }}

    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 6px;
    }}

    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {BG_BASE};
        color: {TEXT_SECONDARY};
        padding: 8px 16px;
        border: 1px solid transparent;
        border-bottom: none;
    }}

    QTabBar::tab:selected {{
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-bottom: 1px solid {BG_ELEVATED};
        background-color: {BG_ELEVATED};
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}

    QProgressBar {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 6px;
        text-align: center;
        color: {TEXT_SECONDARY};
    }}

    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 6px;
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

    QScrollBar:horizontal {{
        background-color: {BG_BASE};
        height: 10px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {BORDER};
        border-radius: 5px;
        min-width: 24px;
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    QStatusBar {{
        background-color: {BG_ELEVATED};
        border-top: 1px solid {BORDER};
        color: {TEXT_SECONDARY};
    }}
    """
