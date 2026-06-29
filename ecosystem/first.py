import random
import time
import os

WIDTH = 20
HEIGHT = 10


def spawn_food(creature):
    while True:
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        if (x, y) != creature:
            return (x, y)


creature = (WIDTH // 2, HEIGHT // 2) #--(1,19)/(3,14)
food = spawn_food(creature)

while True:
    os.system("cls" if os.name == "nt" else "clear")

    # رسم نقشه
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x, y) == creature:
                print("C", end="")
            elif (x, y) == food:
                print("F", end="")
            else:
                print(".", end="")
        print()

    # حرکت موجود به سمت غذا
    cx, cy = creature
    fx, fy = food

    if cx < fx:
        cx += 1
    elif cx > fx:
        cx -= 1
    elif cy < fy:
        cy += 1
    elif cy > fy:
        cy -= 1

    creature = (cx, cy)

    # اگر غذا خورده شد
    if creature == food:
        print("\nFood eaten!")
        food = spawn_food(creature)

    time.sleep(0.10)
