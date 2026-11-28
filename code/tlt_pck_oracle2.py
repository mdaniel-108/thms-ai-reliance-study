r"""Oracle v2 for the PCK problems (2026-11-22): adds edge-case and maximum-size inputs with time limits.

  python code/tlt_pck_oracle2.py [build|score|both]

build: start from oracle.json (samples + 40 random inputs, kept where all Accepted programs agree), add the edge cases
       (gens/<n>x.py edge k) and four maximum-size inputs (gens/<n>x.py large k). Every Accepted program is run on every
       new input; an input is kept when at least 3 Accepted programs finish and all agree. Large inputs get a time limit
       of max(1 s, 2 x the slowest Accepted runtime on that input); other inputs keep the 6 s correctness limit.
       Output (outside Git): <TESTS_DIR>/oracle2.json.
score: run every logged submission on every kept input; private per-submission table
       <AUDIT_DIR>/oracle2_scores.csv; aggregate comparison with the judge printed and written to
       results/oracle/oracle_validation.json.
Participant code is read locally and never printed or copied out.
"""
import csv, json, os, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

TESTS, PROJ = d.TESTS, d.PROJ
OUT2 = f"{TESTS}/oracle2.json"
PRIV = os.path.join(cfg.AUDIT_DIR, "oracle2_scores.csv")
AGG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "oracle", "oracle_validation.json")
CAP = 20.0


def timed(cmd, inp, tl):
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, input=inp.encode(), capture_output=True, timeout=tl)
    except subprocess.TimeoutExpired:
        return None, tl
    dt = time.perf_counter() - t0
    return (r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None), dt


def gen(n, mode, k):
    r = subprocess.run(["python3", "-I", f"{TESTS}/gens/{n}x.py", mode, str(k)], capture_output=True, timeout=120)
    return r.stdout.decode() if r.returncode == 0 else ""


def build_problem(n, rows, base):
    acc = [r for r in rows if r["verdict"] == "AC" and d.PID.get(int(r["problem_id"])) == n]
    new = [("edge", s) for k in range(40) if (s := gen(n, "edge", k))] + [("large", gen(n, "large", k)) for k in range(4)]
    outs = [[] for _ in new]
    with tempfile.TemporaryDirectory() as root:
        for i, r in enumerate(acc):
            src = open(os.path.join(PROJ, r["code_path"]), encoding="utf-8", errors="replace").read()
            dd = os.path.join(root, str(i)); os.makedirs(dd)
            cmd = d.build(src, r["language"], dd)
            if not cmd:
                continue
            for j, (_, s) in enumerate(new):
                o, dt = timed(cmd, s, CAP)
                if o is not None:
                    outs[j].append((o, dt))
    kept = [dict(t, tl=d.TL) for t in base["kept"]]
    dropped = Counter()
    for (kind, s), os_ in zip(new, outs):
        if len(os_) >= 3 and all(d.same(o, os_[0][0]) for o, _ in os_):
            tl = max(1.0, 2.0 * max(dt for _, dt in os_)) if kind == "large" else d.TL
            kept.append(dict(kind=kind, input=s, expected=os_[0][0], agreeing=len(os_), tl=round(tl, 2)))
        else:
            dropped[kind] += 1
    return dict(n_accepted=len(acc), kept=kept, new_dropped=dict(dropped))


def build():
    rows = list(csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig")))
    base = {int(k): v for k, v in json.load(open(f"{TESTS}/oracle.json")).items()}
    res = {}
    for n in range(1, 14):                       # sequential, so the timings are not distorted by parallel load
        res[n] = build_problem(n, rows, base[n])
        c = Counter(t["kind"] for t in res[n]["kept"])
        print(f"problem {n}: kept {dict(c)}, new inputs dropped {res[n]['new_dropped']}", flush=True)
    json.dump(res, open(OUT2, "w"), indent=0)


def score():
    orc = {int(k): v for k, v in json.load(open(OUT2)).items()}
    rows = list(csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig")))

    def one(r):
        n = d.PID.get(int(r["problem_id"]))
        kept = orc[n]["kept"]
        src = open(os.path.join(PROJ, r["code_path"]), encoding="utf-8", errors="replace").read()
        res = dict(submission_id=r["submission_id"], problem=n, verdict=r["verdict"], compiles=0)
        with tempfile.TemporaryDirectory() as td:
            cmd = d.build(src, r["language"], td)
            if not cmd:
                return res
            res["compiles"] = 1
            by = defaultdict(lambda: [0, 0])
            slow = 0
            for t in kept:
                o, dt = timed(cmd, t["input"], t["tl"])
                ok = o is not None and d.same(o, t["expected"])
                if t["kind"] == "large" and o is None and dt >= t["tl"]:
                    slow += 1
                by[t["kind"]][0] += ok
                by[t["kind"]][1] += 1
        for k in ("sample", "random", "edge", "large"):
            res[f"{k}_passed"], res[f"{k}_n"] = by[k]
        res["large_timeouts"] = slow
        return res

    with ThreadPoolExecutor(2) as ex:
        out = list(ex.map(one, rows))
    cols = ["submission_id", "problem", "verdict", "compiles"] + [f"{k}_{x}" for k in ("sample", "random", "edge", "large") for x in ("passed", "n")] + ["large_timeouts"]
    with open(PRIV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval=0); w.writeheader(); w.writerows(out)
    agg = {}
    for label, kinds in (("v1_correctness", ("sample", "random")), ("v2_full", ("sample", "random", "edge", "large"))):
        tab = defaultdict(Counter)
        for r in out:
            if not r["compiles"]:
                tab[r["verdict"]]["compile_fail"] += 1
                continue
            ok = all(r[f"{k}_passed"] == r[f"{k}_n"] for k in kinds)
            tab[r["verdict"]]["oracle_pass" if ok else "oracle_fail"] += 1
        agg[label] = {v: dict(c) for v, c in tab.items()}
    wa = [r for r in out if r["verdict"] == "WA" and r["compiles"]]
    agg["wa_caught_by_new_inputs"] = sum(1 for r in wa if r["sample_passed"] == r["sample_n"] and r["random_passed"] == r["random_n"]
                                         and not (r["edge_passed"] == r["edge_n"] and r["large_passed"] == r["large_n"]))
    agg["tle_with_large_timeout"] = sum(1 for r in out if r["verdict"] == "TLE" and r.get("large_timeouts", 0) > 0)
    agg["inputs_per_problem"] = {n: dict(Counter(t["kind"] for t in v["kept"])) for n, v in orc.items()}
    agg["note"] = ("Oracle v2: samples, 40 random, edge cases and 4 maximum-size inputs per problem, kept where >=3 Accepted programs "
                   "agree; large inputs timed at max(1 s, 2x slowest Accepted runtime). Accepted programs pass by construction on "
                   "untimed inputs. Aggregates only.")
    json.dump(agg, open(AGG, "w"), indent=1)
    print(json.dumps({k: v for k, v in agg.items() if k != "inputs_per_problem"}, indent=1))


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "both"
    if m in ("build", "both"):
        build()
    if m in ("score", "both"):
        score()
