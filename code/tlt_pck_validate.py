r"""Input validators for the 13 PCK 2026 problems (Study 2, oracle v2 validation step 1; 2026-11-22).

One validator per problem, written from the public statement's Input section only (<STATEMENTS_DIR>/<n>.md).
Each validator parses the input strictly (line structure, token counts, integer syntax, ranges, and the statement's
structural guarantees such as distinctness, coprimality, tree connectivity or a consistent switch state) and raises
ValueError on the first violation. Run on every kept input of oracle2.json:

  python -I code/tlt_pck_validate.py [<TESTS_DIR>/oracle2.json]

Prints a per-problem count of valid / invalid inputs by kind and writes the aggregate to
results/oracle/oracle2_input_validation.json. Generated inputs only; no participant data is read.
"""
import json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from collections import Counter, defaultdict

INT = re.compile(r"-?(0|[1-9]\d*)\Z")


def lines_of(s):
    if not s.endswith("\n"):
        raise ValueError("no final newline")
    L = s[:-1].split("\n")
    for x in L:
        if x != x.strip() or "  " in x or "\t" in x or "\r" in x:
            raise ValueError("irregular whitespace")
    return L


def ints(line, k=None, lo=None, hi=None):
    t = line.split(" ")
    if k is not None and len(t) != k:
        raise ValueError(f"expected {k} tokens, got {len(t)}")
    out = []
    for x in t:
        if not INT.match(x):
            raise ValueError(f"not an integer: {x[:20]}")
        v = int(x)
        if lo is not None and v < lo or hi is not None and v > hi:
            raise ValueError(f"out of range: {v}")
        out.append(v)
    return out


def rng(v, lo, hi, name):
    if not lo <= v <= hi:
        raise ValueError(f"{name}={v} outside [{lo},{hi}]")


def nlines(L, k):
    if len(L) != k:
        raise ValueError(f"expected {k} lines, got {len(L)}")


def v1(s):
    L = lines_of(s); nlines(L, 1)
    a, b, c, d = ints(L[0], 4, 1, 100)
    if not a <= b <= c <= d:
        raise ValueError("not sorted")


def v2(s):
    L = lines_of(s); nlines(L, 1)
    (n,) = ints(L[0], 1); rng(n, 1, 10**18, "N")


def v3(s):
    L = lines_of(s); nlines(L, 1)
    n, k = ints(L[0], 2); rng(n, 3, 50, "N"); rng(k, 1, 5000, "K")


RLE = re.compile(r"([1-9]\d*)?([ox])")


def v4(s):
    L = lines_of(s)
    h = L[0].split(" ")
    if len(h) != 3 or h[2] not in ("ON", "OFF"):
        raise ValueError("bad header")
    n, e = ints(" ".join(h[:2]), 2); rng(n, 1, 1000, "N"); rng(e, 1, 1000, "E")
    nlines(L, 1 + e)
    broken, toggles = set(), 0
    for ln in L[1:]:
        t = ln.split(" ")
        if len(t) != 2:
            raise ValueError("bad event")
        if t[0] == "1":
            (b,) = ints(t[1], 1); rng(b, 1, n, "b")
            if b in broken:
                raise ValueError("floor broken twice")
            broken.add(b)
        elif t[0] == "2":
            toggles += 1
            pos, length, has_o = 0, 0, False
            for m in RLE.finditer(t[1]):
                if m.start() != pos:
                    raise ValueError("bad str")
                pos = m.end()
                c = int(m.group(1)) if m.group(1) else 1
                length += c
                has_o |= m.group(2) == "o"
            if pos != len(t[1]) or not t[1]:
                raise ValueError("bad str")
            if length != n - len(broken):
                raise ValueError("str length != working floors")
            if not has_o:
                raise ValueError("no o")
        else:
            raise ValueError("bad event type")
    if len(broken) >= n:
        raise ValueError("too many breakdowns")
    if toggles < 1:
        raise ValueError("no toggle event")


def v5(s):
    L = lines_of(s); nlines(L, 2)
    n, k = ints(L[0], 2); rng(n, 1, 20, "N"); rng(k, 1, n, "K")
    ints(L[1], n, 0, 10**6)


def v6(s):
    L = lines_of(s)
    (t,) = ints(L[0], 1); rng(t, 1, 5 * 10**4, "T")
    nlines(L, 1 + t)
    tot = 0
    for ln in L[1:]:
        x = ints(ln)
        n = x[0]; rng(n, 4, 2 * 10**5, "N")
        if len(x) != n + 1:
            raise ValueError("stick count mismatch")
        for a in x[1:]:
            rng(a, 1, 10**5, "a")
        tot += n
    if tot > 2 * 10**5:
        raise ValueError("sum N too large")


def v7(s):
    L = lines_of(s); nlines(L, 1)
    a, b, k = ints(L[0], 3); rng(a, 1, 10**5, "A"); rng(b, 1, 10**5, "B"); rng(k, 1, 5 * 10**9, "K")
    if math.gcd(a, b) != 1:
        raise ValueError("A, B not coprime")


def v8(s):
    L = lines_of(s); nlines(L, 4)
    (n,) = ints(L[0], 1); rng(n, 1, 2 * 10**5, "N")
    if len(L[1]) != n or not re.fullmatch(r"[a-z]+", L[1]):
        raise ValueError("bad S")
    ints(L[2], n, 1, 1000); ints(L[3], n, 1, 1000)


DEM = re.compile(r"([+-])([1-9]\d*)\Z")


def v9(s):
    L = lines_of(s)
    n, m = ints(L[0], 2); rng(n, 2, 2 * 10**4, "N"); rng(m, 1, 2 * 10**4, "M")
    if len(L) < m + 2:
        raise ValueError("truncated")
    (q,) = ints(L[m + 1], 1); rng(q, 1, 10**5, "Q")
    nlines(L, m + q + 2)

    def pairs(block):
        seen = set()
        for ln in block:
            t = ln.split(" ")
            if len(t) != 2:
                raise ValueError("bad demand line")
            ms = [DEM.match(x) for x in t]
            if not all(ms):
                raise ValueError("bad demand")
            f1, f2 = int(ms[0].group(2)), int(ms[1].group(2))
            rng(f1, 1, n, "f"); rng(f2, 1, n, "f")
            if not f1 < f2:
                raise ValueError("f1 >= f2")
            if ln in seen:
                raise ValueError("duplicate line")
            seen.add(ln)
    pairs(L[1:m + 1]); pairs(L[m + 2:])


def v10(s):
    L = lines_of(s)
    n, q = ints(L[0], 2); rng(n, 2, 2 * 10**5, "N"); rng(q, 1, 2 * 10**5, "Q")
    nlines(L, 1 + q)
    E = set()
    for ln in L[1:]:
        o, u, v = ints(ln, 3)
        rng(u, 1, n, "u"); rng(v, 1, n, "v")
        if not u < v:
            raise ValueError("u >= v")
        if o == 1:
            if (u, v) in E:
                raise ValueError("add existing edge")
            E.add((u, v))
        elif o == 2:
            if (u, v) not in E:
                raise ValueError("delete missing edge")
            E.remove((u, v))
        else:
            raise ValueError("bad op")


def v11(s):
    L = lines_of(s); nlines(L, 2)
    n, v, m = ints(L[0], 3); rng(n, 1, 2 * 10**5, "N"); rng(v, 1, 10**9, "V"); rng(m, 1, n, "M")
    ints(L[1], n, 0, 10**9)


def v12(s):
    L = lines_of(s)
    n, m = ints(L[0], 2); rng(n, 2, 2 * 10**5, "N"); rng(m, 2, 20, "M")
    if m > n:
        raise ValueError("M > N")
    nlines(L, n)
    par = list(range(n + 1))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for ln in L[1:]:
        a, b, c = ints(ln, 3)
        rng(a, 1, n, "a"); rng(b, 1, n, "b"); rng(c, 1, 10**6, "c")
        if not a < b:
            raise ValueError("a >= b")
        ra, rb = f(a), f(b)
        if ra == rb:
            raise ValueError("cycle (not a tree)")
        par[ra] = rb


def v13(s):
    L = lines_of(s)
    n, q = ints(L[0], 2); rng(n, 1, 2 * 10**5, "N"); rng(q, 1, 2 * 10**5, "Q")
    nlines(L, 1 + n + q)
    for ln in L[1:n + 1]:
        t = ln.split(" ", 1)
        if len(t) != 2 or t[0] not in ("A", "B", "C", "D"):
            raise ValueError("bad plant type")
        ints(t[1], 3, 0, 10**9)
    for ln in L[n + 1:]:
        ints(ln, 2, 0, 10**9)


V = {i: globals()[f"v{i}"] for i in range(1, 14)}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(cfg.TESTS_DIR, "oracle2.json")
    orc = json.load(open(src))
    agg, bad = {}, defaultdict(Counter)
    for n in range(1, 14):
        c = Counter()
        for t in orc[str(n)]["kept"]:
            try:
                V[n](t["input"]); c[(t["kind"], "valid")] += 1
            except ValueError as e:
                c[(t["kind"], "invalid")] += 1
                bad[n][f"{t['kind']}: {e}"] += 1
        agg[n] = {f"{k}_{s}": v for (k, s), v in sorted(c.items())}
        print(n, agg[n], dict(bad[n]) if bad[n] else "")
    tot = Counter()
    for a in agg.values():
        for k, v in a.items():
            tot["valid" if k.endswith("_valid") else "invalid"] += v
    out = dict(per_problem=agg, reasons={n: dict(b) for n, b in bad.items()}, total=dict(tot),
               note="Strict per-problem validators from the public statements (code/tlt_pck_validate.py); "
                    "generated inputs only.")
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(out, open(os.path.join(here, "..", "results", "oracle", "oracle2_input_validation.json"), "w"), indent=1)
    print("total", dict(tot))


if __name__ == "__main__":
    main()
