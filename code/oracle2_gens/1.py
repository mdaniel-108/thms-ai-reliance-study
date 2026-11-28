import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
w = sorted(R.randint(1, 10 if small else 100) for _ in range(4))
print(*w)
