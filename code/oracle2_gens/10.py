import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
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
print(N, len(ops)); print("\n".join(ops))
