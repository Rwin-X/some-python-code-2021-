#!/usr/bin/env python3
"""
TermPac — Terminal Pac-Man
devforge // curses edition

Controls: WASD or arrow keys, Q to quit, P to pause
Ghosts run real scatter/chase/frightened state machine, not random walk.
"""

import curses
import random
import time
from collections import deque
from enum import Enum

# ---------------------------------------------------------------- MAP -----
# # wall  .  pellet  o  power pellet  space  empty  G  ghost spawn  P  pac spawn
RAW_MAP = [
"#############################",
"#............#............#",
"#.####.#####.#.#####.####.#",
"#o####.#####.#.#####.####o#",
"#.####.#####.#.#####.####.#",
"#...........................",
"#.####.#.#########.#.####.#",
"#.####.#.#########.#.####.#",
"#......#.....#.....#......#",
"######.##### # #####.######",
"     #.#     #     #.#     ",
"######.# ### # ### #.######",
"      .  #G G   G#  .      ",
"######.# ######### #.######",
"     #.#     #     #.#     ",
"######.# ######### #.######",
"#............#............#",
"#.####.#####.#.#####.####.#",
"#o..#.......P.......#..o#",
"###.#.#.#########.#.#.###",
"#......#.....#.....#......#",
"#.##########.#.##########.#",
"#...........................",
"#############################",
]

class GhostState(Enum):
    SCATTER = 0
    CHASE = 1
    FRIGHTENED = 2
    EATEN = 3

GHOST_COLORS_PAIR = {0: 5, 1: 6, 2: 7, 3: 8}  # curses color pair ids
GHOST_CHARS = ["B", "P", "I", "C"]  # Blinky Pinky Inky Clyde style

DIRS = {
    curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0),
    curses.KEY_LEFT: (0, -1), curses.KEY_RIGHT: (0, 1),
    ord('w'): (-1, 0), ord('s'): (1, 0),
    ord('a'): (0, -1), ord('d'): (0, 1),
}

def norm(row):
    return row.ljust(len(RAW_MAP[0]), '#')

class Board:
    def __init__(self):
        self.grid = [list(norm(r)) for r in RAW_MAP]
        self.h = len(self.grid)
        self.w = len(self.grid[0])
        self.pellets_left = 0
        self.pac_start = (1, 1)
        self.ghost_spawns = []
        for y, row in enumerate(self.grid):
            for x, c in enumerate(row):
                if c == '.':
                    self.pellets_left += 1
                elif c == 'o':
                    self.pellets_left += 1
                elif c == 'P':
                    self.pac_start = (y, x)
                    self.grid[y][x] = '.'
                    self.pellets_left += 1
                elif c == 'G':
                    self.ghost_spawns.append((y, x))
                    self.grid[y][x] = ' '
        if not self.ghost_spawns:
            self.ghost_spawns = [(11, 14)]

    def is_wall(self, y, x):
        y %= self.h
        x %= self.w
        return self.grid[y][x] == '#'

    def cell(self, y, x):
        y %= self.h
        x %= self.w
        return self.grid[y][x]

    def eat(self, y, x):
        y %= self.h
        x %= self.w
        c = self.grid[y][x]
        if c in ('.', 'o'):
            self.grid[y][x] = ' '
            self.pellets_left -= 1
            return c
        return None


class Ghost:
    def __init__(self, name, y, x, color_pair, scatter_target, char):
        self.name = name
        self.y, self.x = y, x
        self.spawn = (y, x)
        self.dir = (0, -1)
        self.state = GhostState.SCATTER
        self.color = color_pair
        self.scatter_target = scatter_target
        self.char = char
        self.frightened_timer = 0
        self.release_timer = 0

    def next_cell_options(self, board):
        y, x = self.y, self.x
        opts = []
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if not board.is_wall(ny, nx):
                # no reversing unless frightened just started / dead end
                if (dy, dx) == (-self.dir[0], -self.dir[1]):
                    continue
                opts.append((dy, dx))
        if not opts:  # dead end, allow reverse
            opts = [(-self.dir[0], -self.dir[1])]
        return opts

    def choose_target(self, board, pac_pos, pac_dir, blinky_pos):
        if self.state == GhostState.SCATTER:
            return self.scatter_target
        if self.state == GhostState.EATEN:
            return self.spawn
        if self.state == GhostState.FRIGHTENED:
            return None  # random
        # CHASE behavior per ghost personality
        py, px = pac_pos
        if self.name == "blinky":
            return (py, px)
        if self.name == "pinky":
            return (py + pac_dir[0] * 4, px + pac_dir[1] * 4)
        if self.name == "inky":
            bx, by = blinky_pos[1], blinky_pos[0]
            tx, ty = px + pac_dir[1] * 2, py + pac_dir[0] * 2
            return (ty + (ty - by), tx + (tx - bx))
        if self.name == "clyde":
            dist = abs(py - self.y) + abs(px - self.x)
            if dist > 8:
                return (py, px)
            return self.scatter_target
        return (py, px)

    def step(self, board, pac_pos, pac_dir, blinky_pos):
        if self.state == GhostState.EATEN and (self.y, self.x) == self.spawn:
            self.state = GhostState.SCATTER
        target = self.choose_target(board, pac_pos, pac_dir, blinky_pos)
        opts = self.next_cell_options(board)
        if not opts:
            return
        if target is None:
            dy, dx = random.choice(opts)
        else:
            ty, tx = target
            best = None
            best_d = None
            for dy, dx in opts:
                ny, nx = self.y + dy, self.x + dx
                d = (ny - ty) ** 2 + (nx - tx) ** 2
                if best_d is None or d < best_d:
                    best_d = d
                    best = (dy, dx)
            dy, dx = best
        self.dir = (dy, dx)
        self.y = (self.y + dy) % board.h
        self.x = (self.x + dx) % board.w


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.board = Board()
        self.score = 0
        self.lives = 3
        self.level = 1
        self.paused = False
        self.frightened_until = 0
        self.mode_timer = 0
        self.mode = GhostState.SCATTER
        self.mode_switch_schedule = [7, 20, 7, 20, 5, 20, 5, 999]
        self.mode_idx = 0
        self.frames = 0
        self.reset_positions()
        self.setup_colors()
        self.high_score = 0

    def reset_positions(self):
        py, px = self.board.pac_start
        self.pac_y, self.pac_x = py, px
        self.pac_dir = (0, 0)
        self.next_dir = (0, 0)
        corners = [(1, self.board.w - 2), (1, 1),
                   (self.board.h - 2, self.board.w - 2), (self.board.h - 2, 1)]
        names = ["blinky", "pinky", "inky", "clyde"]
        spawns = self.board.ghost_spawns
        while len(spawns) < 4:
            spawns.append(spawns[-1])
        self.ghosts = []
        for i, name in enumerate(names):
            gy, gx = spawns[i % len(spawns)]
            self.ghosts.append(Ghost(name, gy, gx, 5 + i, corners[i], GHOST_CHARS[i]))
        self.mode_idx = 0
        self.mode = GhostState.SCATTER
        self.mode_timer = 0

    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_YELLOW, -1)   # pacman
        curses.init_pair(2, curses.COLOR_CYAN, -1)     # walls
        curses.init_pair(3, curses.COLOR_WHITE, -1)    # pellets
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # power pellet
        curses.init_pair(5, curses.COLOR_RED, -1)      # blinky
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # pinky
        curses.init_pair(7, curses.COLOR_CYAN, -1)     # inky
        curses.init_pair(8, curses.COLOR_YELLOW, -1)   # clyde
        curses.init_pair(9, curses.COLOR_BLUE, -1)     # frightened
        curses.init_pair(10, curses.COLOR_GREEN, -1)   # hud

    def try_move_pac(self):
        for d in (self.next_dir, self.pac_dir):
            if d == (0, 0):
                continue
            ny, nx = self.pac_y + d[0], self.pac_x + d[1]
            if not self.board.is_wall(ny, nx):
                self.pac_dir = d
                break
        ny = (self.pac_y + self.pac_dir[0]) % self.board.h
        nx = (self.pac_x + self.pac_dir[1]) % self.board.w
        if not self.board.is_wall(ny, nx):
            self.pac_y, self.pac_x = ny, nx
        eaten = self.board.eat(self.pac_y, self.pac_x)
        if eaten == '.':
            self.score += 10
        elif eaten == 'o':
            self.score += 50
            self.frightened_until = self.frames + 40
            for g in self.ghosts:
                if g.state not in (GhostState.EATEN,):
                    g.state = GhostState.FRIGHTENED
                    g.dir = (-g.dir[0], -g.dir[1])

    def update_ghost_modes(self):
        if self.frightened_until and self.frames >= self.frightened_until:
            self.frightened_until = 0
            for g in self.ghosts:
                if g.state == GhostState.FRIGHTENED:
                    g.state = self.mode
            return
        if self.frightened_until:
            return  # freeze scatter/chase clock while frightened
        self.mode_timer += 1
        limit = self.mode_switch_schedule[min(self.mode_idx, len(self.mode_switch_schedule) - 1)]
        if self.mode_timer >= limit * 6:  # ~6 frames per second-ish
            self.mode_timer = 0
            self.mode_idx += 1
            self.mode = GhostState.CHASE if self.mode == GhostState.SCATTER else GhostState.SCATTER
            for g in self.ghosts:
                if g.state in (GhostState.SCATTER, GhostState.CHASE):
                    g.state = self.mode

    def check_collisions(self):
        for g in self.ghosts:
            if (g.y, g.x) == (self.pac_y, self.pac_x):
                if g.state == GhostState.FRIGHTENED:
                    g.state = GhostState.EATEN
                    self.score += 200
                elif g.state in (GhostState.SCATTER, GhostState.CHASE):
                    self.lose_life()
                    return

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            return
        py, px = self.board.pac_start
        self.pac_y, self.pac_x = py, px
        self.pac_dir = (0, 0)
        self.next_dir = (0, 0)
        for g in self.ghosts:
            g.y, g.x = g.spawn
            g.state = GhostState.SCATTER
        self.frightened_until = 0
        time.sleep(0.5)

    def blinky_pos(self):
        return (self.ghosts[0].y, self.ghosts[0].x)

    def step(self):
        if self.paused or self.lives <= 0 or self.board.pellets_left == 0:
            return
        self.frames += 1
        self.try_move_pac()
        self.update_ghost_modes()
        if self.frames % 2 == 0:  # ghosts move slightly slower than pac
            for g in self.ghosts:
                g.step(self.board, (self.pac_y, self.pac_x), self.pac_dir, self.blinky_pos())
        self.check_collisions()

    def draw(self):
        stdscr = self.stdscr
        stdscr.erase()
        maxy, maxx = stdscr.getmaxyx()
        for y, row in enumerate(self.board.grid):
            if y + 1 >= maxy:
                break
            line = []
            for x, c in enumerate(row):
                if x >= maxx:
                    break
                if c == '#':
                    stdscr.addstr(y + 1, x, '#', curses.color_pair(2) | curses.A_BOLD)
                elif c == '.':
                    stdscr.addstr(y + 1, x, '.', curses.color_pair(3))
                elif c == 'o':
                    attr = curses.color_pair(4) | curses.A_BOLD
                    if self.frames % 10 < 5:
                        attr |= curses.A_BLINK
                    stdscr.addstr(y + 1, x, 'o', attr)
        # ghosts
        for g in self.ghosts:
            if g.y + 1 >= maxy or g.x >= maxx:
                continue
            if g.state == GhostState.FRIGHTENED:
                blink = self.frightened_until - self.frames < 15 and self.frames % 4 < 2
                pair = 3 if blink else 9
                ch = 'F'
            elif g.state == GhostState.EATEN:
                pair, ch = 3, ':'
            else:
                pair, ch = g.color, g.char
            try:
                stdscr.addstr(g.y + 1, g.x, ch, curses.color_pair(pair) | curses.A_BOLD)
            except curses.error:
                pass
        # pacman
        pac_glyphs = {(0, 1): '>', (0, -1): '<', (-1, 0): '^', (1, 0): 'v', (0, 0): 'C'}
        glyph = pac_glyphs.get(self.pac_dir, 'C')
        try:
            stdscr.addstr(self.pac_y + 1, self.pac_x, glyph, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

        # HUD
        hud = f" Score: {self.score:<6} Lives: {'*' * max(self.lives,0):<3} Level: {self.level} "
        try:
            stdscr.addstr(0, 0, hud[:maxx - 1], curses.color_pair(10) | curses.A_BOLD)
        except curses.error:
            pass
        footer_y = min(len(self.board.grid) + 1, maxy - 1)
        if self.paused:
            msg = " PAUSED — press P to resume "
            try:
                stdscr.addstr(footer_y, 0, msg, curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE)
            except curses.error:
                pass
        elif self.lives <= 0:
            msg = " GAME OVER — press R to restart, Q to quit "
            try:
                stdscr.addstr(footer_y, 0, msg, curses.color_pair(5) | curses.A_BOLD | curses.A_REVERSE)
            except curses.error:
                pass
        elif self.board.pellets_left == 0:
            msg = " YOU WIN — press R to restart, Q to quit "
            try:
                stdscr.addstr(footer_y, 0, msg, curses.color_pair(10) | curses.A_BOLD | curses.A_REVERSE)
            except curses.error:
                pass
        stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    game = Game(stdscr)
    tick = 0.09
    last = time.time()
    while True:
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in (ord('q'), ord('Q')):
            break
        elif key in (ord('p'), ord('P')):
            game.paused = not game.paused
        elif key in (ord('r'), ord('R')) and (game.lives <= 0 or game.board.pellets_left == 0):
            game.__init__(stdscr)
        elif key in DIRS:
            game.next_dir = DIRS[key]

        now = time.time()
        if now - last >= tick:
            last = now
            game.step()
        game.draw()
        time.sleep(0.01)


if __name__ == "__main__":
    curses.wrapper(main)
