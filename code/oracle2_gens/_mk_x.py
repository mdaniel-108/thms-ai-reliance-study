r"""Writes <TESTS_DIR>/gens/<n>x.py: edge-case and maximum-size inputs for the 13 problems (2026-11-22, oracle v2).
Built from the public statements' constraints only. Call: python3 -I <n>x.py <mode> <k>, mode "edge" (k-th case of a
fixed list; prints nothing when k is past the end) or "large" (k-th random maximum-size case, seed 7700 + k).
"""
from pathlib import Path

HEAD = "import random, sys\nmode, k = sys.argv[1], int(sys.argv[2])\nR = random.Random(7700 + k)\n"
G = {}
G[1] = """
E = ["1 1 1 1", "100 100 100 100", "1 1 1 100", "1 1 100 100", "1 2 3 4", "1 50 50 100", "99 100 100 100", "1 1 2 100"]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(*sorted(R.randint(1, 100) for _ in range(4)))
"""
G[2] = """
E = [1, 9, 10, 11, 99, 100, 10**18, 10**18 - 1, 999999999999999999, 123456789012345678, 4, 16, 37, 58, 89]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(R.randint(10**17, 10**18))
"""
G[3] = """
E = ["3 1", "3 5000", "4 1", "4 5000", "50 1", "50 5000", "6 5000", "12 5000", "49 4999"]
if mode == "edge":
    if k < len(E): print(E[k])
else:
    print(R.randint(3, 50), 5000)
"""
G[4] = """
def rle(s):
    out, i = [], 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]: j += 1
        n = j - i
        out.append((str(n) if n > 1 else "") + s[i]); i = j
    return "".join(out)
if mode == "edge":
    E = [("1 1 ON", ["2 o"]), ("1 1 OFF", ["2 o"]), ("2 2 OFF", ["1 1", "2 o"]),
         ("1000 1 OFF", ["2 " + rle("o" * 1000)]), ("1000 1 ON", ["2 " + "o" * 1000]),
         ("3 3 OFF", ["1 2", "1 1", "2 o"]), ("5 2 ON", ["2 1o1x1o1x1o", "2 5o"])]
    if k < len(E):
        h, ev = E[k]; print(h); print("\\n".join(ev))
else:
    N, E = 1000, 1000
    broken, ev = set(), []
    for i in range(E):
        working = [f for f in range(1, N + 1) if f not in broken]
        if len(broken) < N - 1 and R.random() < 0.2 and i < E - 1:
            b = R.choice(working); broken.add(b); ev.append(f"1 {b}"); continue
        s = [R.choice("ox") for _ in working]
        if "o" not in s: s[0] = "o"
        ev.append("2 " + (rle("".join(s)) if R.random() < 0.5 else "".join(s)))
    print(N, len(ev), R.choice(["ON", "OFF"])); print("\\n".join(ev))
"""
G[5] = """
E = [("1 1", "0"), ("1 1", "5"), ("2 1", "0 0"), ("2 2", "3 3"), ("3 2", "1 2 3"), ("20 20", " ".join(["1000000"] * 20)),
     ("20 1", " ".join(str(2 ** i) for i in range(20))), ("20 10", " ".join(["0"] * 20)), ("4 3", "1 1 2 4")]
if mode == "edge":
    if k < len(E): print(E[k][0]); print(E[k][1])
else:
    N = 20
    hi = R.choice([10**6, 50, 3])
    print(N, R.randint(1, N)); print(*[R.randint(0, hi) for _ in range(N)])
"""
G[6] = """
E = [["4 1 1 1 1"], ["4 1 1 1 100000"], ["4 100000 100000 100000 100000"], ["5 1 2 3 4 5"], ["4 2 2 3 3"],
     ["6 1 1 1 1 1 1"], ["4 1 2 2 9"], ["7 9 9 1 8 3 3 3"]]
if mode == "edge":
    if k < len(E): print(len(E[k])); print("\\n".join(E[k]))
elif k % 2 == 0:
    n = 200000; print(1); print(n, *[R.randint(1, 100000) for _ in range(n)])
else:
    T = 50000; print(T)
    for _ in range(T): print(4, *[R.randint(1, R.choice([5, 100000])) for _ in range(4)])
"""
G[7] = """
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
"""
G[8] = """
E = [("a", "1", "1"), ("ab", "1 1", "1 1"), ("aa", "1000 1000", "1000 1000"), ("aba", "1 2 3", "3 2 1"), ("zz", "1 1000", "1000 1")]
if mode == "edge":
    if k < len(E):
        s, l, r = E[k]; print(len(s)); print(s); print(l); print(r)
else:
    N = 200000
    al = R.choice(["a", "ab", "abcdefghijklmnopqrstuvwxyz"])
    print(N); print("".join(R.choice(al) for _ in range(N)))
    print(*[R.randint(1, 1000) for _ in range(N)]); print(*[R.randint(1, 1000) for _ in range(N)])
"""
G[9] = """
def emit(N, rules, props):
    print(N, len(rules)); print("\\n".join(rules)); print(len(props)); print("\\n".join(props))
if mode == "edge":
    E = [(2, ["+1 +2"], ["+1 +2"]), (2, ["+1 +2", "-1 -2"], ["+1 -2", "-1 +2", "+1 +2"]),
         (2, ["+1 +2", "+1 -2", "-1 +2", "-1 -2"], ["+1 +2"]), (3, ["+1 +2", "-1 +3", "-2 -3"], ["+1 +3", "-1 -2", "+2 +3"])]
    if k < len(E): emit(*E[k])
else:
    N = 20000
    def pairs(m):
        s = set()
        while len(s) < m:
            f1, f2 = sorted(R.sample(range(1, N + 1), 2))
            s.add(f"{R.choice('+-')}{f1} {R.choice('+-')}{f2}")
        return list(s)
    emit(N, pairs(R.choice([20000, 5000])), pairs(100000))
"""
G[10] = """
def emit(N, ops):
    print(N, len(ops)); print("\\n".join(ops))
if mode == "edge":
    E = [(2, ["1 1 2"]), (3, ["1 1 2", "1 2 3", "1 1 3"]), (3, ["1 1 2", "1 2 3", "1 1 3", "2 1 3", "1 1 3"]),
         (4, ["1 1 2", "1 1 3", "1 1 4", "1 2 3", "1 2 4", "1 3 4", "2 1 2"])]
    if k < len(E): emit(*E[k])
else:
    N, Q = 200000, 200000
    hub = R.choice([600, 3000, 200000])          # dense core makes many trios
    edges, ops = set(), []
    while len(ops) < Q:
        if edges and R.random() < 0.3:
            e = edges.pop(); ops.append(f"2 {e[0]} {e[1]}")
        else:
            u, v = sorted(R.sample(range(1, hub + 1), 2))
            if (u, v) in edges: continue
            edges.add((u, v)); ops.append(f"1 {u} {v}")
    emit(N, ops)
"""
G[11] = """
E = [("1 1 1", "0"), ("1 1 1", "5"), ("3 2 1", "2 2 2"), ("3 2 3", "1 1 1"), ("5 1000000000 2", "0 0 0 0 0"),
     ("4 3 2", "3 6 3 6"), ("2 5 2", "5 5")]
if mode == "edge":
    if k < len(E): print(E[k][0]); print(E[k][1])
else:
    N = 200000
    V = R.choice([1, 2, 1000, 10**9]); M = R.choice([1, 2, 1000, N])
    print(N, V, M); print(*[R.randint(0, R.choice([10, 10**9])) for _ in range(N)])
"""
G[12] = """
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
"""
G[13] = """
if mode == "edge":
    E = [(["A 0 0 0"], ["0 0"]), (["A 0 0 0"], ["1000000000 1000000000"]), (["D 1000000000 0 1000000000"], ["1000000000 0", "0 1000000000"]),
         (["A 5 5 0", "B 5 5 0", "C 5 5 0", "D 5 5 0"], ["5 5", "6 5", "4 5"]), (["C 10 10 1000000000"], ["0 0", "10 10"])]
    if k < len(E):
        pl, qs = E[k]; print(len(pl), len(qs)); print("\\n".join(pl)); print("\\n".join(qs))
else:
    N = Q = 200000
    hi = R.choice([1000, 10**9])
    print(N, Q)
    print("\\n".join(f"{R.choice('ABCD')} {R.randint(0, hi)} {R.randint(0, hi)} {R.randint(0, hi)}" for _ in range(N)))
    print("\\n".join(f"{R.randint(0, hi)} {R.randint(0, hi)}" for _ in range(Q)))
"""
d = Path(__file__).parent
for n, body in G.items():
    (d / f"{n}x.py").write_text(HEAD + body.lstrip("\n"), encoding="utf-8")
print("wrote", len(G))
