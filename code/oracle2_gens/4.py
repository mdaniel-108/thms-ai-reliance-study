import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
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
print("\n".join(ev))
