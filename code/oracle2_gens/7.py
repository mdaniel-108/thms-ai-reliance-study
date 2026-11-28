import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
import math
hi = 30 if small else 10**5
while True:
    A, B = R.randint(1, hi), R.randint(1, hi)
    if math.gcd(A, B) == 1: break
print(A, B, R.randint(1, 50 if small else 5 * 10**9))
