r"""Study 2 analyses RQ1-RQ4. Aggregates only in results/results.json.

  python -I code/study2_analyse.py [--no-bayes]

Inputs (private, outside Git): <STUDY2_DIR>/answers.pkl, decisions.csv, answers_scores.csv; the frozen-oracle scores of
every submission; the handoff zip; the questionnaire responses. No participant identifier, code, prompt or answer is
written to the output; per-participant values appear only as distributions or correlations.
"""
import collections, csv, difflib, json, math, os, pickle, random, sys, zipfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, ts, tok  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

PRIV = cfg.STUDY2_DIR
ZIP = cfg.HANDOFF_ZIP
FROZEN = os.path.join(cfg.AUDIT_DIR, "oracle2_frozen_scores.csv")
LABELS = os.path.join(cfg.AUDIT_DIR, "tlt_labels.csv")
QUEST = cfg.QUESTIONNAIRE_XLSX
QTOOL = HERE
OUT = os.path.join(HERE, "..", "results", "results.json")
KINDS = ("sample", "random", "edge", "large")
SEED, NBOOT = 2026, 2000
BAYES = "--no-bayes" not in sys.argv


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def stage3(s):
    try:
        s = int(s)
    except (TypeError, ValueError):
        return None
    return "1" if s == 1 else "2" if s == 2 else "3+"


def boot_rate(df, num, den_mask=None, unit="user", n=NBOOT, seed=SEED):
    """Rate num/den with a participant-cluster bootstrap 95% interval; df rows are units, num boolean column."""
    x = df if den_mask is None else df[den_mask]
    if len(x) == 0:
        return dict(k=0, n=0, rate=None, lo=None, hi=None)
    k, m = int(x[num].sum()), len(x)
    g = {u: (int(v[num].sum()), len(v)) for u, v in x.groupby(unit)}
    users = list(g)
    rng = random.Random(seed)
    rs = []
    for _ in range(n):
        s = [g[rng.choice(users)] for _ in users]
        tot = sum(b for _, b in s)
        rs.append(sum(a for a, _ in s) / tot if tot else float("nan"))
    rs = sorted(r for r in rs if r == r)
    return dict(k=k, n=m, rate=round(k / m, 4), lo=round(rs[int(0.025 * len(rs))], 4),
                hi=round(rs[int(0.975 * len(rs)) - 1], 4), participants=len(users))


def passes_all(r):
    return all(int(r[f"{k}_passed"]) == int(r[f"{k}_n"]) for k in KINDS) and int(r["compiles"]) == 1


def total_pass(r):
    return sum(int(r[f"{k}_passed"]) for k in KINDS) if int(r["compiles"]) else 0


def main():
    res = {"note": "Study 2 results RQ1-RQ4; aggregates only. 'correct' = correct on the frozen oracle v2."}
    A = pickle.load(open(f"{PRIV}/answers.pkl", "rb"))
    sc = {r["key"]: r for r in csv.DictReader(open(f"{PRIV}/answers_scores.csv"))}
    fz = {r["submission_id"]: r for r in csv.DictReader(open(FROZEN))}
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
    sub = {s["submission_id"]: s for s in subs}
    src = lambda s: open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8", errors="replace").read()

    # ---------- per-answer table ----------
    rows = []
    for a in A:
        f = fz[a["fail"]]
        sev_n = int(f["sample_n"]) + int(f["random_n"])
        sev = (int(f["sample_passed"]) + int(f["random_passed"])) / sev_n if sev_n else None
        row = dict(rid=a["rid"], user=a["user"], problem=a["problem"], fail=a["fail"], t=a["t"], form=a["form"],
                   scorable=a["scorable"], stage=stage3(a["stage"]), provider=(a["provider"] or "").lower(), severity=sev,
                   fail_verdict=a["fail_verdict"], fail_sample_ok=int(f["sample_passed"]) == int(f["sample_n"]),
                   fail_total=total_pass(f), attempt=a["attempt"])
        if a["scorable"]:
            s = sc[a["rid"]]
            row.update(correct=passes_all(s), sample_ok=int(s["compiles"]) == 1 and int(s["sample_passed"]) == int(s["sample_n"]),
                       total=total_pass(s), large_timeouts=int(s["large_timeouts"]), compiles_here=int(s["compiles"]))
            row["cls"] = "correct" if row["correct"] else ("wrong_undetectable" if row["sample_ok"] else "wrong_detectable")
            row["change"] = ("correct" if row["correct"] else "improvement" if row["total"] > row["fail_total"]
                             else "unchanged" if row["total"] == row["fail_total"] else "regression")
        rows.append(row)
    D = pd.DataFrame(rows)
    D["scorable"] = D.scorable.astype(bool)
    S = D[D.scorable].copy()
    S["correct"] = S.correct.astype(bool); S["sample_ok"] = S.sample_ok.astype(bool)
    res["counts"] = dict(answers=len(D), scorable=len(S), participants=D.user.nunique(),
                         scorable_participants=S.user.nunique(), failures_with_scorable=S.fail.nunique())

    # ---------- RQ1 ----------
    rq1 = {}
    rq1["correct"] = boot_rate(S, "correct")
    rq1["classes"] = dict(collections.Counter(S.cls))
    rq1["change_vs_failed_program"] = dict(collections.Counter(S.change))
    rq1["sample_check"] = dict(wrong=int((~S.correct).sum()), wrong_detectable=int((S.cls == "wrong_detectable").sum()),
                               wrong_undetectable=int((S.cls == "wrong_undetectable").sum()))
    D["runnable"] = D.scorable
    D["delivered_fix"] = D.scorable & D["correct"].fillna(False).astype(bool)
    rq1["runnable"] = boot_rate(D, "runnable")
    rq1["delivered_fix"] = boot_rate(D, "delivered_fix")
    for g in ("stage", "provider"):
        rq1[f"correct_by_{g}"] = {str(k): boot_rate(S[S[g] == k], "correct") for k in sorted(S[g].dropna().unique())}
        rq1[f"runnable_by_{g}"] = {str(k): boot_rate(D[D[g] == k], "runnable") for k in sorted(D[g].dropna().unique())}
        rq1[f"class_by_{g}"] = {str(k): dict(collections.Counter(S[S[g] == k].cls)) for k in sorted(S[g].dropna().unique())}
    multi = S.groupby("user").provider.nunique()
    rq1["participants_with_scorable_answers_from_ge2_providers"] = int((multi >= 2).sum())
    wp = []
    for u in multi[multi >= 2].index:
        x = S[S.user == u]
        r = x.groupby("provider").correct.mean()
        wp.append({p: float(v) for p, v in r.items()})
    rq1["within_participant_provider_correct_rates_mean"] = {p: round(float(np.mean([w[p] for w in wp if p in w])), 4)
                                                            for p in ("openai", "anthropic", "google")
                                                            if any(p in w for w in wp)}
    if BAYES:
        M = S.assign(y=S.correct.astype(int), severity=S.severity.fillna(S.severity.median()),
                     stage_2=(S.stage == "2").astype(int), stage_3plus=(S.stage == "3+").astype(int),
                     provider_anthropic=(S.provider == "anthropic").astype(int), provider_google=(S.provider == "google").astype(int))
        rq1["model_R1"] = bayes_logit(M, "y ~ stage_2 + stage_3plus + provider_anthropic + provider_google + severity"
                                         " + (1|user) + (1|problem) + (1|fail)", {})
        rq1["model_R1"]["reference_levels"] = "stage 1, provider OpenAI (explicit indicator columns)"
    res["RQ1"] = rq1

    # ---------- RQ2 ----------
    dec = list(csv.DictReader(open(f"{PRIV}/decisions.csv")))
    cls = dict(zip(S.rid, S.cls))
    R = []
    for x in dec:
        c = cls[x["attributed_rid"]] if x["use"] != "not_used" else cls[x["last_rid"]]
        nxt_ok = passes_all(fz[x["next"]])
        R.append(dict(rid=x["attributed_rid"] if x["use"] != "not_used" else x["last_rid"],
                      user=x["user"], problem=x["problem"], rule=x["rule"], use=x["use"], cls=c, next_correct=nxt_ok,
                      next_verdict=x["next_verdict"], sim=float(x["sim"])))
    R = pd.DataFrame(R)
    R = R[R.rule != "ambiguous"].copy()
    used = R.use.isin(["unchanged", "adapted"])
    wrong = R.cls != "correct"

    def cat(r):
        u = r.use in ("unchanged", "adapted")
        if r.cls != "correct":
            return ("corrective_adaptation" if r.next_correct else "over_reliance") if u else "appropriate_rejection"
        if u:
            return "appropriate_use" if r.next_correct else "damaging_adaptation"
        return "alternative_correct_solution" if r.next_correct else "under_reliance"
    R["category"] = R.apply(cat, axis=1)
    rq2 = dict(decisions_excl_ambiguous=len(R), ambiguous=sum(1 for x in dec if x["rule"] == "ambiguous"))
    rq2["table_18"] = {f"{c}|{u}|{'next_correct' if nc else 'next_not_correct'}": int(v)
                       for (c, u, nc), v in R.groupby(["cls", "use", "next_correct"]).size().items()}
    rq2["categories"] = dict(collections.Counter(R.category))
    for c in ("over_reliance", "under_reliance", "appropriate_use", "appropriate_rejection", "corrective_adaptation",
              "damaging_adaptation", "alternative_correct_solution"):
        R[c] = R.category == c
        rq2[f"rate_{c}"] = boot_rate(R, c)
    R["used_unchanged"] = R.use == "unchanged"
    R["used"] = used
    for c in ("wrong_detectable", "wrong_undetectable", "correct"):
        rq2[f"use_given_{c}"] = boot_rate(R, "used", R.cls == c)
        rq2[f"unchanged_given_{c}"] = boot_rate(R, "used_unchanged", R.cls == c)
    rq2["over_reliance_detectable"] = boot_rate(R, "over_reliance", R.cls == "wrong_detectable")
    rq2["over_reliance_undetectable"] = boot_rate(R, "over_reliance", R.cls == "wrong_undetectable")
    # gate G2 on the D5 cells
    oc = R[wrong & (R.use == "unchanged")]
    ucell = R[(R.cls == "correct") & ~used]
    ocd = R[(R.cls == "wrong_detectable") & (R.use == "unchanged")]
    rq2["G2"] = dict(over_reliance_cell=dict(n=len(oc), participants=oc.user.nunique()),
                     over_reliance_cell_detectable=dict(n=len(ocd), participants=ocd.user.nunique()),
                     under_reliance_cell=dict(n=len(ucell), participants=ucell.user.nunique()),
                     passed=bool(len(oc) >= 30 and oc.user.nunique() >= 8 and len(ucell) >= 30 and ucell.user.nunique() >= 8))
    per = R.groupby("user").agg(nc=("cls", lambda s: (s == "correct").sum()), nwd=("cls", lambda s: (s == "wrong_detectable").sum()))
    rq2["informative_participants"] = int(((per.nc >= 3) & (per.nwd >= 3)).sum())
    rq2["informative_participants_pooled_wrong"] = int(((per.nc >= 3) & (R.groupby("user").apply(lambda v: (v.cls != "correct").sum()) >= 3)).sum())
    # adapted: edit effect
    ad = [x for x in dec if x["use"] == "adapted"]
    eff = collections.Counter()
    for x in ad:
        a_tot = total_pass(sc[x["attributed_rid"]]); n_tot = total_pass(fz[x["next"]])
        eff["improved" if n_tot > a_tot else "neutral" if n_tot == a_tot else "damaged"] += 1
    rq2["edit_effect_adapted"] = dict(eff)
    rq2["G1"] = dict(adapted=len(ad), participants=len({x["user"] for x in ad}), passed=len(ad) >= 50)
    # oracle error on AI answers: unchanged-used answers, judge verdict of the submission vs oracle class
    uu = R[R.use == "unchanged"]
    rq2["oracle_vs_judge_unchanged"] = dict(
        n=len(uu), oracle_correct_judge_AC=int(((uu.cls == "correct") & (uu.next_verdict == "AC")).sum()),
        oracle_correct_judge_not_AC=int(((uu.cls == "correct") & (uu.next_verdict != "AC")).sum()),
        oracle_wrong_judge_AC=int(((uu.cls != "correct") & (uu.next_verdict == "AC")).sum()),
        oracle_wrong_judge_not_AC=int(((uu.cls != "correct") & (uu.next_verdict != "AC")).sum()),
        judge_verdicts_of_oracle_correct_unchanged_submissions=dict(collections.Counter(uu[uu.next_correct].next_verdict)),
        judge_verdicts_by_problem_not_AC=dict(collections.Counter(str(p) for p in uu[uu.next_correct & (uu.next_verdict != "AC")].problem)))
    # sensitivity: last-answer rule and thresholds
    sens = {}
    lastR = []
    for x in dec:
        s_last = None
        for a in A:
            if a["rid"] == x["last_rid"]:
                s_last = a.get("sim_next")
        u = "unchanged" if s_last >= 0.99 else "adapted" if s_last >= 0.80 else "not_used"
        lastR.append(dict(user=x["user"], use=u, cls=cls[x["last_rid"]]))
    L = pd.DataFrame(lastR)
    sens["last_answer_rule_use"] = dict(collections.Counter(L.use))
    sens["last_answer_rule_correct_not_used"] = int(((L.cls == "correct") & (L.use == "not_used")).sum())
    for th_u, th_a in ((0.95, 0.80), (0.99, 0.70)):
        u2 = R.sim.apply(lambda s: "unchanged" if s >= th_u else "adapted" if s >= th_a else "not_used")
        u2 = u2.where(R.rule != "not_used", "not_used")
        sens[f"use_at_{th_u}_{th_a}"] = dict(collections.Counter(u2))
    rq2["sensitivity"] = sens
    res["RQ2"] = rq2

    # ---------- RQ3 ----------
    try:
        res["RQ3"] = rq3(R, A)
    except Exception as e:                       # questionnaire file missing or unreadable
        res["RQ3"] = dict(error=f"{type(e).__name__}: {e}")

    # ---------- RQ4 ----------
    res["RQ4"] = rq4(D, A, sub, src)
    if os.path.exists(f"{PRIV}/rq4_flags.pkl") and res["RQ4"].get("G4", {}).get("passed"):
        F4 = pickle.load(open(f"{PRIV}/rq4_flags.pkl", "rb"))
        fl = dict(zip(F4.rid, F4.flag_lopo_hgb20))
        ov = R[R.over_reliance]
        res["RQ4"]["warning_eligibility"] = dict(
            over_reliance_events=len(ov),
            flagged_by_sample_check=int((ov.cls == "wrong_detectable").sum()),
            undetectable=int((ov.cls == "wrong_undetectable").sum()),
            undetectable_flagged_by_model_lopo_fa20=int(sum(bool(fl.get(r, False)) for r in ov[ov.cls == "wrong_undetectable"].rid)),
            note="eligibility for a timely warning, not prevention; participants never saw a warning")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))[:20000])


FIX = ("stage_2", "stage_3plus", "provider_anthropic", "provider_google", "severity")


def bayes_logit(df, formula, refs, link="logit"):
    import bambi as bmb, arviz as az
    df = df.copy()
    for k, v in refs.items():
        levels = [v] + sorted(x for x in df[k].dropna().unique() if x != v)
        df[k] = pd.Categorical(df[k], categories=levels)
    pri = {"Intercept": bmb.Prior("Normal", mu=0, sigma=2.5), "common": bmb.Prior("Normal", mu=0, sigma=1.5)}
    m = bmb.Model(formula, df, family="bernoulli", link=link,
                  priors={"Intercept": pri["Intercept"], **{t: pri["common"] for t in FIX}})
    out = dict(formula=formula, n=len(df))
    for attempt in ("default", "noncentered"):
        idata = m.fit(draws=2000, tune=2000, chains=4, target_accept=0.95, random_seed=SEED, progressbar=False)
        s = az.summary(idata, var_names=list(FIX), ci_prob=0.95, kind="all")
        div = int(idata.sample_stats["diverging"].sum())
        ok = float(s["r_hat"].max()) <= 1.01 and float(s["ess_bulk"].min()) >= 400 and div <= 0.005 * 8000
        if ok:
            break
        m = bmb.Model(formula, df, family="bernoulli", link=link, noncentered=True,
                      priors={"Intercept": pri["Intercept"], **{t: pri["common"] for t in FIX}})
    out.update(converged=ok, divergences=div, max_rhat=float(s["r_hat"].max()), min_ess=float(s["ess_bulk"].min()))
    post = idata.posterior
    coefs = {}
    for v in FIX:
        a = post[v]
        dims = [x for x in a.dims if x not in ("chain", "draw")]
        if dims:
            for lv in a[dims[0]].values:
                x = a.sel({dims[0]: lv}).values.ravel()
                coefs[f"{v}[{lv}]"] = dict(OR=round(float(np.exp(np.median(x))), 3), lo=round(float(np.exp(np.quantile(x, .025))), 3),
                                          hi=round(float(np.exp(np.quantile(x, .975))), 3), p_gt1=round(float((x > 0).mean()), 3))
        else:
            x = a.values.ravel()
            coefs[v] = dict(OR=round(float(np.exp(np.median(x))), 3), lo=round(float(np.exp(np.quantile(x, .025))), 3),
                            hi=round(float(np.exp(np.quantile(x, .975))), 3), p_gt1=round(float((x > 0).mean()), 3))
    out["coefficients"] = coefs
    return out


def spearman_boot(x, y, n=10000, seed=SEED):
    from scipy.stats import spearmanr
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 5:
        return dict(n=int(len(x)), rho=None)
    rho = spearmanr(x, y).statistic
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        i = rng.integers(0, len(x), len(x))
        if len(set(x[i])) > 1 and len(set(y[i])) > 1:
            bs.append(spearmanr(x[i], y[i]).statistic)
    return dict(n=int(len(x)), rho=round(float(rho), 3), lo=round(float(np.quantile(bs, .025)), 3),
                hi=round(float(np.quantile(bs, .975)), 3))


def rq3(R, A):
    sys.path.insert(0, QTOOL)
    import analyze_questionnaire as aq
    from pathlib import Path
    data = aq.load(Path(QUEST))
    ids = []
    for v in data["A1"]:
        s = str(v).strip() if v is not None else ""
        ids.append(f"E{int(s):03d}" if s.isdigit() else None)
    q = {}
    for j, pid in enumerate(ids):
        if pid is None:
            continue
        g = lambda it: aq.parse(data[it][j])
        lik = lambda it: (g(it)[0] if isinstance(g(it), list) and len(g(it)) == 1 and 1 <= g(it)[0] <= 5 else np.nan)
        d3 = g("D3") if isinstance(g("D3"), list) else []
        d1 = g("D1")
        q[pid] = dict(D3_tested=float(3 in d3) if d3 else np.nan, D3_checks=float(len({1, 2, 3, 5} & set(d3))) if d3 else np.nan,
                      F3=lik("F3"), D4=lik("D4"), C4=lik("C4"),
                      D1=(d1[0] if isinstance(d1, list) and len(d1) == 1 else ("multiple" if isinstance(d1, list) else None)))
    # behavior
    z = zipfile.ZipFile(ZIP)
    beh = collections.defaultdict(dict)
    wd = R[R.cls == "wrong_detectable"]
    for u, v in wd.groupby("user"):
        beh[u]["B_check"] = 1 - v.over_reliance.mean()
    usedR = R[R.use.isin(["unchanged", "adapted"])]
    for u, v in usedR.groupby("user"):
        beh[u]["B_unchanged"] = (v.use == "unchanged").mean()
    lab = list(csv.DictReader(open(LABELS, encoding="utf-8")))
    for u in {r["participant"] for r in lab}:
        L = [float(r["best_similarity"]) for r in lab if r["participant"] == u]
        beh[u]["B_reuse"] = sum(x >= 0.99 for x in L) / len(L)
    app = collections.Counter()
    for r in jsonl(z, "data/analysis/telemetry.jsonl"):
        if r["type"] == "edit_proposal" and r["payload"].get("outcome") == "applied":
            app[r["participant"]] += 1
    reqs, seen = collections.defaultdict(list), set()
    for r in jsonl(z, "data/analysis/proxy_calls.jsonl"):
        if r.get("operation") not in (None, "None") or r.get("status") != "success" or not r.get("created_at"):
            continue
        if r.get("call_index") not in ("primary", None) or r["chat_request_id"] in seen:
            continue
        n = pno(r.get("problem_id"))
        if n is None:
            continue
        seen.add(r["chat_request_id"])
        txt = ""
        for m in reversed(r.get("messages") or []):
            if isinstance(m, dict) and m.get("role") == "user":
                c = m.get("content")
                txt = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
                break
        reqs[(r["participant"], n)].append((ts(r["created_at"]), txt))
    seek, fill = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for (u, n), L in reqs.items():
        L.sort()
        if len(L) >= 6:
            seek[u][1] += 1
            seek[u][0] += len(L) in (6, 11, 16, 21)
        prev = None
        for i, (_, t) in enumerate(L, 1):
            filler = len(t.strip()) < 20 or (prev is not None and difflib.SequenceMatcher(None, prev, t).ratio() >= 0.90)
            pos = 0 if (i % 5) in (4, 0) and i <= 20 else 1
            fill[u][pos][0] += filler; fill[u][pos][1] += 1
            prev = t
    for u in {k[0] for k in reqs}:
        beh[u]["B_apply"] = app.get(u, 0)
        if seek[u][1]:
            beh[u]["B_unlock_seek"] = seek[u][0] / seek[u][1]
        a, b = fill[u]
        if a[1] and b[1]:
            beh[u]["B_unlock_filler"] = a[0] / a[1] - b[0] / b[1]
    P = [u for u in q if u in beh]
    col = lambda k, src: [src[u].get(k, np.nan) if isinstance(src[u], dict) else np.nan for u in P]
    out = dict(linked=len(P))
    for qi, bi in (("F3", "B_reuse"), ("D4", "B_unchanged"), ("C4", "B_unlock_seek"), ("C4", "B_unlock_filler"),
                   ("D3_checks", "B_check")):
        out[f"{qi}_vs_{bi}"] = spearman_boot([q[u][qi] for u in P], [beh[u].get(bi, np.nan) for u in P])
    grp = collections.defaultdict(list)
    for u in P:
        grp[q[u]["D3_tested"]].append(beh[u].get("B_check", np.nan))
    out["D3_tested_groups_B_check"] = {str(k): dict(n=len([x for x in v if x == x]), median=(round(float(np.nanmedian(v)), 3)
                                       if len([x for x in v if x == x]) >= 3 else "suppressed (n<3)")) for k, v in grp.items()}
    labels = {1: "Apply button", 2: "Copying or retyping", 3: "Both about equally", 4: "Did not incorporate", "multiple": "several options"}
    g1 = collections.defaultdict(list)
    for u in P:
        g1[labels.get(q[u]["D1"], str(q[u]["D1"]))].append(beh[u].get("B_apply", np.nan))
    out["D1_groups_B_apply"] = {k: dict(n=len(v), median=(float(np.nanmedian(v)) if len(v) >= 3 else "suppressed (n<3)"))
                                for k, v in g1.items()}
    out["aggregate_context"] = dict(
        D3_tested_share=round(float(np.nanmean([q[u]["D3_tested"] for u in P])), 3),
        F3_agree_share=round(float(np.nanmean([q[u]["F3"] >= 4 for u in P if q[u]["F3"] == q[u]["F3"]])), 3),
        D4_agree_share=round(float(np.nanmean([q[u]["D4"] >= 4 for u in P if q[u]["D4"] == q[u]["D4"]])), 3),
        C4_agree_share=round(float(np.nanmean([q[u]["C4"] >= 4 for u in P if q[u]["C4"] == q[u]["C4"]])), 3))
    return out


def rq4(D, A, sub, src):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import roc_auc_score
    byrid = {a["rid"]: a for a in A}
    S = D[D.scorable].copy()
    S["correct"] = S.correct.astype(bool); S["sample_ok"] = S.sample_ok.astype(bool)
    P = S[S.sample_ok].copy()
    P["y"] = (~P.correct).astype(int)
    wu = P[P.y == 1]
    g4 = dict(wrong_sample_passing=len(wu), participants=wu.user.nunique(), problems=wu.problem.nunique())
    g4["passed"] = bool(len(wu) >= 40 and wu.user.nunique() >= 8 and wu.problem.nunique() >= 5)
    out = dict(G4=g4, population=len(P), correct_in_population=int((P.y == 0).sum()))
    if not g4["passed"]:
        return out
    # features
    feat = []
    for _, r in P.iterrows():
        a = byrid[r.rid]
        ftok = tok(src(sub[r.fail]))
        ptok = tok(a["program"])
        earlier = [b for b in A if b["scorable"] and b["user"] == a["user"] and b["problem"] == a["problem"] and b["t"] < a["t"]]
        same_fail = [b for b in earlier if b["fail"] == a["fail"]]
        sims = [sim(ptok, tok(b["program"])) for b in earlier]
        sims_f = [sim(ptok, tok(b["program"])) for b in same_fail]
        feat.append(dict(stage2=float(r.stage == "2"), stage3=float(r.stage == "3+"), anth=float(r.provider == "anthropic"),
                         goog=float(r.provider == "google"), proposal=float(r.form != "full_program"), length=len(ptok),
                         edit_dist=1 - sim(ptok, ftok), tle=float(r.fail_verdict == "TLE"), fail_sample_ok=float(r.fail_sample_ok),
                         attempt=float(a["attempt"] or np.nan), n_earlier_fail=len(same_fail), n_earlier_thread=len(earlier),
                         max_sim_fail=max(sims_f) if sims_f else np.nan, mean_sim_fail=float(np.mean(sims_f)) if sims_f else np.nan,
                         max_sim_thread=max(sims) if sims else np.nan, has_earlier=float(bool(sims))))
    X = pd.DataFrame(feat)
    y = P.y.values
    users = P.user.values
    probs = P.problem.values

    def make(kind):
        if kind == "hgb":
            return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20,
                                                  class_weight="balanced", random_state=SEED)
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    cols = {"hgb": list(X.columns), "lr": list(X.columns), "stage": ["stage2", "stage3"], "formsize": ["proposal", "length"]}

    def nested(kind, groups, fa=0.20):
        cs = cols[kind]
        sc = np.full(len(y), np.nan); flag = np.zeros(len(y), bool)
        for g in np.unique(groups):
            te = groups == g; tr = ~te
            if len(np.unique(y[tr])) < 2:
                continue
            m = make("hgb" if kind == "hgb" else "lr").fit(X.loc[tr, cs], y[tr])
            sc[te] = m.predict_proba(X.loc[te, cs])[:, 1]
            inner = np.full(tr.sum(), np.nan)
            gi = groups[tr]; Xi = X.loc[tr, cs]; yi = y[tr]
            for h in np.unique(gi):
                t2 = gi == h
                if len(np.unique(yi[~t2])) < 2:
                    continue
                m2 = make("hgb" if kind == "hgb" else "lr").fit(Xi[~t2], yi[~t2])
                inner[t2] = m2.predict_proba(Xi[t2])[:, 1]
            neg = inner[(yi == 0) & ~np.isnan(inner)]
            thr = np.quantile(neg, 1 - fa) if len(neg) else np.inf
            flag[te] = sc[te] > thr
        return sc, flag

    def metrics(sc, flag, groups):
        ok = ~np.isnan(sc)
        hit = flag[(y == 1) & ok].mean(); fa = flag[(y == 0) & ok].mean()
        prec = (flag & (y == 1))[ok].sum() / max(1, flag[ok].sum())
        return dict(auc=round(float(roc_auc_score(y[ok], sc[ok])), 4), hit=round(float(hit), 4), false_alarm=round(float(fa), 4),
                    precision=round(float(prec), 4), warnings_per_answer=round(float(flag[ok].mean()), 4))
    res = {}
    store = {}
    for split, groups in (("leave_one_participant_out", users), ("leave_one_problem_out", probs)):
        res[split] = {}
        for kind in ("hgb", "lr", "stage", "formsize"):
            for fa in (0.10, 0.20):
                sc, flag = nested(kind, groups, fa)
                res[split][f"{kind}_fa{int(fa*100)}"] = metrics(sc, flag, groups)
                store[(split, kind, fa)] = (sc, flag)
    # C4: LOPO, hgb at 20% vs max(observed FA, stage-only hit); participant bootstrap
    sc_h, fl_h = store[("leave_one_participant_out", "hgb", 0.20)]
    sc_s, fl_s = store[("leave_one_participant_out", "stage", 0.20)]
    rng = np.random.default_rng(SEED)
    U = np.unique(users)
    def stat(idx):
        yy, fh, fs = y[idx], fl_h[idx], fl_s[idx]
        if (yy == 1).sum() == 0 or (yy == 0).sum() == 0:
            return np.nan
        return fh[yy == 1].mean() - max(fh[yy == 0].mean(), fs[yy == 1].mean())
    obs = stat(np.arange(len(y)))
    bs = []
    for _ in range(NBOOT):
        pick = rng.choice(U, len(U))
        idx = np.concatenate([np.where(users == u)[0] for u in pick])
        v = stat(idx)
        if v == v:
            bs.append(v)
    res["C4"] = dict(difference=round(float(obs), 4), lo=round(float(np.quantile(bs, .025)), 4),
                     hi=round(float(np.quantile(bs, .975)), 4), confirmed=bool(np.quantile(bs, .025) > 0))
    out.update(res)
    out["features"] = list(X.columns)
    P["flag_lopo_hgb20"] = fl_h
    pickle.dump(P[["rid", "flag_lopo_hgb20", "y"]], open(f"{PRIV}/rq4_flags.pkl", "wb"))
    return out


if __name__ == "__main__":
    main()
