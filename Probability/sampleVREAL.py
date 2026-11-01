import math
from statistics import NormalDist

# Formulas
# z = critical value, d = margin of error, N = population size, q = 1 - p
#
# 1) Quantitative variable, large population:
#        n = (z * s / d) ^ 2
#
# 2) Quantitative variable, finite population:
#        n = N * z^2 * variance / (d^2 * (N - 1) + z^2 * variance)
#        (variance = s^2, so in this case you enter the variance, not s)
#
# 3) Two-valued variable, large population:
#        n = z^2 * p * q / d^2
#
# 4) Two-valued variable, finite population:
#        n = N * z^2 * p * q / (d^2 * (N - 1) + z^2 * p * q)

print("Sample Size Calculator")
print("1. Quantitative variable - large population")
print("2. Quantitative variable - finite population")
print("3. Two-valued variable   - large population")
print("4. Two-valued variable   - finite population")

choice = input("Which one do you want (1-4)? ")

confidence = float(input("Confidence level in % (95): "))
z = NormalDist().inv_cdf(1 - (1 - confidence / 100) / 2)

if choice == "1":
    s = float(input("Standard deviation (s): "))
    d = float(input("Margin of error: "))
    v = s ** 2          # variance
elif choice == "2":
    variance = float(input("Variance (s^2): "))
    d = float(input("Margin of error: "))
    v = variance
else:
    p = float(input("Proportion p (0.5 by default): "))
    d = float(input("Margin of error (0.05): "))
    v = p * (1 - p)     # p * q

if choice == "1" or choice == "3":
    n = z ** 2 * v / d ** 2
else:
    N = float(input("Population size N: "))
    n = N * z ** 2 * v / (d ** 2 * (N - 1) + z ** 2 * v)

print("Sample size =", math.ceil(n))
