"""Use of the answer by answer class, and correctness, unchanged use and over-reliance by stage, from the
pseudonymised tables in data/.

  python reproduce/use_by_class_and_stage.py

Standard library only. Decisions with an ambiguous attribution are left out, as in the main analysis. Correctness by
stage is counted over runnable answers; unchanged use and over-reliance over decisions. Intervals are participant-cluster
bootstrap intervals (2,000 resamples, seed 2026). Output: results/use_by_class_and_stage.json.
"""
import collections, csv, json, os, random

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KINDS = ("sample", "random", "edge", "large")
A = list(csv.DictReader(open(os.path.join(ROOT, "data", "answers.csv"), encoding="utf-8")))
AI = {a["answer_id"]: a for a in A}
D = [x for x in csv.DictReader(open(os.path.join(ROOT, "data", "decisions.csv"), encoding="utf-8"))
     if x["attribution_rule"] != "ambiguous"]


def passes_all(r, p):
    return r[f"{p}compiles"] == "1" and all(r[f"{p}{k}_passed"] == r[f"{p}{k}_n"] for k in KINDS)


def sample_ok(r, p):
    return r[f"{p}compiles"] == "1" and r[f"{p}sample_passed"] == r[f"{p}sample_n"]


def stage3(s):
    return "1" if s == "1" else "2" if s == "2" else "3-5"


def rate(rows, key, n=2000, seed=2026):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["participant"]].append(r[key])
    us = sorted(by); rnd = random.Random(seed); v = []
    for _ in range(n):
        s = [rnd.choice(us) for _ in us]
        v.append(sum(sum(by[u]) for u in s) / sum(len(by[u]) for u in s))
    v.sort()
    k = sum(r[key] for r in rows)
    return dict(k=k, n=len(rows), rate=round(k / len(rows), 4), lo=round(v[49], 4), hi=round(v[1949], 4))


for x in D:
    a = AI[x["attributed_answer_id"] if x["use"] != "not_used" else x["last_answer_id"]]
    x["cls"] = "correct" if passes_all(a, "answer_") else "wrong_sample_passing" if sample_ok(a, "answer_") else "wrong_sample_failing"
    x["unchanged"] = x["use"] == "unchanged"
    x["over_reliance"] = x["cls"] != "correct" and x["use"] != "not_used" and not passes_all(x, "next_")
    x["stage3"] = stage3(x["stage"])
R = [dict(a, correct=passes_all(a, "answer_"), stage3=stage3(a["stage"])) for a in A if a["scorable"] == "1"]
out = {"note": "Use by answer class (decisions) and rates by stage (correctness over runnable answers; unchanged use and "
               "over-reliance over decisions).", "use_by_class": {}, "by_stage": {}}
for c in ("correct", "wrong_sample_failing", "wrong_sample_passing"):
    rows = [x for x in D if x["cls"] == c]
    out["use_by_class"][c] = dict(n=len(rows), **{u: sum(x["use"] == u for x in rows) for u in ("unchanged", "adapted", "not_used")})
for s in ("1", "2", "3-5"):
    out["by_stage"][s] = dict(correct=rate([r for r in R if r["stage3"] == s], "correct"),
                              unchanged=rate([x for x in D if x["stage3"] == s], "unchanged"),
                              over_reliance=rate([x for x in D if x["stage3"] == s], "over_reliance"))
json.dump(out, open(os.path.join(ROOT, "results", "use_by_class_and_stage.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
