import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(1, 10 if small else 2000)
al = "ab" if small and R.random() < 0.5 else "abcdefghijklmnopqrstuvwxyz"[:R.randint(1, 26)]
print(N)
print("".join(R.choice(al) for _ in range(N)))
hi = R.choice([3, 1000]) if small else 1000
print(*[R.randint(1, hi) for _ in range(N)])
print(*[R.randint(1, hi) for _ in range(N)])
