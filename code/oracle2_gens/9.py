import random, sys
R = random.Random(int(sys.argv[1]))
small = R.random() < 0.7
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
print(N, len(rules)); print("\n".join(rules)); print(len(props)); print("\n".join(props))
