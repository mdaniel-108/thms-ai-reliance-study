r"""Study 2, additional analyses E5.1-E5.6.

  python -I code/study2_additional1.py

Aggregates only: results/additional_1.json.
"""
import collections, csv, json, os, pickle, random, sys, tempfile, zipfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, ts  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import study2_analyse as S2  # noqa: E402

PRIV = S2.PRIV
OUT = os.path.join(HERE, "..", "results", "additional_1.json")
STATEMENT_TL = {8: 3.0, 9: 2.0, 10: 6.0, 11: 2.0, 12: 3.0, 13: 3.0}      # problems whose statement states a limit
SEED, NBOOT = 2026, 2000


def boot(df, col, unit="user"):
    return S2.boot_rate(df.assign(**{col: df[col].astype(bool)}), col, unit=unit, n=NBOOT)


def main():
    A = pickle.load(open(f"{PRIV}/answers.pkl", "rb"))
    byrid = {a["rid"]: a for a in A}
    sc = {r["key"]: r for r in csv.DictReader(open(f"{PRIV}/answers_scores.csv"))}
    fz = {r["submission_id"]: r for r in csv.DictReader(open(S2.FROZEN))}
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
    sub = {s["submission_id"]: s for s in subs}
    stime = {s["submission_id"]: ts(s["submitted_at"]) for s in subs}
    sb = collections.defaultdict(list)
    for s in subs:
        sb[(s["user_id"], int(s["problem_id"]) - 794)].append(s)
    for v in sb.values():
        v.sort(key=lambda s: s["submitted_at"])
    cls = {}
    for a in A:
        if a["scorable"]:
            r = sc[a["rid"]]
            ok = S2.passes_all(r); samp = r["compiles"] == "1" and r["sample_passed"] == r["sample_n"]
            cls[a["rid"]] = "correct" if ok else ("wrong_undetectable" if samp else "wrong_detectable")
    z = zipfile.ZipFile(S2.ZIP)
    lat, reqs, seen = {}, collections.defaultdict(list), set()
    for r in jsonl(z, "data/analysis/proxy_calls.jsonl"):
        if r.get("operation") not in (None, "None") or r.get("status") != "success" or not r.get("created_at"):
            continue
        if r.get("call_index") not in ("primary", None) or r["chat_request_id"] in seen:
            continue
        n = pno(r.get("problem_id"))
        if n is None:
            continue
        seen.add(r["chat_request_id"])
        t = ts(r["created_at"])
        lat[r["chat_request_id"]] = t + pd.Timedelta(milliseconds=float(r.get("latency_ms") or 0)).to_pytimedelta()
        reqs[(r["participant"], n)].append((t, r.get("attempt_selected_stage"), r.get("attempt_provider")))
    for v in reqs.values():
        v.sort(key=lambda x: x[0])
    edits = collections.defaultdict(list)
    for r in jsonl(z, "data/analysis/telemetry.jsonl"):
        if r["type"] in ("edit_delta", "file_save"):
            t = ts(r.get("client_ts") or r.get("server_ts"))
            if t:
                edits[r["participant"]].append(t)
    for v in edits.values():
        v.sort()

    dec = [x for x in csv.DictReader(open(f"{PRIV}/decisions.csv")) if x["rule"] != "ambiguous"]
    for x in dec:
        used = x["use"] != "not_used"
        x["rid"] = x["attributed_rid"] if used else x["last_rid"]
        x["cls"] = cls[x["rid"]]
        x["next_ok_oracle"] = S2.passes_all(fz[x["next"]])
        x["t_next"] = stime[x["next"]]
        x["t_fail"] = stime[x["fail"]]
        x["stage3"] = S2.stage3(byrid[x["rid"]]["stage"])
        x["ai_fail"] = x["use"] == "unchanged" and x["next_verdict"] != "AC"
    res = {"note": "Additional analyses E5.1-E5.6. Aggregates only."}

    # ---------- E5.1 ----------
    R = pd.DataFrame(dec)
    uu = R[R.use == "unchanged"]
    mat = collections.defaultdict(lambda: collections.Counter())
    for _, r in uu.iterrows():
        v = r.next_verdict if r.next_verdict in ("AC", "WA", "TLE") else "other"
        mat[str(r.problem)][f"{r.cls}|{v}"] += 1
    e1 = dict(disagreement_matrix_unchanged={k: dict(v) for k, v in sorted(mat.items(), key=lambda kv: int(kv[0]))})

    def categories(df, truth):
        out = collections.Counter()
        for _, r in df.iterrows():
            u = r.use in ("unchanged", "adapted")
            if r.use == "unchanged" and truth != "oracle":
                ok = r.next_verdict == "AC" or (truth == "judge_tle_ok" and r.next_verdict == "TLE")
                out["appropriate_use" if ok else "over_reliance"] += 1
                continue
            wrong = r.cls != "correct"
            if wrong:
                out[("corrective_adaptation" if r.next_ok_oracle else "over_reliance") if u else "appropriate_rejection"] += 1
            else:
                out[("appropriate_use" if r.next_ok_oracle else "damaging_adaptation") if u else
                    ("alternative_correct_solution" if r.next_ok_oracle else "under_reliance")] += 1
        return dict(n=len(df), **{k: out[k] for k in ("over_reliance", "appropriate_use")}, all=dict(out))
    e1["rq2_by_truth"] = {t: categories(R, t) for t in ("oracle", "judge_tle_ok", "judge_strict")}
    e1["rq2_without_problems_10_11"] = {t: categories(R[~R.problem.astype(int).isin([10, 11])], t)
                                       for t in ("oracle", "judge_tle_ok", "judge_strict")}
    Sc = [a for a in A if a["scorable"]]
    e1["rq1_correct_without_10_11"] = dict(k=sum(cls[a["rid"]] == "correct" for a in Sc if a["problem"] not in (10, 11)),
                                          n=sum(a["problem"] not in (10, 11) for a in Sc))
    # TLE re-score at the statement's limit
    import tlt_pck_oracle2_freeze as F
    orc = {int(k): v["kept"] for k, v in json.load(open(F.ORC)).items()}
    tle = uu[(uu.next_verdict == "TLE") & uu.problem.astype(int).isin(list(STATEMENT_TL))]
    rs = collections.Counter()
    for _, r in tle.iterrows():
        a = byrid[r.rid]; n = int(r.problem)
        with tempfile.TemporaryDirectory() as td:
            cmd = d.build(a["program"], a["lang"], td)
            if not cmd:
                rs["no_build"] += 1; continue
            slow = False
            for t in orc[n]:
                if t["kind"] != "large":
                    continue
                times = []
                for _ in range(3):
                    o = F.run1(cmd, t["input"], STATEMENT_TL[n] * 3)
                    times.append(o[1] if o[2] == "ok" else 99)
                if sorted(times)[1] > STATEMENT_TL[n]:
                    slow = True; break
            rs[f"{r.cls}|{'exceeds_statement_limit' if slow else 'within_statement_limit'}"] += 1
    e1["tle_rescore_statement_limit"] = dict(n=len(tle), problems=sorted(STATEMENT_TL), result=dict(rs),
                                             note="median of 3 runs per large input on this machine")
    res["E5_1"] = e1

    # ---------- E5.2 / E5.3 ----------
    by_next = {x["next"]: x for x in dec}
    by_fail = {x["fail"]: x for x in dec}
    for x in dec:
        prev = by_next.get(x["fail"])
        x["prev_type"] = ("ai_attributable" if prev and prev["ai_fail"] else "other_failure")
    thr = collections.defaultdict(list)
    for x in dec:
        thr[(x["user"], x["problem"])].append(x)
    for L in thr.values():
        L.sort(key=lambda x: x["t_fail"])
        k = 0
        for x in L:
            x["k"] = min(k, 3); k += x["ai_fail"]
    R = pd.DataFrame(dec)
    R["unchanged"] = R.use == "unchanged"; R["used"] = R.use != "not_used"
    e2 = {}
    for col in ("unchanged", "used"):
        e2[f"{col}_by_k"] = {str(k): boot(R[R.k == k], col) for k in range(4)}
        e2[f"{col}_by_prev"] = {p: boot(R[R.prev_type == p], col) for p in ("ai_attributable", "other_failure")}
        e2[f"{col}_by_k_and_stage"] = {f"k{k}|stage{s}": dict(k=int(R[(R.k == k) & (R.stage3 == s)][col].sum()),
                                                            n=int(((R.k == k) & (R.stage3 == s)).sum()))
                                       for k in range(4) for s in ("1", "2", "3+")}
    try:
        import statsmodels.api as sm, statsmodels.formula.api as smf
        g = smf.gee("unchanged ~ k + C(stage3) + C(problem)", "user", R.assign(unchanged=R.unchanged.astype(int),
                    k=R.k.astype(float)), family=sm.families.Binomial(), cov_struct=sm.cov_struct.Independence()).fit()
        ci = g.conf_int().loc["k"]
        e2["gee_unchanged_per_prior_ai_failure"] = dict(OR=round(float(np.exp(g.params["k"])), 3),
                                                        lo=round(float(np.exp(ci[0])), 3), hi=round(float(np.exp(ci[1])), 3),
                                                        note="descriptive; participant clusters; stage and problem adjusted")
    except Exception as e:
        e2["gee_unchanged_per_prior_ai_failure"] = f"not estimable: {type(e).__name__}: {e}"
    # actions after each AI-attributable failure
    act = collections.Counter(); change = collections.Counter()
    for x in dec:
        if not x["ai_fail"]:
            continue
        nx = by_fail.get(x["next"])
        key = (x["user"], int(x["problem"]))
        later = [s for s in sb[key] if stime[s["submission_id"]] > x["t_next"]]
        t1 = stime[later[0]["submission_id"]] if later else None
        asked = [q for q in reqs.get(key, []) if q[0] > x["t_next"] and (t1 is None or q[0] < t1)]
        if nx:
            act[f"asked_again_{'submitted_unchanged' if nx['use'] == 'unchanged' else 'adapted_or_not_used'}"] += 1
        elif later and asked:
            act["asked_again_no_runnable_code"] += 1
        elif later:
            act["resubmitted_without_asking"] += 1
        else:
            act["no_further_submission"] += 1
        if asked:
            a0 = byrid[x["rid"]]
            change["stage_changed"] += str(asked[0][1]) != str(a0["stage"])
            change["provider_changed"] += str(asked[0][2]) != str(a0["provider"])
            change["n_with_next_request"] += 1
    e2["action_after_ai_failure"] = dict(act); e2["stage_provider_change_at_next_request"] = dict(change)
    e2["ai_attributable_failures"] = int(R.ai_fail.sum())
    res["E5_2"] = e2
    # loops
    loops = []
    for x in sorted(dec, key=lambda x: x["t_fail"]):
        if not x["ai_fail"]:
            continue
        prev = by_next.get(x["fail"])
        if prev and prev["ai_fail"]:
            continue                                         # not a loop start
        L = [x]
        while True:
            nx = by_fail.get(L[-1]["next"])
            if nx and nx["ai_fail"]:
                L.append(nx)
            else:
                break
        nx = by_fail.get(L[-1]["next"])
        key = (L[-1]["user"], int(L[-1]["problem"]))
        later = [s for s in sb[key] if stime[s["submission_id"]] > L[-1]["t_next"]]
        end = ("next_unchanged_accepted" if nx and nx["use"] == "unchanged" else "next_adapted_or_not_used" if nx
               else "further_submission_without_decision" if later else "no_further_submission")
        loops.append(dict(len=len(L), end=end, stages=len({y["stage3"] for y in L}), user=L[0]["user"]))
    LL = pd.DataFrame(loops)
    over = R[(R.use == "unchanged") & (R.next_verdict != "AC")]
    res["E5_3"] = dict(loops=len(LL), participants=int(LL.user.nunique()) if len(LL) else 0,
                       length_distribution=dict(sorted(collections.Counter(LL.len).items())) if len(LL) else {},
                       ai_failures_in_loops_len_ge2=int(LL[LL.len >= 2].len.sum()) if len(LL) else 0,
                       ai_failures_total=int(len(over)),
                       end=dict(collections.Counter(LL.end)) if len(LL) else {},
                       loops_with_stage_change=int((LL.stages > 1).sum()) if len(LL) else 0)

    # ---------- E5.4 ----------
    rows = []
    with_editor = {u for u in edits}
    for x in dec:
        arr = lat.get(x["rid"])
        if arr is None or x["use"] == "not_used":
            continue
        latency = (x["t_next"] - arr).total_seconds()
        e = edits.get(x["user"], [])
        n_ed = sum(1 for t in e if arr < t < x["t_next"])
        rows.append(dict(user=x["user"], cls=x["cls"], k=x["k"], use=x["use"], latency=latency,
                         editor=x["user"] in with_editor, no_edit_fast=(x["use"] == "unchanged" and n_ed == 0 and latency < 60)))
    T = pd.DataFrame(rows)
    q = lambda v: dict(n=int(len(v)), median=round(float(np.median(v)), 1), q1=round(float(np.quantile(v, .25)), 1),
                       q3=round(float(np.quantile(v, .75)), 1)) if len(v) else dict(n=0)
    TE = T[T.editor]
    res["E5_4"] = dict(latency_seconds_all=q(T.latency), negative_latency=int((T.latency < 0).sum()),
                       latency_by_class={c: q(T[T.cls == c].latency) for c in ("correct", "wrong_detectable", "wrong_undetectable")},
                       latency_by_k={str(k): q(T[T.k == k].latency) for k in range(4)},
                       participants_with_editor_events=int(T[T.editor].user.nunique()),
                       no_edit_fast_unchanged=S2.boot_rate(TE[TE.use == "unchanged"].assign(f=TE.no_edit_fast.astype(bool)), "f"),
                       no_edit_fast_by_class={c: S2.boot_rate(TE[(TE.use == "unchanged") & (TE.cls == c)].assign(f=TE.no_edit_fast.astype(bool)), "f")
                                              for c in ("correct", "wrong_detectable", "wrong_undetectable")})

    # ---------- E5.5 ----------
    Rov = R[(R.cls != "correct") & R.used & ~R.next_ok_oracle]
    res["E5_5"] = dict(over_reliance_events=len(Rov), sample_failing=int((Rov.cls == "wrong_detectable").sum()),
                       participants=int(Rov[Rov.cls == "wrong_detectable"].user.nunique()),
                       sample_failing_unchanged_judge_AC=int(((R.cls == "wrong_detectable") & (R.use == "unchanged") & (R.next_verdict == "AC")).sum()),
                       sample_failing_unchanged_total=int(((R.cls == "wrong_detectable") & (R.use == "unchanged")).sum()))

    # ---------- E5.6 ----------
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_curve
    P = [a for a in Sc if cls[a["rid"]] != "wrong_detectable"]
    y = np.array([cls[a["rid"]] == "wrong_undetectable" for a in P], int)
    X = np.array([[S2.stage3(a["stage"]) == "2", S2.stage3(a["stage"]) == "3+"] for a in P], float)
    users = np.array([a["user"] for a in P]); scr = np.zeros(len(P))
    for u in np.unique(users):
        te = users == u
        scr[te] = LogisticRegression(C=1.0, max_iter=2000).fit(X[~te], y[~te]).predict_proba(X[te])[:, 1]
    fpr, tpr, _ = roc_curve(y, scr)
    res["E5_6"] = dict(stage_only_hit_at_fa_0189=round(float(np.interp(0.189, fpr, tpr)), 4),
                       stage_only_hit_at_fa_020=round(float(np.interp(0.20, fpr, tpr)), 4),
                       hgb_hit_at_observed_fa_0189=0.3106,
                       note="stage-only held-out ROC interpolated (LOPO, no nested threshold); hgb value from results.json")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))[:15000])


if __name__ == "__main__":
    main()
