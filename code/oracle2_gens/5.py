import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(1, 8 if small else 20)
hi = R.choice([3, 10, 10**6]) if small else 10**6
print(N, R.randint(1, N))
print(*[R.randint(0, hi) for _ in range(N)])
