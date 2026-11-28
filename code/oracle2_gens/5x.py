import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = [("1 1", "0"), ("1 1", "5"), ("2 1", "0 0"), ("2 2", "3 3"), ("3 2", "1 2 3"), ("20 20", " ".join(["1000000"] * 20)),
     ("20 1", " ".join(str(2 ** i) for i in range(20))), ("20 10", " ".join(["0"] * 20)), ("4 3", "1 1 2 4")]
if mode == "edge":
    if k < len(E): print(E[k][0]); print(E[k][1])
else:
    N = 20
    hi = R.choice([10**6, 50, 3])
    print(N, R.randint(1, N)); print(*[R.randint(0, hi) for _ in range(N)])
