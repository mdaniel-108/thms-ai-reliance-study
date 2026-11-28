"""Recompute the RQ1 and RQ2 counts from the pseudonymised tables in data/ and check them against results/results.json.

  python reproduce/reproduce_rq1_rq2.py

Needs only the Python standard library. Bootstrap intervals are not recomputed (they depend on participant order);
every count, numerator, denominator and point rate is.
"""
import collections, csv, json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KINDS = ("sample", "random", "edge", "large")
res = json.load(open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8"))
A = list(csv.DictReader(open(os.path.join(ROOT, "data", "answers.csv"), encoding="utf-8")))
D = list(csv.DictReader(open(os.path.join(ROOT, "data", "decisions.csv"), encoding="utf-8")))


def passes_all(r, p):
    return r[f"{p}compiles"] == "1" and all(r[f"{p}{k}_passed"] == r[f"{p}{k}_n"] for k in KINDS)


def total(r, p):
    return sum(int(r[f"{p}{k}_passed"]) for k in KINDS) if r[f"{p}compiles"] == "1" else 0


def stage3(s):
    return "1" if s == "1" else "2" if s == "2" else "3+"


S = [a for a in A if a["scorable"] == "1"]
for a in S:
    a["correct"] = passes_all(a, "answer_")
    sample_ok = a["answer_compiles"] == "1" and a["answer_sample_passed"] == a["answer_sample_n"]
    a["cls"] = "correct" if a["correct"] else ("wrong_undetectable" if sample_ok else "wrong_detectable")
    t, ft = total(a, "answer_"), total(a, "failed_")
    a["change"] = "correct" if a["correct"] else "improvement" if t > ft else "unchanged" if t == ft else "regression"
cls = {a["answer_id"]: a["cls"] for a in S}
checks = []


def check(name, got, want):
    checks.append((name, got == want, got, want))


def kn(rows, f):
    return dict(k=sum(1 for r in rows if f(r)), n=len(rows))


# ---------- counts and RQ1 ----------
c = res["counts"]
check("answers", len(A), c["answers"])
check("scorable answers", len(S), c["scorable"])
check("participants", len({a["participant"] for a in A}), c["participants"])
check("failures with a scorable answer", len({a["failure_id"] for a in S}), c["failures_with_scorable"])
r1 = res["RQ1"]
got = kn(S, lambda a: a["correct"])
check("RQ1 correct k/n", got, {k: r1["correct"][k] for k in ("k", "n")})
check("RQ1 answer classes", dict(collections.Counter(a["cls"] for a in S)), r1["classes"])
check("RQ1 change vs failed program", dict(collections.Counter(a["change"] for a in S)), r1["change_vs_failed_program"])
check("RQ1 runnable k/n", kn(A, lambda a: a["scorable"] == "1"), {k: r1["runnable"][k] for k in ("k", "n")})
check("RQ1 delivered fix k/n", kn(A, lambda a: a["scorable"] == "1" and passes_all(a, "answer_")),
      {k: r1["delivered_fix"][k] for k in ("k", "n")})
for g, key in (("stage", lambda a: stage3(a["stage"])), ("provider", lambda a: a["provider"])):
    for lvl, want in r1[f"correct_by_{g}"].items():
        rows = [a for a in S if key(a) == lvl]
        check(f"RQ1 correct by {g} = {lvl}", kn(rows, lambda a: a["correct"]), {k: want[k] for k in ("k", "n")})

# ---------- RQ2 ----------
r2 = res["RQ2"]
R = []
for x in D:
    if x["attribution_rule"] == "ambiguous":
        continue
    rid = x["attributed_answer_id"] if x["use"] != "not_used" else x["last_answer_id"]
    R.append(dict(x, cls=cls[rid], next_correct=passes_all(x, "next_")))


def category(r):
    used = r["use"] in ("unchanged", "adapted")
    if r["cls"] != "correct":
        return ("corrective_adaptation" if r["next_correct"] else "over_reliance") if used else "appropriate_rejection"
    if used:
        return "appropriate_use" if r["next_correct"] else "damaging_adaptation"
    return "alternative_correct_solution" if r["next_correct"] else "under_reliance"


for r in R:
    r["category"] = category(r)
check("RQ2 decisions (excluding ambiguous)", len(R), r2["decisions_excl_ambiguous"])
check("RQ2 ambiguous decisions", sum(1 for x in D if x["attribution_rule"] == "ambiguous"), r2["ambiguous"])
t18 = collections.Counter(f"{r['cls']}|{r['use']}|{'next_correct' if r['next_correct'] else 'next_not_correct'}" for r in R)
check("RQ2 answer class x use x next submission table", dict(t18), r2["table_18"])
check("RQ2 reliance categories", dict(collections.Counter(r["category"] for r in R)), r2["categories"])
for cat in ("over_reliance", "under_reliance", "appropriate_use", "appropriate_rejection"):
    check(f"RQ2 rate {cat} k/n", kn(R, lambda r: r["category"] == cat), {k: r2[f"rate_{cat}"][k] for k in ("k", "n")})
for cl in ("wrong_detectable", "wrong_undetectable", "correct"):
    rows = [r for r in R if r["cls"] == cl]
    check(f"RQ2 used given {cl} k/n", kn(rows, lambda r: r["use"] in ("unchanged", "adapted")),
          {k: r2[f"use_given_{cl}"][k] for k in ("k", "n")})
    check(f"RQ2 unchanged given {cl} k/n", kn(rows, lambda r: r["use"] == "unchanged"),
          {k: r2[f"unchanged_given_{cl}"][k] for k in ("k", "n")})
oc = [r for r in R if r["cls"] != "correct" and r["use"] == "unchanged"]
uc = [r for r in R if r["cls"] == "correct" and r["use"] not in ("unchanged", "adapted")]
check("Gate G2 over-reliance cell", dict(n=len(oc), participants=len({r["participant"] for r in oc})),
      r2["G2"]["over_reliance_cell"])
check("Gate G2 under-reliance cell", dict(n=len(uc), participants=len({r["participant"] for r in uc})),
      r2["G2"]["under_reliance_cell"])
ans = {a["answer_id"]: a for a in A}
ad = [x for x in D if x["use"] == "adapted"]
eff = collections.Counter()
for x in ad:
    a_tot, n_tot = total(ans[x["attributed_answer_id"]], "answer_"), total(x, "next_")
    eff["improved" if n_tot > a_tot else "neutral" if n_tot == a_tot else "damaged"] += 1
check("Gate G1 adapted decisions", dict(adapted=len(ad), participants=len({x["participant"] for x in ad})),
      {k: r2["G1"][k] for k in ("adapted", "participants")})
check("RQ2 edit effect of adapted answers", dict(eff), r2["edit_effect_adapted"])
uu = [r for r in R if r["use"] == "unchanged"]
ovj = r2["oracle_vs_judge_unchanged"]
check("Oracle vs judge, unchanged submissions", dict(
    n=len(uu),
    oracle_correct_judge_AC=sum(1 for r in uu if r["cls"] == "correct" and r["next_judge_verdict"] == "AC"),
    oracle_correct_judge_not_AC=sum(1 for r in uu if r["cls"] == "correct" and r["next_judge_verdict"] != "AC"),
    oracle_wrong_judge_AC=sum(1 for r in uu if r["cls"] != "correct" and r["next_judge_verdict"] == "AC"),
    oracle_wrong_judge_not_AC=sum(1 for r in uu if r["cls"] != "correct" and r["next_judge_verdict"] != "AC")),
    {k: ovj[k] for k in ("n", "oracle_correct_judge_AC", "oracle_correct_judge_not_AC", "oracle_wrong_judge_AC",
                         "oracle_wrong_judge_not_AC")})

ok = sum(1 for _, good, _, _ in checks if good)
for name, good, g, w in checks:
    print(("OK      " if good else "MISMATCH"), name, "" if good else f"\n   recomputed {g}\n   reported   {w}")
print(f"\n{ok} of {len(checks)} checks match results/results.json")
sys.exit(0 if ok == len(checks) else 1)
