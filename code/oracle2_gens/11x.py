import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = [("1 1 1", "0"), ("1 1 1", "5"), ("3 2 1", "2 2 2"), ("3 2 3", "1 1 1"), ("5 1000000000 2", "0 0 0 0 0"),
     ("4 3 2", "3 6 3 6"), ("2 5 2", "5 5")]
if mode == "edge":
    if k < len(E): print(E[k][0]); print(E[k][1])
else:
    N = 200000
    V = R.choice([1, 2, 1000, 10**9]); M = R.choice([1, 2, 1000, N])
    print(N, V, M); print(*[R.randint(0, R.choice([10, 10**9])) for _ in range(N)])
