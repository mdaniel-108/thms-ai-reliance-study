r"""Oracle v2 validation and freeze (Study 2; 2026-11-22). Local only; nothing is sent anywhere.

  python code/tlt_pck_oracle2_freeze.py [runs|score|analyse|all]

Settings fixed before any scoring (from the statements and the toolchain, not from failing programs):
- Candidate inputs per problem: statement samples, 40 random (gens/<n>.py, seeds 6500-6539), edge cases (gens/<n>x.py edge k)
  and 4 maximum-size inputs (gens/<n>x.py large k). Every candidate is checked by code/tlt_pck_validate.py.
- Comparator: whitespace-separated tokens; integers exact; problem 6 (areas) absolute error <= 1e-3 as its statement says;
  other non-integer tokens 1e-6 relative (none expected).
- Runtime: WSL Ubuntu 22.04, gcc/g++ 11 -O2, OpenJDK 11 (-Xss256m); C/C++ with an unlimited stack (Java already had a
  256 MB stack; the 8 MB default crashed 4 deep-recursion Accepted programs on problem 12 in the preliminary run).
- Correctness inputs (sample, random, edge): one run, 6 s limit. Large inputs: 3 runs; Accepted programs get a 20 s cap,
  the input's time limit is max(1 s, 2 x the slowest Accepted median); a scored program passes a large input when at
  least 2 of its 3 runs (i.e. the median) are correct within that limit.
- An input is kept when >= 3 Accepted programs finish and all agree. Build and scoring both use WORKERS parallel programs.

runs:    run every Accepted program on every candidate (private cache <TESTS_DIR>/v2freeze\accepted_runs.json:
         output class and median time per program and input, no code), build the frozen oracle
         <TESTS_DIR>/v2freeze\oracle2_frozen.json.
score:   run every logged submission on the frozen oracle (private <AUDIT_DIR>/oracle2_frozen_scores.csv).
analyse: specificity (in-sample and leave-one-participant-out), sensitivity with Clopper-Pearson intervals, and the
         classification of Wrong Answer submissions that pass; aggregates only, to
         results/oracle/oracle2_frozen_validation.json.
"""
import csv, hashlib, json, os, platform, re, resource, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tlt_pck_difftest as d  # noqa: E402
import tlt_pck_validate as val  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

TESTS, PROJ = d.TESTS, d.PROJ
FZ = f"{TESTS}/v2freeze"
RUNS, ORC = f"{FZ}/accepted_runs.json", f"{FZ}/oracle2_frozen.json"
PRIV = os.path.join(cfg.AUDIT_DIR, "oracle2_frozen_scores.csv")
AGG = os.path.join(HERE, "..", "results", "oracle", "oracle2_frozen_validation.json")
WORKERS, CAP, TL_SMALL, REP = 2, 20.0, 6.0, 3

resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))   # inherited by children


# ---------- comparator ----------
def same(n, a, b):
    x, y = a.split(), b.split()
    if len(x) != len(y):
        return False
    for p, q in zip(x, y):
        if p == q:
            continue
        try:
            fp, fq = float(p), float(q)
        except ValueError:
            return False
        if n == 6:
            if abs(fp - fq) > 1e-3 + 1e-9:
                return False
        elif abs(fp - fq) > 1e-6 * max(1.0, abs(fq)):
            return False
    return True


def layout(s):
    return [ln.split() for ln in s.strip().split("\n") if ln.strip()]


# ---------- inputs ----------
def gen(path, *args):
    r = subprocess.run(["python3", "-I", path, *map(str, args)], capture_output=True, timeout=120)
    return r.stdout.decode() if r.returncode == 0 else ""


def candidates(n):
    C = [("sample", s) for s in d.samples(n)]
    C += [("random", s) for k in range(40) if (s := gen(f"{TESTS}/gens/{n}.py", 6500 + k))]
    C += [("edge", s) for k in range(40) if (s := gen(f"{TESTS}/gens/{n}x.py", "edge", k))]
    C += [("large", gen(f"{TESTS}/gens/{n}x.py", "large", k)) for k in range(4)]
    return C


def run1(cmd, inp, tl):
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, input=inp.encode(), capture_output=True, timeout=tl)
    except subprocess.TimeoutExpired:
        return None, tl, "timeout"
    dt = time.perf_counter() - t0
    if r.returncode != 0:
        return None, dt, "crash"
    return r.stdout.decode("utf-8", "replace"), dt, "ok"


def median(v):
    return sorted(v)[len(v) // 2]


def src_of(r):
    return open(os.path.join(PROJ, r["code_path"]), encoding="utf-8", errors="replace").read()


# ---------- runs + build ----------
def run_accepted(job):
    r, cand = job
    with tempfile.TemporaryDirectory() as td:
        cmd = d.build(src_of(r), r["language"], td)
        if not cmd:
            return None
        res = []
        for kind, s in cand:
            if kind == "large":
                outs = [run1(cmd, s, CAP) for _ in range(REP)]
                ok = [o for o in outs if o[2] == "ok"]
                consistent = len({o[0] for o in ok}) <= 1
                out = ok[0][0] if len(ok) >= 2 and consistent else None
                res.append((out, median([o[1] for o in outs]), "ok" if out is not None else outs[0][2]))
            else:
                res.append(run1(cmd, s, TL_SMALL))
        return res


def do_runs():
    os.makedirs(FZ, exist_ok=True)
    rows = list(csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig")))
    allruns, oracle, valid = {}, {}, {}
    for n in range(1, 14):
        t0 = time.time()
        cand = candidates(n)
        vc = Counter()
        for kind, s in cand:
            try:
                val.V[n](s); vc[f"{kind}_valid"] += 1
            except ValueError:
                vc[f"{kind}_invalid"] += 1
        valid[n] = dict(vc)
        acc = [r for r in rows if r["verdict"] == "AC" and d.PID.get(int(r["problem_id"])) == n]
        reps = [[] for _ in cand]                # output-class representatives per input
        exact = [[] for _ in cand]               # per class: all members token-identical / layout-identical to the rep
        progs = []
        with ThreadPoolExecutor(WORKERS) as ex:
            for r, res in zip(acc, ex.map(run_accepted, [(r, cand) for r in acc])):
                if res is None:
                    progs.append(dict(sid=r["submission_id"], user=r["user_id"], compiles=0)); continue
                cls, tms, st = [], [], []
                for j, (out, dt, status) in enumerate(res):
                    c = -1
                    if out is not None:
                        for ci, rep in enumerate(reps[j]):
                            if same(n, out, rep):
                                c = ci
                                exact[j][ci][0] &= out.split() == rep.split()
                                exact[j][ci][1] &= layout(out) == layout(rep)
                                break
                        else:
                            reps[j].append(out); exact[j].append([True, True]); c = len(reps[j]) - 1
                    cls.append(c); tms.append(round(dt, 4)); st.append(status)
                progs.append(dict(sid=r["submission_id"], user=r["user_id"], compiles=1, cls=cls, t=tms, st=st))
        allruns[n] = dict(kinds=[k for k, _ in cand], progs=progs, n_classes=[len(x) for x in reps])
        oracle[n] = make_oracle(n, allruns[n], cand=cand, reps=reps, exact=exact)
        print(f"problem {n}: {len(acc)} accepted, {len(cand)} candidates, kept {len(oracle[n]['kept'])}, "
              f"validator {valid[n]}, {time.time() - t0:.0f} s", flush=True)
    json.dump(dict(runs=allruns, validation=valid), open(RUNS, "w"))
    json.dump(oracle, open(ORC, "w"), indent=0)


def make_oracle(n, ar, exclude=None, cand=None, reps=None, exact=None):
    """Kept inputs from the Accepted runs, optionally without one participant's programs."""
    P = [p for p in ar["progs"] if p["compiles"] and p["user"] != exclude]
    kept = []
    for j, kind in enumerate(ar["kinds"]):
        fin = [p for p in P if p["cls"][j] >= 0]
        if len(fin) >= 3 and len({p["cls"][j] for p in fin}) == 1:
            tl = round(max(1.0, 2.0 * max(p["t"][j] for p in fin)), 3) if kind == "large" else TL_SMALL
            t = dict(idx=j, kind=kind, cls=fin[0]["cls"][j], agreeing=len(fin), tl=tl)
            if cand is not None:
                t.update(input=cand[j][1], expected=reps[j][t["cls"]], ac_tokens_exact=exact[j][t["cls"]][0],
                         ac_layout_exact=exact[j][t["cls"]][1])
            kept.append(t)
    return dict(n_accepted=len(ar["progs"]), kept=kept)


# ---------- scoring ----------
def score_one(job):
    r, kept, n = job
    res = dict(submission_id=r["submission_id"], user_id=r["user_id"], problem=n, verdict=r["verdict"],
               language=r["language"], code_sha256=r["code_sha256"], compiles=0)
    with tempfile.TemporaryDirectory() as td:
        cmd = d.build(src_of(r), r["language"], td)
        if not cmd:
            return res
        res["compiles"] = 1
        by = defaultdict(lambda: [0, 0])
        slow = crash = tokfmt = layfmt = 0
        for t in kept:
            if t["kind"] == "large":
                good = bad = 0
                outs = []
                while good < 2 and bad < 2:
                    o = run1(cmd, t["input"], t["tl"])
                    outs.append(o)
                    if o[2] == "ok" and same(n, o[0], t["expected"]):
                        good += 1
                    else:
                        bad += 1
                ok = good >= 2
                if not ok and sum(o[2] == "timeout" for o in outs) >= 2:
                    slow += 1
                o = next((x for x in outs if x[2] == "ok"), outs[0])
            else:
                o = run1(cmd, t["input"], t["tl"])
                ok = o[2] == "ok" and same(n, o[0], t["expected"])
            crash += o[2] == "crash"
            if ok and o[0] is not None:
                tokfmt += t["ac_tokens_exact"] and o[0].split() != t["expected"].split()
                layfmt += t["ac_layout_exact"] and layout(o[0]) != layout(t["expected"])
            by[t["kind"]][0] += ok
            by[t["kind"]][1] += 1
    for k in ("sample", "random", "edge", "large"):
        res[f"{k}_passed"], res[f"{k}_n"] = by[k]
    res.update(large_timeouts=slow, crashes=crash, token_format_diffs=tokfmt, layout_diffs=layfmt)
    return res


COLS = (["submission_id", "user_id", "problem", "verdict", "language", "code_sha256", "compiles"]
        + [f"{k}_{x}" for k in ("sample", "random", "edge", "large") for x in ("passed", "n")]
        + ["large_timeouts", "crashes", "token_format_diffs", "layout_diffs"])


def do_score():
    orc = {int(k): v for k, v in json.load(open(ORC)).items()}
    rows = list(csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig")))
    jobs = [(r, orc[d.PID[int(r["problem_id"])]]["kept"], d.PID[int(r["problem_id"])]) for r in rows]
    out = []
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, res in enumerate(ex.map(score_one, jobs), 1):
            out.append(res)
            if i % 50 == 0:
                print(f"scored {i}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    with open(PRIV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, restval=0); w.writeheader(); w.writerows(out)


# ---------- analysis ----------
def cp(k, n, a=0.05):
    """Clopper-Pearson exact interval [estimate, lower, upper] by bisection on the binomial tails (stdlib only)."""
    from math import comb
    if n == 0:
        return [None, None, None]

    def pmf_sum(p, lo_i, hi_i):
        return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(lo_i, hi_i + 1))

    def bis(f, target, increasing):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if (f(mid) < target) == increasing:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else bis(lambda p: pmf_sum(p, k, n), a / 2, True)       # P(X >= k) = a/2
    upper = 1.0 if k == n else bis(lambda p: pmf_sum(p, 0, k), a / 2, False)      # P(X <= k) = a/2
    return [round(k / n, 4), round(lower, 4), round(upper, 4)]


def passes(r, kinds=("sample", "random", "edge", "large")):
    return all(int(r[f"{k}_passed"]) == int(r[f"{k}_n"]) for k in kinds)


def do_analyse():
    R = json.load(open(RUNS))
    runs, valid = {int(k): v for k, v in R["runs"].items()}, R["validation"]
    orc = {int(k): v for k, v in json.load(open(ORC)).items()}
    S = list(csv.DictReader(open(PRIV)))
    agg = {}
    tot_valid = Counter()
    for v in valid.values():
        for k, c in v.items():
            tot_valid["invalid" if k.endswith("invalid") else "valid"] += c
    agg["input_validation"] = dict(total=dict(tot_valid), per_problem=valid)
    agg["inputs_kept_per_problem"] = {n: dict(Counter(t["kind"] for t in v["kept"])) for n, v in orc.items()}
    agg["candidates_dropped_per_problem"] = {n: len(runs[n]["kinds"]) - len(orc[n]["kept"]) for n in orc}
    agg["large_time_limits_s"] = {n: [t["tl"] for t in v["kept"] if t["kind"] == "large"] for n, v in orc.items()}

    # timing stability of Accepted programs on large inputs: max/min ratio of the three runs is not stored; report medians
    # comparison with the preliminary oracle2.json
    try:
        old = {int(k): v for k, v in json.load(open(f"{TESTS}/oracle2.json")).items()}
        diff = Counter()
        for n in orc:
            o = {(t["kind"], t["input"]): t for t in old[n]["kept"]}
            for t in orc[n]["kept"]:
                p = o.get((t["kind"], t["input"]))
                if p is None:
                    diff["new_input"] += 1
                elif not same(n, p["expected"], t["expected"]):
                    diff["expected_changed"] += 1
                else:
                    diff["same_expected"] += 1
                    if t["kind"] == "large" and abs(p["tl"] - t["tl"]) > 0.01:
                        diff["large_tl_changed"] += 1
            diff["old_inputs_not_kept"] += len(set(o) - {(t["kind"], t["input"]) for t in orc[n]["kept"]})
        agg["vs_preliminary_oracle2"] = dict(diff)
    except FileNotFoundError:
        pass

    # verdict x oracle table
    tab = defaultdict(Counter)
    for r in S:
        tab[r["verdict"]]["compile_fail" if r["compiles"] == "0" else ("oracle_pass" if passes(r) else "oracle_fail")] += 1
    agg["verdict_by_oracle"] = {v: dict(c) for v, c in tab.items()}

    # specificity
    ac = [r for r in S if r["verdict"] == "AC" and r["compiles"] == "1"]
    k = sum(passes(r) for r in ac)
    agg["specificity_in_sample"] = dict(passing=k, n=len(ac), rate_ci95=cp(k, len(ac)))
    lopo_pass, lopo_n, users_all = 0, 0, Counter()
    users = sorted({p["user"] for ar in runs.values() for p in ar["progs"]})
    per_user = {}
    for u in users:
        up, un = 0, 0
        for n, ar in runs.items():
            o = make_oracle(n, ar, exclude=u)["kept"]
            for p in ar["progs"]:
                if p["user"] != u or not p["compiles"]:
                    continue
                ok = all(p["cls"][t["idx"]] == t["cls"] and (t["kind"] != "large" or p["t"][t["idx"]] <= t["tl"]) for t in o)
                up += ok; un += 1
        per_user[u] = (up, un)
        lopo_pass += up; lopo_n += un
    agg["specificity_leave_one_participant_out"] = dict(
        passing=lopo_pass, n=lopo_n, rate_ci95=cp(lopo_pass, lopo_n), participants=len(users),
        participants_all_passing=sum(1 for a, b in per_user.values() if a == b))

    # sensitivity
    def sens(verdict, kinds=("sample", "random", "edge", "large")):
        X = [r for r in S if r["verdict"] == verdict and r["compiles"] == "1"]
        f = sum(not passes(r, kinds) for r in X)
        byp = defaultdict(list)
        for r in X:
            byp[r["code_sha256"]].append(not passes(r, kinds))
        fd = sum(all(v) for v in byp.values())
        mixed = sum(1 for v in byp.values() if len(set(v)) > 1)
        return dict(per_submission=dict(failing=f, n=len(X), rate_ci95=cp(f, len(X))),
                    per_distinct_program=dict(failing=fd, n=len(byp), rate_ci95=cp(fd, len(byp)), mixed_outcome=mixed),
                    participants=len({r["user_id"] for r in X}),
                    not_compiling_here=sum(1 for r in S if r["verdict"] == verdict and r["compiles"] == "0"))
    agg["sensitivity"] = {v: sens(v) for v in ("WA", "TLE", "MLE")}
    agg["sensitivity_v1_inputs_only"] = {v: sens(v, ("sample", "random")) for v in ("WA", "TLE")}
    tle = [r for r in S if r["verdict"] == "TLE" and r["compiles"] == "1"]
    agg["tle_with_large_timeout"] = dict(n=sum(int(r["large_timeouts"]) > 0 for r in tle), of=len(tle))

    # WA submissions that pass: ordered classification
    acsha = defaultdict(set)
    for r in S:
        if r["verdict"] == "AC":
            acsha[r["problem"]].add(r["code_sha256"])
    wap = [r for r in S if r["verdict"] == "WA" and r["compiles"] == "1" and passes(r)]
    cls = Counter()
    for r in wap:
        if r["code_sha256"] in acsha[r["problem"]]:
            cls["1_identical_to_an_accepted_submission"] += 1
        elif int(r["token_format_diffs"]) > 0:
            cls["2_formatting_numeric_tokens"] += 1
        elif int(r["layout_diffs"]) > 0:
            cls["3_formatting_line_layout"] += 1
        elif r["submission_id"] in UB:
            cls["4_undefined_behaviour_flagged_by_sanitizer"] += 1
        else:
            cls["6_unexplained_possible_edge_case_not_in_oracle"] += 1
    cls["5_multiple_valid_outputs"] = 0      # no statement admits more than one correct output
    wsha = Counter(r["code_sha256"] for r in wap)
    agg["wa_passing_classification"] = dict(
        n=len(wap), distinct_programs=len(wsha), repeated_submissions=len(wap) - len(wsha),
        participants=len({r["user_id"] for r in wap}),
        by_problem=dict(sorted(Counter(int(r["problem"]) for r in wap).items())),
        by_language=dict(Counter(r["language"] for r in wap)), classes=dict(sorted(cls.items())),
        ub_checked=UB_CHECKED,
        note="Ordered rules; the oracle was not revised on these submissions. 'Formatting' = output equal under the "
             "comparator but not token- or line-identical where all agreeing Accepted outputs were identical.")
    agg["settings"] = dict(workers_build=WORKERS, workers_score=WORKERS, large_runs=REP, accepted_cap_s=CAP,
                           small_tl_s=TL_SMALL, large_tl_rule="max(1 s, 2 x slowest Accepted median of 3)",
                           c_cpp_stack="unlimited", java_stack="256 MB", comparator="integers exact; problem 6 abs 1e-3")
    agg["machine"] = MACHINE
    agg["freeze_manifest_sha256"] = manifest()
    json.dump(agg, open(AGG, "w"), indent=1)
    print(json.dumps({k: v for k, v in agg.items() if k not in ("input_validation", "freeze_manifest_sha256", "large_time_limits_s")}, indent=1))


def tool_version(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0] or ""
    except Exception:
        return ""


MACHINE = {}
UB, UB_CHECKED = set(), 0


def machine():
    cpu = next((ln.split(":", 1)[1].strip() for ln in open("/proc/cpuinfo") if ln.startswith("model name")), "")
    MACHINE.update(cpu=cpu, logical_cpus=os.cpu_count(), os=platform.platform(), python=platform.python_version(),
                   gcc=tool_version(["gcc", "--version"]), java=subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()[0])


def manifest():
    files = [f"{TESTS}/gens/{f}" for f in sorted(os.listdir(f"{TESTS}/gens")) if f.endswith(".py")]
    files += [ORC, os.path.join(HERE, "tlt_pck_validate.py"), os.path.abspath(__file__), os.path.join(HERE, "tlt_pck_difftest.py")]
    files += [f"{d.STM}/{n}.md" for n in range(1, 14)]
    return {os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f): hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}


def ub_check():
    """C/C++ Wrong Answer submissions that pass: rebuild with -fsanitize=address,undefined and run the correctness inputs."""
    global UB_CHECKED
    orc = {int(k): v for k, v in json.load(open(ORC)).items()}
    rows = {r["submission_id"]: r for r in csv.DictReader(open(f"{PROJ}/submissions.csv", encoding="utf-8-sig"))}
    S = [r for r in csv.DictReader(open(PRIV)) if r["verdict"] == "WA" and r["compiles"] == "1" and passes(r) and r["language"] in ("C", "C++")]

    def one(r):
        src = src_of(rows[r["submission_id"]])
        with tempfile.TemporaryDirectory() as td:
            fn = os.path.join(td, "a.c" if r["language"] == "C" else "a.cpp")
            open(fn, "w").write(src)
            cc = ["gcc", "-std=gnu11"] if r["language"] == "C" else ["g++", "-std=gnu++17"]
            b = subprocess.run(cc + ["-O2", "-w", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all", fn,
                                     "-o", os.path.join(td, "a.out"), "-lm"], capture_output=True, timeout=180)
            if b.returncode:
                return None
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
            for t in orc[int(r["problem"])]["kept"]:
                if t["kind"] == "large":
                    continue
                try:
                    p = subprocess.run(["bash", "-c", 'ulimit -s 262144; exec "$0"', os.path.join(td, "a.out")],
                                       input=t["input"].encode(), capture_output=True, timeout=30, env=env)
                except subprocess.TimeoutExpired:
                    continue
                if p.returncode != 0 and (b"runtime error" in p.stderr or b"AddressSanitizer" in p.stderr):
                    return True
            return False
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(one, S))
    UB_CHECKED = sum(x is not None for x in res)
    UB.update(r["submission_id"] for r, x in zip(S, res) if x)


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "all"
    machine()
    if m in ("runs", "all"):
        do_runs()
    if m in ("score", "all"):
        do_score()
    if m in ("analyse", "all"):
        ub_check()
        do_analyse()
