# Engineering Economy: ROR vs MARR

Minimal PyQt6 desktop tool, bilingual labels (English with Persian in parentheses).

Pages
1. Interest rate: nominal, effective, continuous; simple vs compound interest
2. Cash flow: cash flow diagram, PW, FW, AW, cumulative and discounted table
3. ROR: rate of return by trial and error with interpolation, sign changes, NPV profile
4. MARR: built from cost of equity, after-tax cost of debt (WACC) and a risk premium
5. ROR vs MARR: difference, accept or reject by the ROR rule and by the PW rule, sensitivity to MARR
6. P-A-F-i: equivalent P, A, F at rate i with three cash flow diagrams and the six factors

Cash flows and MARR are shared: change them on one page and the other pages follow.
On the MARR page, "Use as project MARR" sends the computed MARR to the project.

## Run

    pip install -r requirements.txt
    python main.py

"Load dataset" fills the pages from a JSON file, for example
`data/hydraulic_jack_dataset.json`, and recalculates.

## Build an executable

On Windows, double-click `build_exe.bat` (needs Python 3.10+ on PATH).
Result: `dist\EngineeringEconomy.exe`. PyInstaller builds for the OS it runs on.

## Layout

    main.py          entry point
    core/            pure calculation logic, no Qt
    ui/              window, pages, widgets, QSS in style.py, Persian labels in i18n.py
    tests/           pytest: core math and headless UI tests
    data/            sample dataset

## Test

    QT_QPA_PLATFORM=offscreen python -m pytest
