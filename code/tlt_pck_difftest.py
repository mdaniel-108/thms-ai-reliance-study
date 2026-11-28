r"""Oracle check (2026-11-22): do the context-free contest-model solutions pass? (local only, nothing sent)

Oracle: the participants' Accepted programs for each problem (verdict AC in the judge dataset). For every test input,
all Accepted programs that finish are run; the input is kept only if they all print the same answer (whitespace-
normalized; numbers compared with 1e-6 tolerance). A generated program passes a problem if it matches the consensus on
every kept input within the time limit.

Inputs per problem, <TESTS_DIR>/<n>\: the statement's sample inputs (parsed from <STATEMENTS_DIR>/<n>.md)
plus, when <TESTS_DIR>/gens\<n>.py exists, 40 seeded random inputs from that generator (public statement only).

Runs inside WSL (Ubuntu-22.04: gcc 11 -std=gnu11 -O2, g++ 11 -std=gnu++17 -O2, OpenJDK):
  python code/tlt_pck_difftest.py [--gen-dir contest_gen]

Participant code is read from <JUDGE_DIR> (outside Git) and never printed or copied out.
Outputs (outside Git): <TESTS_DIR>/oracle.json (kept inputs per problem, number of agreeing AC programs) and
<WORK_DIR>/<gen-dir>/pass.csv (key, problem, language, compiles, passed, failed_input_kind). Aggregates only go into Git.
"""
import argparse, csv, json, os, re, subprocess, sys, tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

PROJ = cfg.JUDGE_DIR
STM = cfg.STATEMENTS_DIR
TESTS = cfg.TESTS_DIR
PID = {795 + i: i + 1 for i in range(13)}           # judge problem id -> statement number
TL = 6.0                                            # seconds per run (generous; the check is correctness, not speed)
EXT = {"c": "C", "cpp": "C++", "java": "Java"}


def samples(n):
    t = open(f"{STM}/{n}.md", encoding="utf-8").read()
    return [m.group(1) for m in re.finditer(r"###\s*Sample Input[^\n]*\n+```[^\n]*\n(.*?)```", t, re.S)]


def build(src, lang, d):
    if lang == "Java":
        m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)", src)
        cls = m.group(1) if m else "Main"
        open(os.path.join(d, cls + ".java"), "w").write(src)
        r = subprocess.run(["javac", "-nowarn", "-d", d, os.path.join(d, cls + ".java")], capture_output=True, timeout=120)
        return (["java", "-Xss256m", "-cp", d, cls] if r.returncode == 0 else None)
    fn = os.path.join(d, "a.c" if lang == "C" else "a.cpp")
    open(fn, "w").write(src)
    cc = ["gcc", "-std=gnu11"] if lang == "C" else ["g++", "-std=gnu++17"]
    r = subprocess.run(cc + ["-O2", "-w", fn, "-o", os.path.join(d, "a.out"), "-lm"], capture_output=True, timeout=120)
    return [os.path.join(d, "a.out")] if r.returncode == 0 else None


def run(cmd, inp):
    try:
        r = subprocess.run(cmd, input=inp.encode(), capture_output=True, timeout=TL)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None


def same(a, b):
    x, y = a.split(), b.split()
    if len(x) != len(y):
        return False
    for p, q in zip(x, y):
        if p == q:
            continue
        try:
            if abs(float(p) - float(q)) > 1e-6 * max(1.0, abs(float(q))):
                return False
        except ValueError:
            return False
    return True


def inputs(n):
    L = [("sample", s) for s in samples(n)]
    g = f"{TESTS}/gens/{n}.py"
    if os.path.exists(g):
        for k in range(40):
            r = subprocess.run(["python3", "-I", g, str(6500 + k)], capture_output=True, timeout=60)
            if r.returncode == 0 and r.stdout:
                L.append(("random", r.stdout.decode()))
    return L


def oracle(n, rows):
    acc = [r for r in rows if r["verdict"] == "AC" and PID.get(int(r["problem_id"])) == n]
    ins = inputs(n)
    outs = [[] for _ in ins]
    with tempfile.TemporaryDirectory() as root:
        for i, r in enumerate(acc):
            src = open(os.path.join(PROJ, r["code_path"]), encoding="utf-8", errors="replace").read()
            d = os.path.join(root, str(i)); os.makedirs(d)
            cmd = build(src, r["language"], d)
            if not cmd:
                continue
            for j, (_, s) in enumerate(ins):
                o = run(cmd, s)
                if o is not None:
                    outs[j].append(o)
    kept = []
    for (kind, s), os_ in zip(ins, outs):
        if len(os_) >= 3 and all(same(o, os_[0]) for o in os_):
            kept.append({"kind": kind, "input": s, "expected": os_[0], "agreeing": len(os_)})
    return {"n_accepted": len(acc), "n_inputs": len(ins), "kept": kept}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-dir", default="contest_gen")
    ap.add_argument("--rebuild-oracle", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig")))
    of = f"{TESTS}/oracle.json"
    os.makedirs(TESTS, exist_ok=True)
    if a.rebuild_oracle or not os.path.exists(of):
        with ThreadPoolExecutor(4) as ex:
            orc = dict(zip(range(1, 14), ex.map(lambda n: oracle(n, rows), range(1, 14))))
        json.dump(orc, open(of, "w"), indent=0)
    orc = {int(k): v for k, v in json.load(open(of)).items()}
    for n, v in orc.items():
        print(f"problem {n}: {len(v['kept'])}/{v['n_inputs']} inputs kept, {v['n_accepted']} accepted programs")
    G = os.path.join(cfg.WORK_DIR, a.gen_dir)
    res = []
    for key in sorted(os.listdir(G)):
        if not os.path.isdir(os.path.join(G, key)):
            continue
        for fn in sorted(os.listdir(os.path.join(G, key))):
            m = re.match(r"(\d+)_(c|cpp|java)\.", fn)
            if not m:
                continue
            n, lang = int(m.group(1)), EXT[m.group(2)]
            n = PID.get(n, n)                       # files may be named by judge id (795..807)
            src = open(os.path.join(G, key, fn), encoding="utf-8", errors="replace").read()
            kept = orc[n]["kept"]
            with tempfile.TemporaryDirectory() as d:
                cmd = build(src, lang, d)
                fail = None
                if cmd and kept:
                    for t in kept:
                        o = run(cmd, t["input"])
                        if o is None or not same(o, t["expected"]):
                            fail = t["kind"]; break
            res.append(dict(key=key, problem=n, language=lang, compiles=bool(cmd), n_tests=len(kept),
                            passed=bool(cmd) and bool(kept) and fail is None, failed_input_kind=fail or ""))
    with open(f"{G}/pass.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0]) if res else ["key"]); w.writeheader(); w.writerows(res)
    c = Counter((r["key"], r["passed"]) for r in res)
    for key in sorted({r["key"] for r in res}):
        print(key, "passed", c[(key, True)], "of", c[(key, True)] + c[(key, False)])


if __name__ == "__main__":
    main()
