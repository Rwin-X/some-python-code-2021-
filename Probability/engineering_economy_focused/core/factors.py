"""Interest factors linking P, A, F at rate i over n periods (end-of-period)."""


def _zero(x: float) -> bool:
    return abs(x) < 1e-12


def fp(i, n):  # (F/P,i,n)
    return (1 + i) ** n


def pf(i, n):  # (P/F,i,n)
    return (1 + i) ** -n


def af(i, n):  # (A/F,i,n)
    return 1 / n if _zero(i) else i / ((1 + i) ** n - 1)


def ap(i, n):  # (A/P,i,n)
    return 1 / n if _zero(i) else i * (1 + i) ** n / ((1 + i) ** n - 1)


def fa(i, n):  # (F/A,i,n)
    return n if _zero(i) else ((1 + i) ** n - 1) / i


def pa(i, n):  # (P/A,i,n)
    return n if _zero(i) else ((1 + i) ** n - 1) / (i * (1 + i) ** n)


FACTOR_ROWS = (
    ("(F/P,i,n)", "Single payment compound amount", fp),
    ("(P/F,i,n)", "Single payment present worth", pf),
    ("(A/F,i,n)", "Sinking fund", af),
    ("(A/P,i,n)", "Capital recovery", ap),
    ("(F/A,i,n)", "Uniform series compound amount", fa),
    ("(P/A,i,n)", "Uniform series present worth", pa),
)


def equivalent(given: str, amount: float, i: float, n: int) -> dict:
    """Given one of P, A or F, return all three equivalent amounts at rate i."""
    if n < 1:
        raise ValueError("Periods n must be at least 1")
    if i <= -1:
        raise ValueError("Rate must be greater than -100%")
    if given == "P":
        p, a, f = amount, amount * ap(i, n), amount * fp(i, n)
    elif given == "A":
        p, a, f = amount * pa(i, n), amount, amount * fa(i, n)
    elif given == "F":
        p, a, f = amount * pf(i, n), amount * af(i, n), amount
    else:
        raise ValueError("Given must be P, A or F")
    return {"P": p, "A": a, "F": f,
            "factors": [(sym, desc, fn(i, n)) for sym, desc, fn in FACTOR_ROWS]}
