import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = [["4 1 1 1 1"], ["4 1 1 1 100000"], ["4 100000 100000 100000 100000"], ["5 1 2 3 4 5"], ["4 2 2 3 3"],
     ["6 1 1 1 1 1 1"], ["4 1 2 2 9"], ["7 9 9 1 8 3 3 3"]]
if mode == "edge":
    if k < len(E): print(len(E[k])); print("\n".join(E[k]))
elif k % 2 == 0:
    n = 200000; print(1); print(n, *[R.randint(1, 100000) for _ in range(n)])
else:
    T = 50000; print(T)
    for _ in range(T): print(4, *[R.randint(1, R.choice([5, 100000])) for _ in range(4)])
