r"""Study 2: score programs on the frozen oracle v2 (same procedure as the freeze: 2 workers, large inputs until 2 good
or 2 bad runs, 6 s on other inputs, unlimited C/C++ stack).

  python -I .../tools/study2_score.py answers      # the 587 scorable logged answers
  python -I .../tools/study2_score.py b2           # B2 statement-only local programs
  python -I .../tools/study2_score.py selftest     # 13 Accepted submissions (one per problem)

Private outputs in <STUDY2_DIR>/ (answers_scores.csv, b2_scores.csv). Aggregates are made by study2_analyse.py.
"""
import collections, csv, json, os, pickle, re, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tlt_pck_oracle2_freeze as F  # noqa: E402  (sets the unlimited stack, inherited by children)
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

PRIV = cfg.STUDY2_DIR
FENCE = re.compile(r"```([A-Za-z0-9+#]*)[^\n]*\n(.*?)```", re.S)
LANG = {"c": "C", "cpp": "C++", "c++": "C++", "cc": "C++", "cxx": "C++", "java": "Java"}
KINDS = ("sample", "random", "edge", "large")


def score_src(job):
    key, src, lang, n, kept = job
    res = dict(key=key, problem=n, compiles=0)
    with tempfile.TemporaryDirectory() as td:
        cmd = d.build(src, lang, td)
        if not cmd:
            return res
        res["compiles"] = 1
        by = collections.defaultdict(lambda: [0, 0])
        slow = 0
        for t in kept:
            if t["kind"] == "large":
                good = bad = 0
                outs = []
                while good < 2 and bad < 2:
                    o = F.run1(cmd, t["input"], t["tl"]); outs.append(o)
                    if o[2] == "ok" and F.same(n, o[0], t["expected"]):
                        good += 1
                    else:
                        bad += 1
                ok = good >= 2
                slow += (not ok) and sum(o[2] == "timeout" for o in outs) >= 2
            else:
                o = F.run1(cmd, t["input"], t["tl"])
                ok = o[2] == "ok" and F.same(n, o[0], t["expected"])
            by[t["kind"]][0] += ok
            by[t["kind"]][1] += 1
    for k in KINDS:
        res[f"{k}_passed"], res[f"{k}_n"] = by[k]
    res["large_timeouts"] = slow
    return res


def run(jobs, path):
    out, t0 = [], time.time()
    with ThreadPoolExecutor(F.WORKERS) as ex:
        for i, r in enumerate(ex.map(score_src, jobs), 1):
            out.append(r)
            if i % 25 == 0:
                print(f"scored {i}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    cols = ["key", "problem", "compiles"] + [f"{k}_{x}" for k in KINDS for x in ("passed", "n")] + ["large_timeouts"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval=0); w.writeheader(); w.writerows(out)
    return out


def main():
    mode = sys.argv[1]
    orc = {int(k): v["kept"] for k, v in json.load(open(F.ORC)).items()}
    if mode == "selftest":
        rows = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
        pick = {}
        for r in rows:
            n = d.PID[int(r["problem_id"])]
            if r["verdict"] == "AC" and n not in pick:
                pick[n] = r
        jobs = [(r["submission_id"], F.src_of(r), r["language"], n, orc[n]) for n, r in sorted(pick.items())]
        out = run(jobs, f"{PRIV}/selftest_scores.csv")
        print("selftest: all inputs passed in", sum(all(int(o[f"{k}_passed"]) == int(o[f"{k}_n"]) for k in KINDS)
                                                     for o in out), "of", len(out))
    elif mode == "answers":
        A = pickle.load(open(f"{PRIV}/answers.pkl", "rb"))
        jobs = [(a["rid"], a["program"], a["lang"], a["problem"], orc[a["problem"]]) for a in A if a["scorable"]]
        run(jobs, f"{PRIV}/answers_scores.csv")
    elif mode == "b2":
        jobs = []
        for ln in open(f"{PRIV}/b2/generations.jsonl", encoding="utf-8"):
            g = json.loads(ln)
            prog = None
            for tag, body in reversed(FENCE.findall(g["response"])):
                if LANG.get(tag.lower(), g["lang"] if tag == "" else None) == g["lang"] and re.search(r"\bmain\s*\(", body):
                    prog = body; break
            key = f'{g["model"]}|{g["problem"]}|{g["lang"]}|{g["seed"]}'
            if prog is None:
                jobs.append((key, "", g["lang"], g["problem"], []))       # no program: compiles = 0
            else:
                jobs.append((key, prog, g["lang"], g["problem"], orc[g["problem"]]))
        run(jobs, f"{PRIV}/b2_scores.csv")


if __name__ == "__main__":
    main()
