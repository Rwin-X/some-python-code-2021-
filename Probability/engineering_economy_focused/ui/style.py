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

FONT_UI = "Inter, -apple-system, Segoe UI, Vazirmatn, Tahoma, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {BG_BASE};
        color: {TEXT_PRIMARY};
        font-family: {FONT_UI};
        font-size: 13px;
    }}
    QLabel {{ background: transparent; }}
    QWidget#rootContainer {{ border: 1px solid {BORDER}; }}
    QWidget#titleBar {{
        background-color: {BG_ELEVATED};
        border-bottom: 1px solid {BORDER};
    }}
    QWidget#titleBar QLabel {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
    QWidget#sidebar {{
        background-color: {BG_ELEVATED};
        border-right: 1px solid {BORDER};
    }}

    QLabel#pageTitle {{ font-size: 18px; font-weight: 600; }}
    QLabel#secondaryLabel {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
    QLabel#tertiaryLabel {{ color: {TEXT_TERTIARY}; font-size: 11px; }}
    QLabel#valueLabel {{ font-family: {FONT_MONO}; color: {TEXT_PRIMARY}; }}
    QLabel#status {{ color: {TEXT_TERTIARY}; font-size: 12px; }}
    QLabel#status[error="true"] {{ color: {DANGER}; }}

    QLineEdit, QPlainTextEdit {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {BG_HOVER};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; }}

    QComboBox {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 28px 6px 10px;
    }}
    QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox::down-arrow {{ image: none; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        selection-background-color: {BG_HOVER};
        selection-color: {ACCENT};
        outline: none;
    }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 16px;
    }}
    QPushButton:hover {{ background-color: {BG_HOVER}; }}
    QPushButton:pressed {{ background-color: {BG_SUNKEN}; }}
    QPushButton:disabled {{ color: {TEXT_TERTIARY}; }}
    QPushButton#primaryAction {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}

    QListWidget#nav {{ background: transparent; border: none; outline: none; }}
    QListWidget#nav::item {{
        padding: 8px 12px;
        margin: 1px 0;
        border-radius: 8px;
        color: {TEXT_SECONDARY};
    }}
    QListWidget#nav::item:hover {{ background-color: {BG_HOVER}; }}
    QListWidget#nav::item:selected {{ background-color: {BG_HOVER}; color: {ACCENT}; }}

    QTableWidget {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        gridline-color: {BORDER};
        outline: none;
    }}
    QTableWidget::item {{ padding: 3px 8px; border: none; }}
    QTableWidget::item:selected {{ background-color: {BG_HOVER}; color: {TEXT_PRIMARY}; }}
    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 6px 8px;
        font-size: 11px;
    }}
    QTableCornerButton::section {{ background-color: {BG_ELEVATED}; border: none; }}

    QScrollBar:vertical {{ background-color: {BG_BASE}; width: 10px; border: none; }}
    QScrollBar::handle:vertical {{
        background-color: {BORDER}; border-radius: 5px; min-height: 24px;
    }}
    QScrollBar:horizontal {{ background-color: {BG_BASE}; height: 10px; border: none; }}
    QScrollBar::handle:horizontal {{
        background-color: {BORDER}; border-radius: 5px; min-width: 24px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
    QSizeGrip {{ background: transparent; }}
    """
