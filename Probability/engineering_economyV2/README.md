            
# Engineering Economy

Minimal PyQt6 desktop calculator for engineering economy.

Pages: Factors, Rates, Cash flow (PW, FW, AW, IRR, MIRR, payback, B/C, NPV profile),
Alternatives (LCM of lives, incremental ROR), Depreciation (SL, DB/DDB, SYD, MACRS),
Loan, After-tax, Inflation, Capitalized cost, Break-even.

## Run

    pip install -r requirements.txt
    python main.py

"Load dataset" fills every page from a JSON file, for example
`data/hydraulic_jack_dataset.json`, and recalculates.

## Build an executable

On Windows, double-click `build_exe.bat` (needs Python 3.10+ on PATH).
Result: `dist\EngineeringEconomy.exe`, a single file with no console window.
On macOS/Linux run `python build_exe.py` instead; PyInstaller builds for the OS it runs on.

## Layout

    main.py          entry point
    core/            pure calculation logic, no Qt
    ui/              window, pages, widgets, QSS in style.py
    tests/           pytest: core math and headless UI smoke tests
    data/            sample dataset

## Test

    QT_QPA_PLATFORM=offscreen python -m pytest
