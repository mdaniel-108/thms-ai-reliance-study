import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(2, 8 if small else 3000)
M = R.randint(2, min(N, 5 if small else 20))
hi = R.choice([3, 1000, 10**6]) if small else 10**6
print(N, M)
for v in range(2, N + 1):
    u = R.randint(max(1, v - 3) if R.random() < 0.3 else 1, v - 1)
    print(u, v, R.randint(1, hi))
