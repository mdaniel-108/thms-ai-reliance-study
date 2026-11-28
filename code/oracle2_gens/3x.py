import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = ["3 1", "3 5000", "4 1", "4 5000", "50 1", "50 5000", "6 5000", "12 5000", "49 4999"]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(R.randint(3, 50), 5000)
