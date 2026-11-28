import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
def emit(N, rules, props):
    print(N, len(rules)); print("\n".join(rules)); print(len(props)); print("\n".join(props))
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
