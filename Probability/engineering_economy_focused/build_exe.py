"""Build a single-file executable with PyInstaller.

Run on the target OS (a Windows .exe must be built on Windows):
    python build_exe.py
Output: dist/EngineeringEconomy(.exe)
"""
import os
import subprocess
import sys


def main() -> int:
    sep = os.pathsep  # ';' on Windows, ':' elsewhere (PyInstaller --add-data format)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "EngineeringEconomy",
        "--add-data", f"data{sep}data",
        "main.py",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
