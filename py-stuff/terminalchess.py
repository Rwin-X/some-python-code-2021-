#!/usr/bin/env python3
"""
terminal_chess.py - Chess for the terminal, built with Windows consoles in mind.

Run:    python terminal_chess.py
Needs:  Python 3.8+  (standard library only, nothing to pip install)

Works in Windows Terminal, PowerShell, cmd.exe (Windows 10+), VS Code terminal,
and on Linux/macOS terminals too.

Windows specifics handled here:
  * ANSI colors are switched on via SetConsoleMode(ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    and the program falls back to a plain monochrome board if that fails.
  * Chess glyphs only render reliably in Windows Terminal / VS Code (the legacy
    conhost font has no fallback), so cmd.exe defaults to letter pieces.
    Override with --unicode or --ascii.
  * No curses (not available on Windows); only input()/print().
"""
import argparse
import os
import random
import re
import sys
import time

FILES = "abcdefgh"
VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
INF = 10 ** 9
MATE = 100000
ILLEGAL = None

# ----------------------------------------------------------------------------
# Console setup (Windows aware)
# ----------------------------------------------------------------------------


def setup_console():
    """Return (ansi_ok, unicode_ok)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ansi = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    unicode_ok = True
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetStdHandle.restype = wintypes.HANDLE
            k32.GetStdHandle.argtypes = [wintypes.DWORD]
            k32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            k32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = wintypes.DWORD()
            if k32.GetConsoleMode(handle, ctypes.byref(mode)):
                if not (mode.value & 0x0004):  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    ansi = ansi and bool(k32.SetConsoleMode(handle, mode.value | 0x0004))
            else:
                ansi = False
        except Exception:
            ansi = False
        unicode_ok = "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") == "vscode"
    return ansi, unicode_ok


# ----------------------------------------------------------------------------
# Board representation: 64-list, index = rank*8 + file, a1 = 0, h8 = 63.
# Pieces: "PNBRQK" white, "pnbrqk" black, "." empty.
# ----------------------------------------------------------------------------


class Position:
    __slots__ = ("board", "white", "castling", "ep", "half", "full")

    def __init__(self, board, white, castling, ep, half, full):
        self.board = board
        self.white = white
        self.castling = castling
        self.ep = ep
        self.half = half
        self.full = full


def start_position():
    b = ["."] * 64
    back = "RNBQKBNR"
    for f in range(8):
        b[f] = back[f]
        b[8 + f] = "P"
        b[48 + f] = "p"
        b[56 + f] = back[f].lower()
    return Position(b, True, "KQkq", -1, 0, 1)


def _build_tables():
    def on(f, r):
        return 0 <= f < 8 and 0 <= r < 8

    def ray(f, r, df, dr):
        out = []
        f += df
        r += dr
        while on(f, r):
            out.append(r * 8 + f)
            f += df
            r += dr
        return out

    kn = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
    diag = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    orth = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    knight, king, pf_w, pf_b, bray, rray = [], [], [], [], [], []
    for sq in range(64):
        f, r = sq & 7, sq >> 3
        knight.append([(r + dr) * 8 + f + df for df, dr in kn if on(f + df, r + dr)])
        king.append([(r + dr) * 8 + f + df for df, dr in diag + orth if on(f + df, r + dr)])
        pf_w.append([(r - 1) * 8 + f + df for df in (-1, 1) if on(f + df, r - 1)])
        pf_b.append([(r + 1) * 8 + f + df for df in (-1, 1) if on(f + df, r + 1)])
        bray.append([x for x in (ray(f, r, df, dr) for df, dr in diag) if x])
        rray.append([x for x in (ray(f, r, df, dr) for df, dr in orth) if x])
    return knight, king, pf_w, pf_b, bray, rray


KNIGHT, KING, PAWN_FROM_W, PAWN_FROM_B, BRAYS, RRAYS = _build_tables()
CASTLE_MASK = {0: "Q", 4: "KQ", 7: "K", 56: "q", 60: "kq", 63: "k"}


def attacked(b, sq, by_white):
    """Is `sq` attacked by the given colour?"""
    if by_white:
        pawn, knight, bishop, rook, queen, king = "PNBRQK"
        pf = PAWN_FROM_W[sq]
    else:
        pawn, knight, bishop, rook, queen, king = "pnbrqk"
        pf = PAWN_FROM_B[sq]
    for s in pf:
        if b[s] == pawn:
            return True
    for s in KNIGHT[sq]:
        if b[s] == knight:
            return True
    for s in KING[sq]:
        if b[s] == king:
            return True
    for r in BRAYS[sq]:
        for s in r:
            p = b[s]
            if p != ".":
                if p == bishop or p == queen:
                    return True
                break
    for r in RRAYS[sq]:
        for s in r:
            p = b[s]
            if p != ".":
                if p == rook or p == queen:
                    return True
                break
    return False


def pseudo_moves(pos):
    b = pos.board
    white = pos.white
    out = []
    add = out.append
    for sq in range(64):
        p = b[sq]
        if p == "." or p.isupper() != white:
            continue
        t = p.upper()
        f, r = sq & 7, sq >> 3
        if t == "P":
            d = 8 if white else -8
            start, last = (1, 7) if white else (6, 0)
            to = sq + d
            if b[to] == ".":
                if to >> 3 == last:
                    for pr in "qrbn":
                        add((sq, to, pr))
                else:
                    add((sq, to, ""))
                    if r == start and b[to + d] == ".":
                        add((sq, to + d, ""))
            for df in (-1, 1):
                if 0 <= f + df < 8:
                    to = sq + d + df
                    q = b[to]
                    if q != "." and q.isupper() != white:
                        if to >> 3 == last:
                            for pr in "qrbn":
                                add((sq, to, pr))
                        else:
                            add((sq, to, ""))
                    elif to == pos.ep:
                        add((sq, to, ""))
        elif t == "N":
            for to in KNIGHT[sq]:
                q = b[to]
                if q == "." or q.isupper() != white:
                    add((sq, to, ""))
        elif t == "K":
            for to in KING[sq]:
                q = b[to]
                if q == "." or q.isupper() != white:
                    add((sq, to, ""))
            c = pos.castling
            if white and sq == 4 and c:
                if "K" in c and b[5] == b[6] == "." and b[7] == "R" and \
                        not any(attacked(b, s, False) for s in (4, 5, 6)):
                    add((4, 6, ""))
                if "Q" in c and b[1] == b[2] == b[3] == "." and b[0] == "R" and \
                        not any(attacked(b, s, False) for s in (4, 3, 2)):
                    add((4, 2, ""))
            elif not white and sq == 60 and c:
                if "k" in c and b[61] == b[62] == "." and b[63] == "r" and \
                        not any(attacked(b, s, True) for s in (60, 61, 62)):
                    add((60, 62, ""))
                if "q" in c and b[57] == b[58] == b[59] == "." and b[56] == "r" and \
                        not any(attacked(b, s, True) for s in (60, 59, 58)):
                    add((60, 58, ""))
        else:
            rays = []
            if t in "BQ":
                rays += BRAYS[sq]
            if t in "RQ":
                rays += RRAYS[sq]
            for ry in rays:
                for to in ry:
                    q = b[to]
                    if q == ".":
                        add((sq, to, ""))
                    else:
                        if q.isupper() != white:
                            add((sq, to, ""))
                        break
    return out


def make(pos, m):
    frm, to, promo = m
    b = pos.board[:]
    white = pos.white
    p = b[frm]
    cap = b[to]
    t = p.upper()
    half = 0 if (t == "P" or cap != ".") else pos.half + 1
    ep = -1
    castling = pos.castling
    b[to] = p
    b[frm] = "."
    if t == "P":
        if to == pos.ep and cap == "." and (frm & 7) != (to & 7):  # en passant
            b[to - 8 if white else to + 8] = "."
        if abs(to - frm) == 16:
            enemy = "p" if white else "P"
            f = to & 7
            if (f > 0 and b[to - 1] == enemy) or (f < 7 and b[to + 1] == enemy):
                ep = (frm + to) // 2
        if promo:
            b[to] = promo.upper() if white else promo
    elif t == "K" and abs(to - frm) == 2:  # castling: move the rook too
        if to > frm:
            b[to - 1] = b[to + 1]
            b[to + 1] = "."
        else:
            b[to + 1] = b[to - 2]
            b[to - 2] = "."
    if castling:
        for s in (frm, to):
            rm = CASTLE_MASK.get(s)
            if rm:
                for ch in rm:
                    castling = castling.replace(ch, "")
    return Position(b, not white, castling, ep, half, pos.full + (0 if white else 1))


def legal(pos):
    """List of (move, resulting_position) for the side to move."""
    b = pos.board
    white = pos.white
    kch = "K" if white else "k"
    ksq = b.index(kch)
    kf, kr = ksq & 7, ksq >> 3
    incheck = attacked(b, ksq, not white)
    out = []
    for m in pseudo_moves(pos):
        frm, to, _ = m
        ff, fr = frm & 7, frm >> 3
        # Only moves that can expose the king need the (slower) attack test.
        risky = (incheck or ff == kf or fr == kr or abs(ff - kf) == abs(fr - kr)
                 or (to == pos.ep and b[frm] in "Pp"))
        nxt = make(pos, m)
        if risky and attacked(nxt.board, nxt.board.index(kch), not white):
            continue
        out.append((m, nxt))
    return out


def in_check(pos):
    k = "K" if pos.white else "k"
    return attacked(pos.board, pos.board.index(k), not pos.white)


def insufficient(pos):
    minors = []
    for sq, p in enumerate(pos.board):
        t = p.upper()
        if t in "PRQ":
            return False
        if t in "NB":
            minors.append((t, ((sq & 7) + (sq >> 3)) % 2))
    if len(minors) <= 1:
        return True
    return all(t == "B" for t, _ in minors) and len({c for _, c in minors}) == 1


def pos_key(pos):
    return ("".join(pos.board), pos.white, pos.castling, pos.ep)


# ----------------------------------------------------------------------------
# Notation
# ----------------------------------------------------------------------------


def sq_name(sq):
    return FILES[sq & 7] + str((sq >> 3) + 1)


def parse_sq(s):
    return FILES.index(s[0]) + 8 * (int(s[1]) - 1)


def to_san(pos, m, legals, suffix=True):
    frm, to, promo = m
    p = pos.board[frm]
    t = p.upper()
    if t == "K" and abs(to - frm) == 2:
        s = "O-O" if to > frm else "O-O-O"
    else:
        cap = pos.board[to] != "." or (t == "P" and to == pos.ep and (frm & 7) != (to & 7))
        s = ""
        if t == "P":
            if cap:
                s += FILES[frm & 7]
        else:
            s += t
            others = [x for x, _ in legals if x != m and pos.board[x[0]] == p and x[1] == to]
            if others:
                if all((o[0] & 7) != (frm & 7) for o in others):
                    s += FILES[frm & 7]
                elif all((o[0] >> 3) != (frm >> 3) for o in others):
                    s += str((frm >> 3) + 1)
                else:
                    s += sq_name(frm)
        if cap:
            s += "x"
        s += sq_name(to)
        if promo:
            s += "=" + promo.upper()
    if suffix:
        nxt = make(pos, m)
        if in_check(nxt):
            s += "#" if not legal(nxt) else "+"
    return s


COORD_RE = re.compile(r"^([a-h][1-8])\s*[-x:]?\s*([a-h][1-8])\s*=?\s*([qrbn])?$", re.I)


def parse_move(text, pos, kids):
    """Return (candidate_moves, error). More than one candidate = promotion choice."""
    s = text.strip()
    low = s.lower().replace("0", "o")
    if low in ("o-o", "oo", "o-o-o", "ooo"):
        short = low in ("o-o", "oo")
        c = [m for m, _ in kids if pos.board[m[0]] in "Kk" and m[1] - m[0] == (2 if short else -2)]
        return (c, None) if c else ([], "Castling is not possible right now.")
    mt = COORD_RE.match(s)
    if mt:
        frm, to = parse_sq(mt.group(1).lower()), parse_sq(mt.group(2).lower())
        promo = (mt.group(3) or "").lower()
        c = [m for m, _ in kids if m[0] == frm and m[1] == to]
        if promo:
            c = [m for m in c if m[2] == promo]
        if not c:
            return [], "Illegal move: " + s
        return c, None

    def norm(x):
        return re.sub(r"[x=+#!?\-]", "", x)

    exact, folded, loose = {}, {}, {}
    for m, _ in kids:
        n = norm(to_san(pos, m, kids, False))
        exact.setdefault(n, []).append(m)
        folded.setdefault(n.lower(), []).append(m)
        if n[0] in "NBRQK" and not m[2]:
            loose.setdefault(n[0] + n[-2:], []).append(m)
    n = norm(s)
    c = exact.get(n) or folded.get(n.lower())
    if c:
        return c, None
    if len(n) >= 3 and n[0].upper() in "NBRQK":
        lc = loose.get(n[0].upper() + n[-2:], [])
        if len(lc) > 1:
            opts = ", ".join(sq_name(m[0]) + sq_name(m[1]) for m in lc)
            return [], "Ambiguous move. Use coordinates, e.g. one of: " + opts
    return [], "Not a legal move: " + s


# ----------------------------------------------------------------------------
# Engine: iterative-deepening negamax + alpha-beta, material + piece-square tables
# ----------------------------------------------------------------------------

_PST = {
    "P": [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10,
          5, 5, 10, 25, 25, 10, 5, 5, 0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5,
          5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
    "N": [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40,
          -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30,
          -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30,
          -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
    "B": [-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 10, 10, 5, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10,
          -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10,
          -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20],
    "R": [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 10, 10, 10, 10, 5, -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5, 0, 0, 0, 5, 5, 0, 0, 0],
    "Q": [-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 5, 5, 5, 0, -10, -5, 0, 5, 5, 5, 5, 0, -5,
          0, 0, 5, 5, 5, 5, 0, -5, -10, 5, 5, 5, 5, 5, 0, -10,
          -10, 0, 5, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20],
}
_KING_MID = [-30, -40, -40, -50, -50, -40, -40, -30] * 4 + \
            [-20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10,
             20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20]
_KING_END = [-50, -40, -30, -20, -20, -30, -40, -50, -30, -20, -10, 0, 0, -10, -20, -30,
             -30, -10, 20, 30, 30, 20, -10, -30, -30, -10, 30, 40, 40, 30, -10, -30,
             -30, -10, 30, 40, 40, 30, -10, -30, -30, -10, 20, 30, 30, 20, -10, -30,
             -30, -30, 0, 0, 0, 0, -30, -30, -50, -30, -30, -30, -30, -30, -30, -50]


def evaluate(pos):
    """Static score in centipawns from the side-to-move's point of view."""
    s = 0
    npm = 0
    wk = bk = 0
    for sq, p in enumerate(pos.board):
        if p == ".":
            continue
        t = p.upper()
        if t == "K":
            if p == "K":
                wk = sq
            else:
                bk = sq
            continue
        v = VAL[t]
        if t != "P":
            npm += v
        if p.isupper():
            s += v + _PST[t][sq ^ 56]
        else:
            s -= v + _PST[t][sq]
    kt = _KING_END if npm <= 2600 else _KING_MID
    s += kt[wk ^ 56] - kt[bk]
    return s if pos.white else -s


class Timeout(Exception):
    pass


class Ctx:
    def __init__(self, deadline, max_ply):
        self.deadline = deadline
        self.max_ply = max_ply
        self.nodes = 0


def order_key(pos, m):
    frm, to, promo = m
    b = pos.board
    s = 0
    victim = b[to]
    if victim != ".":
        s += 10 * VAL[victim.upper()] - VAL[b[frm].upper()]
    elif b[frm] in "Pp" and to == pos.ep:
        s += 900
    if promo:
        s += VAL[promo.upper()]
    return s


def negamax(pos, depth, ply, alpha, beta, ctx):
    ctx.nodes += 1
    if ctx.nodes & 511 == 0 and time.time() > ctx.deadline:
        raise Timeout
    if pos.half >= 100:
        return 0
    if depth <= 0:
        # Quiet leaf -> static eval; extend only while in check (bounded by max_ply).
        if ply >= ctx.max_ply or not in_check(pos):
            return evaluate(pos)
    kids = legal(pos)
    if not kids:
        return -(MATE - ply) if in_check(pos) else 0
    kids.sort(key=lambda k: order_key(pos, k[0]), reverse=True)
    best = -INF
    for _, nxt in kids:
        sc = -negamax(nxt, depth - 1, ply + 1, -beta, -alpha, ctx)
        if sc > best:
            best = sc
            if sc > alpha:
                alpha = sc
                if alpha >= beta:
                    break
    return best


def choose_move(pos, level, tlimit):
    kids = legal(pos)
    if not kids:
        return None
    if len(kids) == 1:
        return kids[0][0]
    if level <= 1 and random.random() < 0.3:  # beginner mode: sometimes plays a random move
        return random.choice(kids)[0]
    random.shuffle(kids)
    kids.sort(key=lambda k: order_key(pos, k[0]), reverse=True)
    ctx = Ctx(time.time() + tlimit, level + 4)
    best = kids[0]
    for depth in range(1, level + 1):
        alpha = -INF
        cur, cur_sc = None, -INF
        try:
            for k in kids:
                sc = -negamax(k[1], depth - 1, 1, -INF, -alpha, ctx)
                if sc > cur_sc:
                    cur_sc, cur = sc, k
                    alpha = sc
        except Timeout:
            break
        best = cur
        kids.remove(cur)
        kids.insert(0, cur)
        if cur_sc > MATE - 100:  # forced mate found, no need to search deeper
            break
    return best[0]


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

SOLID = {"P": "\u265f", "N": "\u265e", "B": "\u265d", "R": "\u265c", "Q": "\u265b", "K": "\u265a"}
HOLLOW = {"P": "\u2659", "N": "\u2658", "B": "\u2657", "R": "\u2656", "Q": "\u2655", "K": "\u2654"}
BULLET = "\u2022"

# 256-colour palette (tweak freely)
C_LIGHT, C_DARK = 137, 94
C_HL_L, C_HL_D = 143, 100        # last move
C_MK_L, C_MK_D = 108, 65         # legal-move marks
C_CHECK = 160                    # king in check


class Style:
    def __init__(self, color, uni):
        self.color = color
        self.uni = uni


def glyph(p, st):
    if not st.uni:
        return p
    t = p.upper()
    if st.color or p.islower():
        return SOLID[t]
    return HOLLOW[t]


def cell(p, sq, st, last, marks, check_sq):
    light = ((sq >> 3) + (sq & 7)) % 2 == 1
    marked = sq in marks
    mark = BULLET if st.uni else "*"
    if not st.color:
        if p == ".":
            return " %s " % (mark if marked else ("." if light else " "))
        g = glyph(p, st)
        return "[%s]" % g if marked else " %s " % g
    if sq == check_sq:
        bg = C_CHECK
    elif marked:
        bg = C_MK_L if light else C_MK_D
    elif sq in last:
        bg = C_HL_L if light else C_HL_D
    else:
        bg = C_LIGHT if light else C_DARK
    if p == ".":
        txt = " %s " % mark if marked else "   "
        return "\033[48;5;%dm\033[38;5;16m%s\033[0m" % (bg, txt)
    fg = "1;38;5;231" if p.isupper() else "38;5;16"
    return "\033[48;5;%dm\033[%sm %s \033[0m" % (bg, fg, glyph(p, st))


def captured_line(pos, st):
    start = {"P": 8, "N": 2, "B": 2, "R": 2, "Q": 1}
    have_w = {t: 0 for t in start}
    have_b = {t: 0 for t in start}
    for p in pos.board:
        if p in "PNBRQ":
            have_w[p] += 1
        elif p in "pnbrq":
            have_b[p.upper()] += 1
    by_white = "".join(glyph(t.lower(), st) * max(0, start[t] - have_b[t]) for t in "QRBNP")
    by_black = "".join(glyph(t, st) * max(0, start[t] - have_w[t]) for t in "QRBNP")
    return "  Captured by White: %-14s Captured by Black: %s" % (by_white or "-", by_black or "-")


def clear(st):
    if st.color:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        os.system("cls" if os.name == "nt" else "clear")


def draw(game, st, flipped, marks, msg, ai_side):
    pos = game.pos
    clear(st)
    last = set(game.moves[-1][1][:2]) if game.moves else set()
    csq = pos.board.index("K" if pos.white else "k") if in_check(pos) else -1
    files = range(7, -1, -1) if flipped else range(8)
    ranks = range(8) if flipped else range(7, -1, -1)
    out = ["", "   T E R M I N A L   C H E S S", ""]
    out.append("      " + "".join(" %s " % FILES[f] for f in files))
    for r in ranks:
        row = " %d    " % (r + 1)
        row += "".join(cell(pos.board[r * 8 + f], r * 8 + f, st, last, marks, csq) for f in files)
        out.append(row + "  %d" % (r + 1))
    out.append("      " + "".join(" %s " % FILES[f] for f in files))
    out += ["", captured_line(pos, st), ""]
    sans = [s for s, _ in game.moves]
    rows = []
    for i in range(0, len(sans), 2):
        rows.append("%d. %s %s" % (i // 2 + 1, sans[i], sans[i + 1] if i + 1 < len(sans) else ""))
    rows = rows[-8:]
    for i in range(0, len(rows), 4):
        out.append("  " + "   ".join("%-14s" % x for x in rows[i:i + 4]).rstrip())
    if rows:
        out.append("")
    if msg:
        out.append("  " + msg)
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


# ----------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------


class Game:
    def __init__(self):
        self.pos = start_position()
        self.moves = []          # (san, move)
        self.keys = [pos_key(self.pos)]

    def play(self, m, san):
        self.moves.append((san, m))
        self.pos = make(self.pos, m)
        self.keys.append(pos_key(self.pos))

    def undo_one(self):
        # Rebuild from the start (cheap) so we never need to store old positions.
        mv = [m for _, m in self.moves[:-1]]
        self.__init__()
        for m in mv:
            kids = legal(self.pos)
            self.play(m, to_san(self.pos, m, kids, False))

    def status(self, kids):
        pos = self.pos
        if not kids:
            if in_check(pos):
                return "Checkmate! %s wins." % ("Black" if pos.white else "White")
            return "Stalemate - draw."
        if insufficient(pos):
            return "Draw - insufficient material."
        if pos.half >= 100:
            return "Draw - 50-move rule."
        if self.keys.count(self.keys[-1]) >= 3:
            return "Draw - threefold repetition."
        return None


HELP = """
  Moves:     e2e4   e2 e4   e4   Nf3   exd5   O-O   O-O-O   e7e8q
  Commands:  moves [sq]   legal moves (e.g. 'moves e2' highlights targets)
             undo         take back your last move
             hint         engine suggestion
             flip         rotate the board
             resign       give up
             new          back to the menu
             help         this text
             quit         exit
"""


def ask(prompt, default=None, choices=None):
    while True:
        try:
            v = input(prompt).strip().lower()
        except EOFError:
            raise KeyboardInterrupt
        if not v and default is not None:
            return default
        if choices is None or v in choices:
            return v
        print("  Please enter one of: " + "/".join(choices))


def run_game(st, args):
    print()
    print("  1) Play vs computer as White")
    print("  2) Play vs computer as Black")
    print("  3) Two players on this keyboard")
    mode = ask("  Choose [1]: ", "1", ("1", "2", "3"))
    ai_side = {"1": False, "2": True, "3": None}[mode]  # True = AI plays White
    level = args.level
    if ai_side is not None and level is None:
        print("  Strength: 1 (beginner) ... 5 (strongest, slower)")
        level = int(ask("  Level [3]: ", "3", ("1", "2", "3", "4", "5")))
    level = level or 3
    flipped = (ai_side is True)
    game = Game()
    marks, msg = set(), "Type 'help' for commands."

    while True:
        pos = game.pos
        kids = legal(pos)
        result = game.status(kids)
        draw(game, st, flipped, marks, msg, ai_side)
        marks, msg = set(), ""
        if result:
            print("\n  " + result)
            return
        side_name = "White" if pos.white else "Black"

        if ai_side is not None and pos.white == ai_side:
            sys.stdout.write("  Computer (%s) is thinking...\n" % side_name)
            sys.stdout.flush()
            t0 = time.time()
            m = choose_move(pos, level, args.time)
            san = to_san(pos, m, kids)
            game.play(m, san)
            msg = "Computer played %s  (%.1fs)" % (san, time.time() - t0)
            continue

        try:
            raw = ask("  %s to move > " % side_name)
        except KeyboardInterrupt:
            raise
        if not raw:
            continue
        cmd = raw.split()
        c0 = cmd[0]

        if c0 in ("quit", "exit", "q"):
            raise KeyboardInterrupt
        if c0 == "help":
            msg = HELP
        elif c0 == "flip":
            flipped = not flipped
        elif c0 == "new":
            return "menu"
        elif c0 == "resign":
            if ask("  Really resign? [y/N]: ", "n", ("y", "n")) == "y":
                draw(game, st, flipped, set(), "", ai_side)
                print("\n  %s resigns. %s wins." % (side_name, "Black" if pos.white else "White"))
                return
        elif c0 == "undo":
            if not game.moves:
                msg = "Nothing to undo."
            else:
                game.undo_one()
                if ai_side is not None and game.moves and game.pos.white == ai_side:
                    game.undo_one()
                msg = "Move taken back."
        elif c0 == "hint":
            sys.stdout.write("  Thinking...\n")
            sys.stdout.flush()
            m = choose_move(pos, 3, min(args.time, 4))
            msg = "Hint: %s" % to_san(pos, m, kids)
        elif c0 == "moves":
            if len(cmd) > 1 and re.match(r"^[a-h][1-8]$", cmd[1]):
                sq = parse_sq(cmd[1])
                tg = [m for m, _ in kids if m[0] == sq]
                marks = {m[1] for m in tg}
                msg = ("%s: %s" % (cmd[1], " ".join(sorted({sq_name(m[1]) for m in tg})))
                       if tg else "No legal moves from %s." % cmd[1])
            else:
                msg = "Legal moves: " + " ".join(sorted(to_san(pos, m, kids, False) for m, _ in kids))
        else:
            cands, err = parse_move(raw, pos, kids)
            if err:
                msg = err
                continue
            if len(cands) > 1:  # promotion choice
                pc = ask("  Promote to (Q/R/B/N) [Q]: ", "q", ("q", "r", "b", "n"))
                cands = [m for m in cands if m[2] == pc]
            m = cands[0]
            game.play(m, to_san(pos, m, kids))


def main():
    ap = argparse.ArgumentParser(description="Terminal chess (Windows-friendly)")
    ap.add_argument("--ascii", action="store_true", help="use letters instead of chess symbols")
    ap.add_argument("--unicode", action="store_true", help="force chess symbols")
    ap.add_argument("--no-color", action="store_true", help="monochrome board")
    ap.add_argument("--level", type=int, choices=range(1, 6), help="engine level 1-5")
    ap.add_argument("--time", type=float, default=5.0, help="max seconds per engine move (default 5)")
    args = ap.parse_args()

    ansi, uni = setup_console()
    if args.no_color:
        ansi = False
    if args.unicode:
        uni = True
    if args.ascii:
        uni = False
    st = Style(ansi, uni)

    try:
        while True:
            if run_game(st, args) == "menu":
                continue
            if ask("\n  Play again? [Y/n]: ", "y", ("y", "n")) == "n":
                break
    except KeyboardInterrupt:
        pass
    finally:
        if st.color:
            sys.stdout.write("\033[0m")
        print("\n  Bye.")


if __name__ == "__main__":
    main()
