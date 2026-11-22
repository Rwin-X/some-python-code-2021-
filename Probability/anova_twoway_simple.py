"""anova_twoway_simple.py

Simplest two-way ANOVA with interaction: factors A and B, one numeric outcome.
Every combination of A and B must have the same number of values
(for unequal sizes use anova_gui.py).

Requirements:  pip install numpy scipy matplotlib
Run:           python anova_twoway_simple.py
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# 1. Get the data: one line of numbers for every combination of A and B
na = int(input("Number of levels of factor A? "))
nb = int(input("Number of levels of factor B? "))
if na < 2 or nb < 2:
    raise SystemExit("Each factor needs at least 2 levels.")

cells = []
for i in range(1, na + 1):
    row = []
    for j in range(1, nb + 1):
        text = input(f"Values for A{i} and B{j}: ").replace(",", " ")
        row.append([float(v) for v in text.split()])
    cells.append(row)

if len({len(values) for row in cells for values in row}) != 1:
    raise SystemExit("Every combination needs the same number of values.")
data = np.array(cells)          # shape: (levels of A, levels of B, values per cell)
n = data.shape[2]
if n < 2:
    raise SystemExit("Each combination needs at least 2 values.")

# 2. Split the variation into A, B, their interaction and the error
grand_mean = data.mean()
a_means = data.mean(axis=(1, 2))
b_means = data.mean(axis=(0, 2))
cell_means = data.mean(axis=2)

ss_a = nb * n * ((a_means - grand_mean) ** 2).sum()
ss_b = na * n * ((b_means - grand_mean) ** 2).sum()
ss_ab = n * ((cell_means - a_means[:, None] - b_means[None, :] + grand_mean) ** 2).sum()
ss_error = ((data - cell_means[:, :, None]) ** 2).sum()

df_a, df_b, df_ab = na - 1, nb - 1, (na - 1) * (nb - 1)
df_error = na * nb * (n - 1)
ms_error = ss_error / df_error

print("\nSource     df        SS        MS         F         p")
for name, ss, df in (("A", ss_a, df_a), ("B", ss_b, df_b), ("A:B", ss_ab, df_ab)):
    f_value = (ss / df) / ms_error
    p_value = stats.f.sf(f_value, df, df_error)
    print(f"{name:<8}{df:4d} {ss:9.2f} {ss / df:9.2f} {f_value:9.3f} {p_value:9.4g}")
print(f"Residual{df_error:4d} {ss_error:9.2f} {ms_error:9.2f}")

# 3. Plot: mean of every combination (parallel lines = no interaction)
for j in range(nb):
    plt.plot(range(1, na + 1), cell_means[:, j], marker="o", linewidth=2, label=f"B{j + 1}")
plt.xticks(range(1, na + 1), [f"A{i}" for i in range(1, na + 1)])
plt.xlabel("Factor A")
plt.ylabel("Mean of value")
plt.legend(title="Factor B")
plt.show()
