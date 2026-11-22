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
POINT = "#c9c9d0"
SELECTION = "rgba(94, 224, 192, 0.18)"

FONT_UI = '"Inter", "Segoe UI", "Helvetica Neue", "DejaVu Sans", sans-serif'
FONT_MONO = '"JetBrains Mono", "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace'


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
    QWidget#titleBar QLabel {{ background: transparent; }}
    QWidget#sidebar {{ border-right: 1px solid {BORDER}; }}
    QWidget#footerBar {{ border-top: 1px solid {BORDER}; }}

    QWidget#elevatedPanel {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        color: {TEXT_PRIMARY};
        selection-background-color: {SELECTION};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {ACCENT};
    }}
    QPlainTextEdit#monoText {{ font-family: {FONT_MONO}; }}

    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 7px 12px;
        color: {TEXT_PRIMARY};
    }}
    QPushButton:hover {{ background-color: {BG_HOVER}; }}
    QPushButton:pressed {{ background-color: {BG_SUNKEN}; }}
    QPushButton:disabled {{ color: {TEXT_TERTIARY}; }}
    QPushButton#primaryAction {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}
    QPushButton#primaryAction:disabled {{ border: 1px solid {BORDER}; color: {TEXT_TERTIARY}; }}

    QComboBox {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QComboBox:hover {{ background-color: {BG_ELEVATED}; }}
    QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox::down-arrow {{ image: none; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        selection-background-color: {SELECTION};
        selection-color: {TEXT_PRIMARY};
        outline: 0;
    }}

    QListWidget {{
        background-color: {BG_SUNKEN};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 4px;
        outline: 0;
    }}
    QListWidget::item {{ padding: 3px 4px; border-radius: 4px; }}
    QListWidget::item:hover {{ background-color: {BG_ELEVATED}; }}
    QListWidget::item:selected {{ background-color: transparent; color: {TEXT_PRIMARY}; }}
    QListWidget::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {TEXT_TERTIARY};
        border-radius: 4px;
        background-color: {BG_SUNKEN};
    }}
    QListWidget::indicator:checked {{ background-color: {ACCENT}; border: 1px solid {ACCENT}; }}

    QCheckBox {{ spacing: 8px; background: transparent; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {TEXT_TERTIARY};
        border-radius: 4px;
        background-color: {BG_SUNKEN};
    }}
    QCheckBox::indicator:checked {{ background-color: {ACCENT}; border: 1px solid {ACCENT}; }}

    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {TEXT_SECONDARY};
        padding: 8px 16px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:hover {{ background-color: {BG_ELEVATED}; }}
    QTabBar::tab:selected {{ color: {TEXT_PRIMARY}; border-bottom: 2px solid {ACCENT}; }}

    QTableView, QTableWidget {{
        background-color: {BG_SUNKEN};
        gridline-color: {BORDER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        selection-background-color: {SELECTION};
        selection-color: {TEXT_PRIMARY};
        font-family: {FONT_MONO};
        outline: 0;
    }}
    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
        border-right: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        padding: 6px 10px;
        font-family: {FONT_UI};
    }}
    QTableCornerButton::section {{ background-color: {BG_ELEVATED}; border: none; }}

    QLabel#secondaryLabel {{ color: {TEXT_SECONDARY}; }}
    QLabel#tertiaryLabel {{ color: {TEXT_TERTIARY}; font-size: 11px; }}
    QLabel#sectionLabel {{ color: {TEXT_TERTIARY}; font-size: 11px; font-weight: bold; }}
    QLabel#monoLabel {{ font-family: {FONT_MONO}; color: {TEXT_PRIMARY}; }}
    QLabel#equationLabel {{ font-family: {FONT_MONO}; color: {ACCENT}; font-size: 15px; }}
    QLabel#metricTitle {{ color: {TEXT_SECONDARY}; font-size: 11px; }}
    QLabel#metricValue {{ font-family: {FONT_MONO}; color: {TEXT_PRIMARY}; font-size: 20px; }}

    QScrollBar:vertical {{ background-color: {BG_BASE}; width: 10px; border: none; }}
    QScrollBar::handle:vertical {{ background-color: {BORDER}; border-radius: 5px; min-height: 24px; }}
    QScrollBar:horizontal {{ background-color: {BG_BASE}; height: 10px; border: none; }}
    QScrollBar::handle:horizontal {{ background-color: {BORDER}; border-radius: 5px; min-width: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}

    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 4px 8px;
    }}
    """
