import os
import time

WIDTH = 40
HEIGHT = 10

fish_x = 5
fish_y = HEIGHT // 2
direction = 1


while True:
    os.system("cls" if os.name == "nt" else "clear")

    # سقف
    print("+" + "-" * WIDTH + "+")

    # داخل آکواریوم
    for y in range(HEIGHT):
        print("|", end="")

        for x in range(WIDTH):
            if x == fish_x and y == fish_y:
                if direction == 1:
                    print("><>", end="")
                else:
                    print("<><", end="")
                # چون ماهی 3 کاراکتر است
                for _ in range(2):
                    next
                break
            else:
                print(" ", end="")

        # پر کردن بقیه خط
        current = fish_x + 3 if y == fish_y else 0
        while current < WIDTH:
            print(" ", end="")
            current += 1

        print("|")

    # کف
    print("+" + "-" * WIDTH + "+")

    # حرکت
    fish_x += direction

    if fish_x >= WIDTH - 3:
        direction = -1

    if fish_x <= 0:
        direction = 1

    time.sleep(0.08)
