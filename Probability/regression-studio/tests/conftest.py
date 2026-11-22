import os

# Must be set before any QApplication exists; lets the UI tests run headless.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
