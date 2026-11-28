import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
E = [("a", "1", "1"), ("ab", "1 1", "1 1"), ("aa", "1000 1000", "1000 1000"), ("aba", "1 2 3", "3 2 1"), ("zz", "1 1000", "1000 1")]
if mode == "edge":
    if k < len(E):
        s, l, r = E[k]; print(len(s)); print(s); print(l); print(r)
else:
    N = 200000
    al = R.choice(["a", "ab", "abcdefghijklmnopqrstuvwxyz"])
    print(N); print("".join(R.choice(al) for _ in range(N)))
    print(*[R.randint(1, 1000) for _ in range(N)]); print(*[R.randint(1, 1000) for _ in range(N)])
