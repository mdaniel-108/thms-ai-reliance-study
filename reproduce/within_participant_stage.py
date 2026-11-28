"""Unchanged use and over-reliance by stage within participants, from the pseudonymised tables in data/.

  python reproduce/within_participant_stage.py

Standard library only. Decisions with an ambiguous attribution are left out, as in the main analysis. Stage 1 is
compared with stages 2-5 among the participants who have decisions at both. Output: results/within_stage.json.
"""
import collections, csv, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KINDS = ("sample", "random", "edge", "large")
A = {a["answer_id"]: a for a in csv.DictReader(open(os.path.join(ROOT, "data", "answers.csv"), encoding="utf-8"))}
D = [x for x in csv.DictReader(open(os.path.join(ROOT, "data", "decisions.csv"), encoding="utf-8"))
     if x["attribution_rule"] != "ambiguous"]


def passes_all(r, p):
    return r[f"{p}compiles"] == "1" and all(r[f"{p}{k}_passed"] == r[f"{p}{k}_n"] for k in KINDS)


cnt = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for x in D:
    rid = x["attributed_answer_id"] if x["use"] != "not_used" else x["last_answer_id"]
    wrong = not passes_all(A[rid], "answer_")
    used = x["use"] in ("unchanged", "adapted")
    over = wrong and used and not passes_all(x, "next_")
    c = cnt[x["participant"]]["stage_1" if x["stage"] == "1" else "stages_2_5"]
    c["n"] += 1
    c["unchanged"] += x["use"] == "unchanged"
    c["over_reliance"] += over

both = sorted(p for p in cnt if cnt[p]["stage_1"]["n"] and cnt[p]["stages_2_5"]["n"])
out = {"note": "Within-participant comparison of stage 1 with stages 2-5 (participants with decisions at both).",
       "participants": len(both)}
for m in ("unchanged", "over_reliance"):
    pooled = {s: dict(k=sum(cnt[p][s][m] for p in both), n=sum(cnt[p][s]["n"] for p in both)) for s in ("stage_1", "stages_2_5")}
    for s in pooled:
        pooled[s]["rate"] = round(pooled[s]["k"] / pooled[s]["n"], 4)
    r = [(cnt[p]["stage_1"][m] / cnt[p]["stage_1"]["n"], cnt[p]["stages_2_5"][m] / cnt[p]["stages_2_5"]["n"]) for p in both]
    pooled["participants_higher_later"] = sum(b > a for a, b in r)
    pooled["participants_lower_later"] = sum(b < a for a, b in r)
    pooled["participants_equal"] = sum(b == a for a, b in r)
    out[m] = pooled
json.dump(out, open(os.path.join(ROOT, "results", "within_stage.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
