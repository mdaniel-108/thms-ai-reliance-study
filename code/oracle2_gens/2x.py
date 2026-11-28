import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = [1, 9, 10, 11, 99, 100, 10**18, 10**18 - 1, 999999999999999999, 123456789012345678, 4, 16, 37, 58, 89]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(R.randint(10**17, 10**18))
