import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
if mode == "edge":
    E = [(["A 0 0 0"], ["0 0"]), (["A 0 0 0"], ["1000000000 1000000000"]), (["D 1000000000 0 1000000000"], ["1000000000 0", "0 1000000000"]),
         (["A 5 5 0", "B 5 5 0", "C 5 5 0", "D 5 5 0"], ["5 5", "6 5", "4 5"]), (["C 10 10 1000000000"], ["0 0", "10 10"])]
    if k < len(E):
        pl, qs = E[k]; print(len(pl), len(qs)); print("\n".join(pl)); print("\n".join(qs))
else:
    N = Q = 200000
    hi = R.choice([1000, 10**9])
    print(N, Q)
    print("\n".join(f"{R.choice('ABCD')} {R.randint(0, hi)} {R.randint(0, hi)} {R.randint(0, hi)}" for _ in range(N)))
    print("\n".join(f"{R.randint(0, hi)} {R.randint(0, hi)}" for _ in range(Q)))
