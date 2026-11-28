import random, sys
mode, k = sys.argv[1], int(sys.argv[2])
R = random.Random(7700 + k)
def emit(N, ops):
    print(N, len(ops)); print("\n".join(ops))
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
