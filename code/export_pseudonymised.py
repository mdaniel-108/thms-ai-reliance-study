"""Write the pseudonymised, code-free tables in data/ from the private Study 2 files.

  python export_pseudonymised.py <private_study2_dir> <frozen_scores_csv> <out_dir>

Participant, failure, answer and decision identifiers are replaced by new random IDs (drawn with the operating-system
random source, so the mapping cannot be recomputed and is not stored). Rows are shuffled, so their order carries no
time information. No source code, prompt, assistant answer, timestamp, judge submission ID or account ID is written.
"""
import csv, os, pickle, secrets, sys

PRIV, FROZEN, OUT = sys.argv[1:4]
KINDS = ("sample", "random", "edge", "large")
rng = secrets.SystemRandom()


def mapping(keys, prefix, width):
    keys = sorted(set(keys))
    nums = list(range(1, len(keys) + 1))
    rng.shuffle(nums)
    return {k: f"{prefix}{n:0{width}d}" for k, n in zip(keys, nums)}


A = pickle.load(open(os.path.join(PRIV, "answers.pkl"), "rb"))
sc = {r["key"]: r for r in csv.DictReader(open(os.path.join(PRIV, "answers_scores.csv")))}
fz = {r["submission_id"]: r for r in csv.DictReader(open(FROZEN))}
dec = list(csv.DictReader(open(os.path.join(PRIV, "decisions.csv"))))

P = mapping([a["user"] for a in A] + [x["user"] for x in dec], "P", 2)
F = mapping([a["fail"] for a in A] + [x["fail"] for x in dec], "F", 4)
R = mapping([a["rid"] for a in A], "A", 4)
D = mapping([x["fail"] for x in dec], "D", 4)


def oracle_cols(prefix, r):
    out = {f"{prefix}compiles": int(r["compiles"]) if r else ""}
    for k in KINDS:
        out[f"{prefix}{k}_passed"] = int(r[f"{k}_passed"]) if r else ""
        out[f"{prefix}{k}_n"] = int(r[f"{k}_n"]) if r else ""
    return out


rows = []
for a in A:
    s = sc.get(a["rid"]) if a["scorable"] else None
    row = dict(answer_id=R[a["rid"]], participant=P[a["user"]], problem=int(a["problem"]), failure_id=F[a["fail"]],
               failed_verdict=a["fail_verdict"], failed_language=a["fail_lang"], stage=a["stage"],
               provider=(a["provider"] or "").lower(), model=a["model"], form=a["form"], answer_language=a["lang"] or "",
               scorable=int(bool(a["scorable"])),
               similarity_to_next_submission=round(float(a["sim_next"]), 4) if a.get("sim_next") not in (None, "") else "")
    row.update(oracle_cols("failed_", fz[a["fail"]]))
    row.update(oracle_cols("answer_", s))
    row["answer_large_timeouts"] = int(s["large_timeouts"]) if s else ""
    rows.append(row)
rng.shuffle(rows)

drows = []
for x in dec:
    drows.append(dict(decision_id=D[x["fail"]], participant=P[x["user"]], problem=int(x["problem"]), failure_id=F[x["fail"]],
                      attributed_answer_id=R.get(x["attributed_rid"], ""), last_answer_id=R[x["last_rid"]],
                      scorable_answers=int(x["n_scorable"]), attribution_rule=x["rule"], use=x["use"],
                      similarity=round(float(x["sim"]), 4), stage=x["stage"], provider=x["provider"], form=x["form"],
                      next_judge_verdict=x["next_verdict"], **oracle_cols("next_", fz[x["next"]])))
rng.shuffle(drows)

os.makedirs(OUT, exist_ok=True)
for name, rr in (("answers.csv", rows), ("decisions.csv", drows)):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rr[0]))
        w.writeheader()
        w.writerows(rr)
print(len(rows), "answers;", len(drows), "decisions;", len(P), "participants")
