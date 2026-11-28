import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
if mode == "edge":
    E = [(2, 2, [(1, 2, 1)]), (2, 2, [(1, 2, 1000000)]), (3, 3, [(1, 2, 1), (2, 3, 1)]), (4, 2, [(1, 2, 5), (1, 3, 1), (1, 4, 1)])]
    if k < len(E):
        N, M, ed = E[k]; print(N, M)
        for a, b, c in ed: print(a, b, c)
else:
    N, M = 200000, 20
    print(N, M)
    shape = k % 3                                   # 0 path (deep), 1 random, 2 star
    for v in range(2, N + 1):
        u = v - 1 if shape == 0 else (R.randint(1, v - 1) if shape == 1 else 1)
        print(u, v, R.randint(1, 10**6))
