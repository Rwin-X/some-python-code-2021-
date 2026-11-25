"""Depreciation schedules: straight line, declining balance, SYD, MACRS (GDS, half-year)."""

MACRS = {
    3: [33.33, 44.45, 14.81, 7.41],
    5: [20, 32, 19.2, 11.52, 11.52, 5.76],
    7: [14.29, 24.49, 17.49, 12.49, 8.93, 8.92, 8.93, 4.46],
    10: [10, 18, 14.4, 11.52, 9.22, 7.37, 6.55, 6.55, 6.56, 6.55, 3.28],
    15: [5, 9.5, 8.55, 7.7, 6.93, 6.23, 5.9, 5.9, 5.91, 5.9, 5.91, 5.9, 5.91, 5.9, 5.91, 2.95],
    20: [3.75, 7.219, 6.677, 6.177, 5.713, 5.285, 4.888, 4.522, 4.462, 4.461, 4.462,
         4.461, 4.462, 4.461, 4.462, 4.461, 4.462, 4.461, 4.462, 4.461, 2.231],
}
METHODS = ("Straight line", "Declining balance", "Sum-of-years digits", "MACRS (half-year)")
MACRS_CLASSES = tuple(MACRS)


def charges(method: str, cost: float, salvage: float, life: int,
            db_factor: float = 2.0, macrs_class: int = 5) -> list[float]:
    """Yearly depreciation charges (MACRS ignores salvage by definition)."""
    if life < 1:
        raise ValueError("Life must be at least 1 year")
    if salvage < 0 or salvage > cost:
        raise ValueError("Salvage must be between 0 and the first cost")
    if method == "Straight line":
        return [(cost - salvage) / life] * life
    if method == "Declining balance":
        out, bv, d = [], cost, db_factor / life
        for _ in range(life):
            dep = min(bv * d, max(bv - salvage, 0.0))
            out.append(dep)
            bv -= dep
        return out
    if method == "Sum-of-years digits":
        total = life * (life + 1) / 2
        return [(life - t) / total * (cost - salvage) for t in range(life)]
    if method == "MACRS (half-year)":
        if macrs_class not in MACRS:
            raise ValueError(f"MACRS class must be one of {sorted(MACRS)}")
        return [cost * p / 100 for p in MACRS[macrs_class]]
    raise ValueError(f"Unknown depreciation method: {method}")


def schedule(method, cost, salvage, life, db_factor=2.0, macrs_class=5):
    """Rows of (year, depreciation, accumulated, book value), year 0 included."""
    rows, acc = [(0, 0.0, 0.0, cost)], 0.0
    for t, d in enumerate(charges(method, cost, salvage, life, db_factor, macrs_class), 1):
        acc += d
        rows.append((t, d, acc, cost - acc))
    return rows
