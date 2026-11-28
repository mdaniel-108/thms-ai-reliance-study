import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(1, 8 if small else 3000)
hi = R.choice([5, 100, 10**9]) if small else 10**9
print(N, R.randint(1, hi), R.randint(1, N))
print(*[R.randint(0, hi) for _ in range(N)])
