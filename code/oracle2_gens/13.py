import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(1, 6 if small else 3000)
Q = R.randint(1, 6 if small else 3000)
hi = R.choice([10, 1000, 10**9]) if small else 10**9
print(N, Q)
for _ in range(N):
    print(R.choice("ABCD"), R.randint(0, hi), R.randint(0, hi), R.randint(0, hi))
for _ in range(Q):
    print(R.randint(0, hi), R.randint(0, hi))
