import random
import time
import os

WIDTH = 20
HEIGHT = 10

# محل موجود
creature_x = WIDTH // 2
creature_y = HEIGHT // 2

# دم موجود
tail = []

# غذا
food_x = random.randint(0, WIDTH - 1)
food_y = random.randint(0, HEIGHT - 1)

while food_x == creature_x and food_y == creature_y:
    food_x = random.randint(0, WIDTH - 1)
    food_y = random.randint(0, HEIGHT - 1)

while True:

    os.system("cls" if os.name == "nt" else "clear")

    # رسم نقشه
    for y in range(HEIGHT):
        for x in range(WIDTH):

            if x == creature_x and y == creature_y:
                print("C", end="")

            elif (x, y) in tail:
                print("*", end="")

            elif x == food_x and y == food_y:
                print("F", end="")

            else:
                print(".", end="")

        print()

    # ذخیره محل قبلی موجود
    tail.append((creature_x, creature_y))

    # حرکت
    if creature_x < food_x:
        creature_x += 1

    elif creature_x > food_x:
        creature_x -= 1

    elif creature_y < food_y:
        creature_y += 1

    elif creature_y > food_y:
        creature_y -= 1

    # اگر غذا خورده شد
    if creature_x == food_x and creature_y == food_y:

        print("Food Eaten!")

        food_x = random.randint(0, WIDTH - 1)
        food_y = random.randint(0, HEIGHT - 1)

        while food_x == creature_x and food_y == creature_y:
            food_x = random.randint(0, WIDTH - 1)
            food_y = random.randint(0, HEIGHT - 1)

        # چیزی حذف نمی‌کنیم، دم یک خانه بلندتر می‌شود

    else:
        # اگر غذا نخورده، طول دم ثابت بماند
        if len(tail) > 0:
            tail.pop(0)

    time.sleep(0.1)
