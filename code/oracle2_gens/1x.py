import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = ["1 1 1 1", "100 100 100 100", "1 1 1 100", "1 1 100 100", "1 2 3 4", "1 50 50 100", "99 100 100 100", "1 1 2 100"]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(*sorted(R.randint(1, 100) for _ in range(4)))
