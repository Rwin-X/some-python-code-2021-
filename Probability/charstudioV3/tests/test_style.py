"""Tests for ui/style.py's theme-switching logic.

These touch zero PyQt widgets -- style.py only uses plain dataclasses
and module globals -- so they run with plain Python, no PyQt6 install
required, same as the other test files here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui import style


def _reset_to_dark():
    style.set_theme(style.STUDIO_DARK.name)


def test_default_theme_is_studio_dark():
    _reset_to_dark()
    assert style.current_theme().name == "studio_dark"
    assert style.BG_BASE == style.STUDIO_DARK.bg_base


def test_set_theme_updates_module_constants():
    _reset_to_dark()
    style.set_theme("drafting_sheet")
    assert style.current_theme().name == "drafting_sheet"
    assert style.BG_BASE == style.DRAFTING_SHEET.bg_base
    assert style.ACCENT == style.DRAFTING_SHEET.accent
    assert style.PLOT_LINE_COLORS == style.DRAFTING_SHEET.plot_colors
    _reset_to_dark()


def test_toggle_theme_round_trips():
    _reset_to_dark()
    style.toggle_theme()
    assert style.current_theme().name == "drafting_sheet"
    style.toggle_theme()
    assert style.current_theme().name == "studio_dark"


def test_set_theme_rejects_unknown_name():
    _reset_to_dark()
    try:
        style.set_theme("not_a_real_theme")
        raised = False
    except ValueError:
        raised = True
    assert raised
    # Failed set_theme should not have left the module in a bad state.
    assert style.current_theme().name == "studio_dark"


def test_build_stylesheet_reflects_current_theme():
    _reset_to_dark()
    dark_qss = style.build_stylesheet()
    assert style.STUDIO_DARK.bg_base in dark_qss

    style.set_theme("drafting_sheet")
    light_qss = style.build_stylesheet()
    assert style.DRAFTING_SHEET.bg_base in light_qss
    assert style.STUDIO_DARK.bg_base not in light_qss
    _reset_to_dark()


def test_themes_have_distinct_radii():
    # The light theme intentionally uses square-ish corners vs. the
    # dark theme's soft rounding -- this is the "different UI" axis,
    # not just a recolor.
    assert style.DRAFTING_SHEET.radius < style.STUDIO_DARK.radius


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
