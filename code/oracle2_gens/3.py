import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
print(R.randint(3, 12 if small else 50), R.randint(1, 20 if small else 5000))
