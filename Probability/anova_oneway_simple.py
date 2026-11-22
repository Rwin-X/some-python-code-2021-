"""anova_oneway_simple.py

Simplest one-way ANOVA: compares the means of several groups.

Requirements:  pip install numpy scipy matplotlib
Run:           python anova_oneway_simple.py
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# 1. Get the data: one line of numbers per group
k = int(input("How many groups? "))
if k < 2:
    raise SystemExit("Enter at least 2 groups.")

groups = []
for g in range(1, k + 1):
    text = input(f"Values of group {g}: ").replace(",", " ")
    groups.append(np.array([float(v) for v in text.split()]))

# 2. Compute the ANOVA table by hand
all_values = np.concatenate(groups)
grand_mean = all_values.mean()
n = len(all_values)

ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)  # between groups
ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)             # inside groups
df_between, df_within = k - 1, n - k
ms_between, ms_within = ss_between / df_between, ss_within / df_within
f_value = ms_between / ms_within
p_value = stats.f.sf(f_value, df_between, df_within)

print("\nSource       df       SS       MS        F        p")
print(f"Groups   {df_between:6d} {ss_between:8.2f} {ms_between:8.2f} {f_value:8.3f} {p_value:8.4g}")
print(f"Residual {df_within:6d} {ss_within:8.2f} {ms_within:8.2f}")

if p_value < 0.05:
    print("\nSignificant difference between the groups (p < 0.05)")
else:
    print("\nNo significant difference (p >= 0.05)")

# 3. Tukey post-hoc comparisons: which pairs of groups differ?
tukey = stats.tukey_hsd(*groups)
ci = tukey.confidence_interval()
print("\nTukey comparisons (difference of means, 95% interval, adjusted p):")
for i in range(k):
    for j in range(i + 1, k):
        print(f"Group {j + 1} - Group {i + 1}: {tukey.statistic[j][i]:8.3f}"
              f"  [{ci.low[j][i]:8.3f}, {ci.high[j][i]:8.3f}]  p = {tukey.pvalue[j][i]:.4g}")

# 4. Plot: box plot of each group with the group means in red
plt.boxplot(groups)
plt.xticks(range(1, k + 1), [f"Group {g}" for g in range(1, k + 1)])
plt.plot(range(1, k + 1), [g.mean() for g in groups], "D", color="red", label="Group mean")
plt.ylabel("Value")
plt.legend()
plt.show()
