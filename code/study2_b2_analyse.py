r"""Study 2: baseline B2 summary and the second G0 convergence source.

  python -I code/study2_b2_analyse.py

B2: per model, the share of the 39 problem x language cells solved (mean of 3 samples, and at least 1 of 3), by problem.
G0 source (b): pairs between B2 programs correct on the oracle and Accepted submissions that are below 0.80 similarity
to every earlier AI block (the same independent set as source (a)); share of pairs at >= 0.80 and >= 0.99.
Aggregate output: results/b2_results.json.
"""
import collections, csv, difflib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import tok  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

PRIV = cfg.STUDY2_DIR
LABELS = os.path.join(cfg.AUDIT_DIR, "tlt_labels.csv")
OUT = os.path.join(HERE, "..", "results", "b2_results.json")
FENCE = re.compile(r"```([A-Za-z0-9+#]*)[^\n]*\n(.*?)```", re.S)
LANG = {"c": "C", "cpp": "C++", "c++": "C++", "cc": "C++", "cxx": "C++", "java": "Java"}
KINDS = ("sample", "random", "edge", "large")


def main():
    gens = [json.loads(ln) for ln in open(f"{PRIV}/b2/generations.jsonl", encoding="utf-8")]
    sc = {r["key"]: r for r in csv.DictReader(open(f"{PRIV}/b2_scores.csv"))}
    ok = lambda r: r["compiles"] == "1" and all(r[f"{k}_passed"] == r[f"{k}_n"] for k in KINDS)
    cell = collections.defaultdict(list)
    progs = collections.defaultdict(list)
    aborted = collections.Counter()
    for g in gens:
        key = f'{g["model"]}|{g["problem"]}|{g["lang"]}|{g["seed"]}'
        c = ok(sc[key])
        cell[(g["model"], g["problem"], g["lang"])].append(c)
        if str(g.get("done_reason", "")).startswith("error"):
            aborted[g["model"]] += 1
        if c:
            for tag, body in reversed(FENCE.findall(g["response"])):
                if LANG.get(tag.lower(), g["lang"] if tag == "" else None) == g["lang"] and re.search(r"\bmain\s*\(", body):
                    progs[g["problem"]].append(body); break
    out = dict(generations=len(gens), aborted_by_server=dict(aborted),
               compiled=sum(sc[k]["compiles"] == "1" for k in sc), correct_generations=sum(ok(r) for r in sc.values()))
    models = sorted({m for m, _, _ in cell})
    per = {}
    for m in models:
        cs = [v for (mm, _, _), v in cell.items() if mm == m]
        per[m] = dict(cells=len(cs), mean_of_3=round(sum(sum(v) / len(v) for v in cs) / len(cs), 4),
                      at_least_1_of_3=round(sum(any(v) for v in cs) / len(cs), 4),
                      problems_solved_any_language=len({p for (mm, p, _), v in cell.items() if mm == m and any(v)}))
    out["per_model"] = per
    out["problems_solved_by_any_model"] = sorted({p for (_, p, _), v in cell.items() if any(v)})
    # G0 source (b)
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
    lab = {r["submission_id"]: float(r["best_similarity"]) for r in csv.DictReader(open(LABELS, encoding="utf-8"))}
    indep = collections.defaultdict(list)
    for s in subs:
        if s["verdict"] == "AC" and lab.get(s["submission_id"], 1.0) < 0.80:
            indep[int(s["problem_id"]) - 794].append(tok(open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8",
                                                              errors="replace").read()))
    sims, probs = [], set()
    for n, P in progs.items():
        for p in P:
            tp = tok(p)
            for a in indep.get(n, []):
                sims.append(difflib.SequenceMatcher(None, tp, a, autojunk=False).ratio()); probs.add(n)
    out["G0_source_b"] = dict(pairs=len(sims), problems=len(probs), usable=len(sims) >= 20 and len(probs) >= 5,
                              share_ge_080=round(sum(x >= 0.80 for x in sims) / len(sims), 4) if sims else None,
                              share_ge_099=round(sum(x >= 0.99 for x in sims) / len(sims), 4) if sims else None,
                              p99=round(sorted(sims)[min(len(sims) - 1, int(0.99 * len(sims)))], 4) if sims else None)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
