import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
T = R.randint(1, 5 if small else 50)
print(T)
for _ in range(T):
    n = R.randint(4, 10 if small else 300)
    hi = R.choice([5, 20, 10**5]) if small else 10**5
    print(n, *[R.randint(1, hi) for _ in range(n)])
