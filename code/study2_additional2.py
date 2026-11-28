r"""Study 2, additional checks C1-C6 and perspectives P.

  python -I code/study2_additional2.py

C1 timing with created_at as answer arrival (the proxy builds its record just after the call ends)
C2 other ways of adapting after a rejected unchanged AI submission (stage, provider, waiting, editing) vs other failures
C3 acceptance by earlier rejections with participant random effects (Bayesian) and within-person comparison
C4 participant-cluster intervals for the actions after a rejection
C5 count reconciliations (seven categories per truth source; 172 vs 174; 413 vs 470)
C6 stage-only warning rule: its real operating points
P  perspectives: participant, problem, language, configuration, weighting, problem-cluster bootstrap, loop survival
Aggregates only: results/additional_2.json (participants appear only as anonymous ranks).
"""
import collections, csv, json, os, pickle, random, sys, zipfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, ts  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import study2_analyse as S2  # noqa: E402

PRIV = S2.PRIV
OUT = os.path.join(HERE, "..", "results", "additional_2.json")
SEED, NBOOT = 2026, 2000
STAGE = lambda s: S2.stage3(s)


def boot(df, col, unit="user"):
    return S2.boot_rate(df.assign(**{col: df[col].astype(bool)}), col, unit=unit, n=NBOOT)


def q(v):
    v = np.asarray(list(v), float)
    return dict(n=int(len(v)), median=round(float(np.median(v)), 1), q1=round(float(np.quantile(v, .25)), 1),
                q3=round(float(np.quantile(v, .75)), 1)) if len(v) else dict(n=0)


def load():
    A = pickle.load(open(f"{PRIV}/answers.pkl", "rb"))
    byrid = {a["rid"]: a for a in A}
    sc = {r["key"]: r for r in csv.DictReader(open(f"{PRIV}/answers_scores.csv"))}
    fz = {r["submission_id"]: r for r in csv.DictReader(open(S2.FROZEN))}
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
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
    arr, lat_ms, reqs, seen = {}, {}, collections.defaultdict(list), set()
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
        arr[r["chat_request_id"]] = t
        lat_ms[r["chat_request_id"]] = float(r.get("latency_ms") or 0)
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
        x["t_next"], x["t_fail"] = stime[x["next"]], stime[x["fail"]]
        x["stage3"] = STAGE(byrid[x["rid"]]["stage"])
        x["ai_fail"] = x["use"] == "unchanged" and x["next_verdict"] != "AC"
    by_next = {x["next"]: x for x in dec}
    by_fail = {x["fail"]: x for x in dec}
    for x in dec:
        prev = by_next.get(x["fail"])
        x["prev_type"] = "ai_attributable" if prev and prev["ai_fail"] else "other_failure"
    thr = collections.defaultdict(list)
    for x in dec:
        thr[(x["user"], x["problem"])].append(x)
    for L in thr.values():
        L.sort(key=lambda x: x["t_fail"])
        k = 0
        for x in L:
            x["k_raw"] = k; x["k"] = min(k, 3); k += x["ai_fail"]
    return A, byrid, cls, sc, fz, subs, stime, sb, arr, lat_ms, reqs, edits, dec, by_next, by_fail


def main():
    A, byrid, cls, sc, fz, subs, stime, sb, arr, lat_ms, reqs, edits, dec, by_next, by_fail = load()
    R = pd.DataFrame(dec)
    R["unchanged"] = R.use == "unchanged"; R["used"] = R.use != "not_used"
    res = {"note": "Additional checks C1-C6 and perspectives P. Aggregates only."}

    # ---------- C1 timing ----------
    rows, recon = [], collections.Counter()
    with_editor = set(edits)
    for x in dec:
        if x["use"] != "unchanged":
            continue
        recon["unchanged"] += 1
        t0 = arr.get(x["rid"])
        if t0 is None:
            recon["no_proxy_record"] += 1; continue
        dt = (x["t_next"] - t0).total_seconds()
        if x["user"] not in with_editor:
            recon["participant_without_editor_events"] += 1
        n_ed = sum(1 for t in edits.get(x["user"], []) if t0 < t < x["t_next"])
        rows.append(dict(user=x["user"], cls=x["cls"], k=x["k"], dt=dt, lat=lat_ms[x["rid"]] / 1000,
                         editor=x["user"] in with_editor, n_ed=n_ed))
    T = pd.DataFrame(rows)
    TE = T[T.editor].copy()
    TE["fast_no_edit"] = (TE.dt < 60) & (TE.n_ed == 0)
    TE["no_edit"] = TE.n_ed == 0
    res["C1_timing"] = dict(
        definition="decision time = judge submission time - proxy created_at (record built just after the call ended)",
        reconciliation=dict(recon, with_timing=len(T), with_timing_and_editor=len(TE)),
        decision_seconds=q(T.dt), negative=int((T.dt < 0).sum()), negative_over_minus5s=int((T.dt < -5).sum()),
        negative_participants=int(T[T.dt < 0].user.nunique()),
        answer_latency_seconds=q(T.lat),
        decision_seconds_by_class={c: q(T[T.cls == c].dt) for c in ("correct", "wrong_detectable", "wrong_undetectable")},
        decision_seconds_by_k={str(k): q(T[T.k == k].dt) for k in range(4)},
        within_60s_no_edit=boot(TE, "fast_no_edit"), no_edit_any_time=boot(TE, "no_edit"),
        within_60s_no_edit_by_class={c: boot(TE[TE.cls == c], "fast_no_edit")
                                     for c in ("correct", "wrong_detectable", "wrong_undetectable")},
        note="negative values: the submission is stamped by the judge server, created_at by the proxy; the clocks are not "
             "synchronised, so the sign of small differences is not interpretable")

    # ---------- C2 adaptation in other forms ----------
    ev = []
    allpairs = collections.Counter()
    for key, L in reqs.items():
        for a, b in zip(L, L[1:]):
            allpairs["n"] += 1; allpairs["stage_changed"] += str(a[1]) != str(b[1])
            allpairs["provider_changed"] += str(a[2]) != str(b[2])
    for x in dec:
        key = (x["user"], int(x["problem"]))
        tf = x["t_fail"]
        before = [r for r in reqs.get(key, []) if r[0] < tf]
        after = [r for r in reqs.get(key, []) if tf < r[0] < x["t_next"]]
        if not before or not after:
            continue
        nx = after[0]
        n_ed = sum(1 for t in edits.get(x["user"], []) if tf < t < x["t_next"])
        ev.append(dict(user=x["user"], type=x["prev_type"], stage_changed=str(nx[1]) != str(before[-1][1]),
                       provider_changed=str(nx[2]) != str(before[-1][2]), wait=(nx[0] - tf).total_seconds(),
                       edited=n_ed > 0, editor=x["user"] in with_editor, unchanged=x["use"] == "unchanged",
                       k=x["k"]))
    E = pd.DataFrame(ev)
    c2 = dict(base_rate_consecutive_requests=dict(allpairs),
              note="failure -> next request on the same problem; the previous request is the last one before the failure")
    for t in ("ai_attributable", "other_failure"):
        e = E[E.type == t]
        c2[t] = dict(n=len(e), participants=int(e.user.nunique()), stage_changed=boot(e, "stage_changed"),
                     provider_changed=boot(e, "provider_changed"), wait_to_next_request_s=q(e.wait),
                     edited_before_next_submission=boot(e[e.editor], "edited"), unchanged_next=boot(e, "unchanged"))
    c2["stage_changed_by_k"] = {str(k): boot(E[E.k == k], "stage_changed") for k in range(4)}
    try:
        import statsmodels.api as sm, statsmodels.formula.api as smf
        for col in ("stage_changed", "provider_changed"):
            g = smf.gee(f"{col} ~ ai", "user", E.assign(**{col: E[col].astype(int), "ai": (E.type == "ai_attributable").astype(int)}),
                        family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
            ci = g.conf_int().loc["ai"]
            c2[f"gee_{col}_ai_vs_other"] = dict(OR=round(float(np.exp(g.params["ai"])), 3), lo=round(float(np.exp(ci[0])), 3),
                                                hi=round(float(np.exp(ci[1])), 3))
    except Exception as e:  # pragma: no cover
        c2["gee"] = f"not estimable: {e}"
    res["C2_other_adaptation"] = c2

    # ---------- C3 acceptance by earlier rejections ----------
    c3 = {}
    import statsmodels.api as sm, statsmodels.formula.api as smf
    Rm = R.assign(unchanged_i=R.unchanged.astype(int), kf=R.k.astype(float))
    for cs in ("Independence", "Exchangeable"):
        g = smf.gee("unchanged_i ~ kf + C(stage3) + C(problem)", "user", Rm, family=sm.families.Binomial(),
                    cov_struct=getattr(sm.cov_struct, cs)()).fit()
        ci = g.conf_int().loc["kf"]
        c3[f"gee_{cs.lower()}"] = dict(OR=round(float(np.exp(g.params["kf"])), 3), lo=round(float(np.exp(ci[0])), 3),
                                       hi=round(float(np.exp(ci[1])), 3))
    try:
        import bambi as bmb, arviz as az
        df = Rm[["unchanged_i", "kf", "stage3", "user", "problem"]].copy()
        df["s2"] = (df.stage3 == "2").astype(int); df["s3"] = (df.stage3 == "3+").astype(int)
        df["problem"] = df.problem.astype(str)
        m = bmb.Model("unchanged_i ~ kf + s2 + s3 + (1|user) + (1|problem)", df, family="bernoulli",
                      priors={"Intercept": bmb.Prior("Normal", mu=0, sigma=2.5), "kf": bmb.Prior("Normal", mu=0, sigma=1.5),
                              "s2": bmb.Prior("Normal", mu=0, sigma=1.5), "s3": bmb.Prior("Normal", mu=0, sigma=1.5)},
                      noncentered=True)
        idata = m.fit(draws=2000, tune=2000, chains=4, target_accept=0.95, random_seed=SEED, progressbar=False)
        s = az.summary(idata, var_names=["kf"], kind="all")
        x = idata.posterior["kf"].values.ravel()
        c3["bayes_random_effects"] = dict(OR=round(float(np.exp(np.median(x))), 3), lo=round(float(np.exp(np.quantile(x, .025))), 3),
                                          hi=round(float(np.exp(np.quantile(x, .975))), 3), p_gt1=round(float((x > 0).mean()), 3),
                                          rhat=round(float(s["r_hat"].max()), 4),
                                          divergences=int(idata.sample_stats["diverging"].sum()),
                                          formula="unchanged ~ k + stage + (1|participant) + (1|problem)")
    except Exception as e:  # pragma: no cover
        c3["bayes_random_effects"] = f"not estimable: {type(e).__name__}: {e}"
    within = collections.Counter()
    for u, g in R.groupby("user"):
        a, b = g[g.k == 0], g[g.k >= 1]
        if len(a) and len(b):
            ra, rb = a.unchanged.mean(), b.unchanged.mean()
            within["higher_after_rejection" if rb > ra else "lower_after_rejection" if rb < ra else "equal"] += 1
    from scipy.stats import binomtest
    hi_, lo_ = within["higher_after_rejection"], within["lower_after_rejection"]
    c3["within_person_k0_vs_k1plus"] = dict(within, sign_test_p=round(binomtest(hi_, hi_ + lo_).pvalue, 4) if hi_ + lo_ else None)
    # selection: share of k>=3 decisions contributed by the participants with the most of them
    k3 = R[R.k >= 3].groupby("user").size().sort_values(ascending=False)
    c3["k3_concentration"] = dict(decisions=int(k3.sum()), participants=int(len(k3)),
                                  top3_share=round(float(k3.head(3).sum() / k3.sum()), 4) if len(k3) else None)
    res["C3_acceptance_by_rejections"] = c3

    # ---------- C4 actions after a rejection, with intervals ----------
    acts = []
    for x in dec:
        if not x["ai_fail"]:
            continue
        nx = by_fail.get(x["next"])
        key = (x["user"], int(x["problem"]))
        later = [s for s in sb[key] if stime[s["submission_id"]] > x["t_next"]]
        t1 = stime[later[0]["submission_id"]] if later else None
        asked = [r for r in reqs.get(key, []) if r[0] > x["t_next"] and (t1 is None or r[0] < t1)]
        a = ("asked_again_submitted_unchanged" if nx and nx["use"] == "unchanged" else "asked_again_adapted_or_not_used" if nx
             else "asked_again_no_runnable_code" if later and asked else "resubmitted_without_asking" if later
             else "no_further_submission")
        acts.append(dict(user=x["user"], a=a))
    AC = pd.DataFrame(acts)
    res["C4_actions_after_rejection"] = {a: boot(AC.assign(f=AC.a == a), "f") for a in sorted(AC.a.unique())}

    # ---------- C5 reconciliation ----------
    ov = R[(R.cls != "correct") & R.used & ~R.next_ok_oracle]
    res["C5_reconciliation"] = dict(
        over_reliance_oracle=len(ov),
        over_reliance_sample_failing=int((ov.cls == "wrong_detectable").sum()),
        of_which_unchanged=int(((ov.cls == "wrong_detectable") & (ov.use == "unchanged")).sum()),
        of_which_adapted=int(((ov.cls == "wrong_detectable") & (ov.use == "adapted")).sum()),
        sample_failing_unchanged_all=int(((R.cls == "wrong_detectable") & R.unchanged).sum()),
        sample_failing_unchanged_judge_AC=int(((R.cls == "wrong_detectable") & R.unchanged & (R.next_verdict == "AC")).sum()),
        decisions=len(R), unchanged=int(R.unchanged.sum()), adapted=int((R.use == "adapted").sum()),
        not_used=int((R.use == "not_used").sum()))

    # ---------- C6 stage rule operating points ----------
    Sc = [a for a in A if a["scorable"]]
    P = [a for a in Sc if cls[a["rid"]] != "wrong_detectable"]
    y = np.array([cls[a["rid"]] == "wrong_undetectable" for a in P], bool)
    st = np.array([STAGE(a["stage"]) for a in P])
    pts = []
    for name, flag in (("flag none", np.zeros(len(P), bool)), ("flag stage 3+", st == "3+"),
                       ("flag stage 2 or 3+", st != "1"), ("flag all", np.ones(len(P), bool)),
                       ("flag stage 1 only", st == "1")):
        pts.append(dict(rule=name, hit=round(float(flag[y].mean()), 4), false_alarm=round(float(flag[~y].mean()), 4),
                        flagged=int(flag.sum())))
    res["C6_stage_rule_points"] = dict(positives=int(y.sum()), negatives=int((~y).sum()), points=pts)

    # ---------- P perspectives ----------
    Ad = pd.DataFrame([dict(user=a["user"], problem=a["problem"], stage=STAGE(a["stage"]), provider=a["provider"],
                            lang=a["lang"], correct=cls[a["rid"]] == "correct", cls=cls[a["rid"]]) for a in Sc])
    R["over_oracle"] = (R.cls != "correct") & R.used & ~R.next_ok_oracle
    R["over_strict"] = R.over_oracle.where(~R.unchanged, R.next_verdict != "AC")
    p = {}
    for name, df, col in (("rq1_correct", Ad, "correct"), ("unchanged_use", R, "unchanged"),
                          ("over_reliance_oracle", R, "over_oracle"), ("over_reliance_judge_strict", R, "over_strict")):
        per_u = df.groupby("user")[col].agg(["sum", "count"])
        per_p = df.groupby("problem")[col].agg(["sum", "count"])
        p[name] = dict(pooled=boot(df, col), problem_cluster=boot(df, col, unit="problem"),
                       participant_macro=round(float((per_u["sum"] / per_u["count"]).mean()), 4),
                       problem_macro=round(float((per_p["sum"] / per_p["count"]).mean()), 4),
                       per_participant_sorted=[[int(a), int(b)] for a, b in
                                               sorted(zip(per_u["sum"], per_u["count"]), key=lambda t: t[0] / t[1])],
                       per_problem={str(k): [int(v["sum"]), int(v["count"])] for k, v in per_p.iterrows()})
    p["rq1_by_language"] = {str(l): boot(Ad[Ad.lang == l], "correct") for l in ("C", "C++", "Java")}
    p["rq1_by_stage_provider"] = {f"{s}|{v}": [int(Ad[(Ad.stage == s) & (Ad.provider == v)].correct.sum()),
                                               int(((Ad.stage == s) & (Ad.provider == v)).sum())]
                                  for s in ("1", "2", "3+") for v in ("openai", "anthropic", "google")}
    p["rq1_by_provider"] = {v: boot(Ad[Ad.provider == v], "correct") for v in ("openai", "anthropic", "google")}
    p["rq1_class_by_stage"] = {s: dict(collections.Counter(Ad[Ad.stage == s].cls)) for s in ("1", "2", "3+")}
    p["over_reliance_oracle_by_stage"] = {s: boot(R[R.stage3 == s], "over_oracle") for s in ("1", "2", "3+")}
    p["over_reliance_oracle_by_provider"] = {v: boot(R[R.provider == v], "over_oracle") for v in ("openai", "anthropic", "google")}
    p["unchanged_by_stage"] = {s: boot(R[R.stage3 == s], "unchanged") for s in ("1", "2", "3+")}
    # heatmap: participant (anonymous rank) x problem, over-reliance counts (oracle)
    users = R.groupby("user").over_oracle.sum().sort_values(ascending=False).index.tolist()
    p["heatmap_over_reliance_oracle"] = dict(rows="participants ranked by total (anonymous)", cols=list(range(1, 14)),
                                             counts=[[int(R[(R.user == u) & (R.problem.astype(int) == n)].over_oracle.sum())
                                                      for n in range(1, 14)] for u in users])
    # loop survival
    lens = []
    for x in sorted(dec, key=lambda x: x["t_fail"]):
        if not x["ai_fail"]:
            continue
        prev = by_next.get(x["fail"])
        if prev and prev["ai_fail"]:
            continue
        L = [x]
        while True:
            nx = by_fail.get(L[-1]["next"])
            if nx and nx["ai_fail"]:
                L.append(nx)
            else:
                break
        lens.append(len(L))
    lens = np.array(lens)
    p["loop_survival"] = {str(k): round(float((lens >= k).mean()), 4) for k in range(1, int(lens.max()) + 1)}
    p["loops"] = int(len(lens))
    res["P_perspectives"] = p

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: v for k, v in res.items() if k != "P_perspectives"}, indent=1,
                     default=lambda o: o.item() if hasattr(o, "item") else str(o))[:20000])


if __name__ == "__main__":
    main()
