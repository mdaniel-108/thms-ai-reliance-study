r"""Writes the 13 seeded input generators <TESTS_DIR>/gens/<n>.py (2026-11-22).
Built from the public statements' input formats and constraints only. Each generator: python3 -I <n>.py <seed>.
About 70% of seeds give small cases (correctness), the rest medium cases; none is at the maximum size, because the
check is correctness against the participants' accepted programs, not speed.
"""
from pathlib import Path

HEAD = "import random, sys\nR = random.Random(int(sys.argv[1]))\nsmall = R.random() < 0.7\n"
G = {}
G[1] = """
w = sorted(R.randint(1, 10 if small else 100) for _ in range(4))
print(*w)
"""
G[2] = """
N = R.randint(1, 50) if small else R.choice([R.randint(1, 10**6), R.randint(1, 10**12), R.randint(1, 10**18)])
print(N)
"""
G[3] = """
print(R.randint(3, 12 if small else 50), R.randint(1, 20 if small else 5000))
"""
G[4] = """
N = R.randint(1, 8 if small else 60)
E = R.randint(1, 10 if small else 80)
broken, ev = set(), []
for i in range(E):
    working = [f for f in range(1, N + 1) if f not in broken]
    if len(broken) < N - 1 and R.random() < 0.3 and i < E - 1:
        b = R.choice(working); broken.add(b); ev.append(f"1 {b}"); continue
    s = [R.choice("ox") for _ in working]
    if "o" not in s: s[R.randrange(len(s))] = "o"
    out, k = [], 0
    while k < len(s):                       # random run-length encoding as the statement allows
        j = k
        while j < len(s) and s[j] == s[k]: j += 1
        run = j - k
        while run > 0:
            m = R.randint(1, run)
            out.append((str(m) if (m > 1 or R.random() < 0.2) else "") + s[k]); run -= m
        k = j
    ev.append("2 " + "".join(out))
if not any(e.startswith("2") for e in ev):
    ev[-1] = "2 " + "o" * (N - len(broken))
print(N, len(ev), R.choice(["ON", "OFF"]))
print("\\n".join(ev))
"""
G[5] = """
N = R.randint(1, 8 if small else 20)
hi = R.choice([3, 10, 10**6]) if small else 10**6
print(N, R.randint(1, N))
print(*[R.randint(0, hi) for _ in range(N)])
"""
G[6] = """
T = R.randint(1, 5 if small else 50)
print(T)
for _ in range(T):
    n = R.randint(4, 10 if small else 300)
    hi = R.choice([5, 20, 10**5]) if small else 10**5
    print(n, *[R.randint(1, hi) for _ in range(n)])
"""
G[7] = """
import math
hi = 30 if small else 10**5
while True:
    A, B = R.randint(1, hi), R.randint(1, hi)
    if math.gcd(A, B) == 1: break
print(A, B, R.randint(1, 50 if small else 5 * 10**9))
"""
G[8] = """
N = R.randint(1, 10 if small else 2000)
al = "ab" if small and R.random() < 0.5 else "abcdefghijklmnopqrstuvwxyz"[:R.randint(1, 26)]
print(N)
print("".join(R.choice(al) for _ in range(N)))
hi = R.choice([3, 1000]) if small else 1000
print(*[R.randint(1, hi) for _ in range(N)])
print(*[R.randint(1, hi) for _ in range(N)])
"""
G[9] = """
N = R.randint(2, 6 if small else 200)
def pair():
    f1, f2 = sorted(R.sample(range(1, N + 1), 2))
    return f"{R.choice('+-')}{f1} {R.choice('+-')}{f2}"
def uniq(k):
    s = set()
    for _ in range(k * 5):
        if len(s) >= k: break
        s.add(pair())
    return sorted(s, key=lambda _: R.random())
rules = uniq(R.randint(1, 6 if small else 300))
props = uniq(R.randint(1, 8 if small else 500))
print(N, len(rules)); print("\\n".join(rules)); print(len(props)); print("\\n".join(props))
"""
G[10] = """
N = R.randint(2, 7 if small else 300)
Q = R.randint(1, 15 if small else 2000)
edges, ops = set(), []
for _ in range(Q):
    if edges and R.random() < 0.35:
        u, v = R.choice(sorted(edges)); edges.remove((u, v)); ops.append(f"2 {u} {v}")
    else:
        for _ in range(50):
            u, v = sorted(R.sample(range(1, N + 1), 2))
            if (u, v) not in edges: break
        else:
            continue
        edges.add((u, v)); ops.append(f"1 {u} {v}")
print(N, len(ops)); print("\\n".join(ops))
"""
G[11] = """
N = R.randint(1, 8 if small else 3000)
hi = R.choice([5, 100, 10**9]) if small else 10**9
print(N, R.randint(1, hi), R.randint(1, N))
print(*[R.randint(0, hi) for _ in range(N)])
"""
G[12] = """
N = R.randint(2, 8 if small else 3000)
M = R.randint(2, min(N, 5 if small else 20))
hi = R.choice([3, 1000, 10**6]) if small else 10**6
print(N, M)
for v in range(2, N + 1):
    u = R.randint(max(1, v - 3) if R.random() < 0.3 else 1, v - 1)
    print(u, v, R.randint(1, hi))
"""
G[13] = """
N = R.randint(1, 6 if small else 3000)
Q = R.randint(1, 6 if small else 3000)
hi = R.choice([10, 1000, 10**9]) if small else 10**9
print(N, Q)
for _ in range(N):
    print(R.choice("ABCD"), R.randint(0, hi), R.randint(0, hi), R.randint(0, hi))
for _ in range(Q):
    print(R.randint(0, hi), R.randint(0, hi))
"""
d = Path(__file__).parent
for n, body in G.items():
    (d / f"{n}.py").write_text(HEAD + body.lstrip("\n"), encoding="utf-8")
print("wrote", len(G))
