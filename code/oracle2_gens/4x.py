import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
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
        h, ev = E[k]; print(h); print("\n".join(ev))
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
    print(N, len(ev), R.choice(["ON", "OFF"])); print("\n".join(ev))
