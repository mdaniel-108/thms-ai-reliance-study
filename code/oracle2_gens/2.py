import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
N = R.randint(1, 50) if small else R.choice([R.randint(1, 10**6), R.randint(1, 10**12), R.randint(1, 10**18)])
print(N)
