import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = ["1 1 1", "1 2 1", "2 3 1", "2 3 2", "100000 99999 1", "100000 99999 5000000000", "99999 100000 4999850001",
     "99999 100000 4999850000", "1 100000 1", "3 7 6", "4 7 9"]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    import math
    while True:
        A, B = R.randint(50000, 100000), R.randint(50000, 100000)
        if math.gcd(A, B) == 1: break
    print(A, B, R.randint(1, 5 * 10**9))
