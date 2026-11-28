r"""Study 2, additional checks M1-M2.

  python -I code/study2_additional6.py

M1 warning rules compared at matched false-alarm rates (held out by participant)
M2 posterior predictive check of the RQ1 model of answer correctness
Aggregates only: results/additional_6.json.
"""
import collections, csv, inspect, json, os, pickle, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import study2_analyse as S2  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "additional_6.json")
SEED, NBOOT = 2026, 2000

A = pickle.load(open(f"{S2.PRIV}/answers.pkl", "rb"))
sc = {r["key"]: r for r in csv.DictReader(open(f"{S2.PRIV}/answers_scores.csv"))}
fz = {r["submission_id"]: r for r in csv.DictReader(open(S2.FROZEN))}
subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
sub = {s["submission_id"]: s for s in subs}
src = lambda s: open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8", errors="replace").read()
rows = []
for a in A:                                     # same per-answer table as study2_analyse.main
    f = fz[a["fail"]]
    sev_n = int(f["sample_n"]) + int(f["random_n"])
    sev = (int(f["sample_passed"]) + int(f["random_passed"])) / sev_n if sev_n else None
    row = dict(rid=a["rid"], user=a["user"], problem=a["problem"], fail=a["fail"], t=a["t"], form=a["form"],
               scorable=a["scorable"], stage=S2.stage3(a["stage"]), provider=(a["provider"] or "").lower(), severity=sev,
               fail_verdict=a["fail_verdict"], fail_sample_ok=int(f["sample_passed"]) == int(f["sample_n"]),
               fail_total=S2.total_pass(f), attempt=a["attempt"])
    if a["scorable"]:
        s = sc[a["rid"]]
        row.update(correct=S2.passes_all(s), sample_ok=int(s["compiles"]) == 1 and int(s["sample_passed"]) == int(s["sample_n"]))
    rows.append(row)
D = pd.DataFrame(rows); D["scorable"] = D.scorable.astype(bool)
res = {}

# ---------- (1) matched false-alarm comparison ----------
code = inspect.getsource(S2.rq4).replace("    out.update(res)\n", "    out.update(res); out['_store'] = store; out['_y'] = y; out['_users'] = users\n", 1)
ns = dict(vars(S2)); exec(code, ns)
R4 = ns["rq4"](D, A, sub, src)
y, users, store = R4["_y"], R4["_users"], R4["_store"]
sh = store[("leave_one_participant_out", "hgb", 0.20)][0]
ss = store[("leave_one_participant_out", "stage", 0.20)][0]
ok = ~np.isnan(sh) & ~np.isnan(ss)


def hr_at(scores, idx, fa):
    """hit rate of score > t, with t chosen on the negatives in idx so that the false-alarm rate is at most fa"""
    neg = np.sort(scores[idx][y[idx] == 0])[::-1]
    k = int(np.floor(fa * len(neg)))
    t = neg[k] if k < len(neg) else -np.inf
    return float((scores[idx][y[idx] == 1] > t).mean()), float((scores[idx][y[idx] == 0] > t).mean())


pts = []
for t in sorted(set(np.round(ss[ok], 10)), reverse=True)[:-1]:
    flag = ss > t
    pts.append(dict(fa=float(flag[ok & (y == 0)].mean()), hr=float(flag[ok & (y == 1)].mean())))
rng = np.random.default_rng(SEED); U = np.unique(users)
match = []
for p in pts:
    idx = np.where(ok)[0]
    hm, fam = hr_at(sh, idx, p["fa"])
    bs = []
    for _ in range(NBOOT):
        pick = rng.choice(U, len(U)); j = np.concatenate([np.where((users == u) & ok)[0] for u in pick])
        if (y[j] == 1).sum() == 0 or (y[j] == 0).sum() == 0:
            continue
        hm_b, _ = hr_at(sh, j, float(((ss[j] > (sorted(set(np.round(ss[ok], 10)), reverse=True)[pts.index(p)])) & (y[j] == 0)).sum() / (y[j] == 0).sum()))
        hs_b = float(((ss[j] > sorted(set(np.round(ss[ok], 10)), reverse=True)[pts.index(p)]) & (y[j] == 1)).sum() / (y[j] == 1).sum())
        bs.append(hm_b - hs_b)
    match.append(dict(stage_fa=round(p["fa"], 4), stage_hr=round(p["hr"], 4), model_hr=round(hm, 4), model_fa=round(fam, 4),
                      difference=round(hm - p["hr"], 4), lo=round(float(np.quantile(bs, .025)), 4), hi=round(float(np.quantile(bs, .975)), 4)))
res["matched_false_alarm"] = dict(
    note="Held out by participant; pooled held-out gradient-boosting scores thresholded at each stage-rule operating point's false-alarm rate; participant bootstrap of the hit-rate difference.",
    population=int(ok.sum()), points=match)

# ---------- (2) posterior predictive check of the RQ1 model ----------
import bambi as bmb, arviz as az  # noqa: E402
S = D[D.scorable].copy(); S["correct"] = S.correct.astype(bool)
M = S.assign(y=S.correct.astype(int), severity=S.severity.fillna(S.severity.median()),
             stage_2=(S.stage == "2").astype(int), stage_3plus=(S.stage == "3+").astype(int),
             provider_anthropic=(S.provider == "anthropic").astype(int), provider_google=(S.provider == "google").astype(int)).reset_index(drop=True)
pri = {"Intercept": bmb.Prior("Normal", mu=0, sigma=2.5), **{t: bmb.Prior("Normal", mu=0, sigma=1.5) for t in S2.FIX}}
m = bmb.Model("y ~ stage_2 + stage_3plus + provider_anthropic + provider_google + severity + (1|user) + (1|problem) + (1|fail)",
              M, family="bernoulli", priors=pri)
idata = m.fit(draws=2000, tune=2000, chains=4, target_accept=0.95, random_seed=SEED, progressbar=False)
m.predict(idata, kind="response", random_seed=SEED)
yrep = idata.posterior_predictive["y"].values.reshape(-1, len(M))     # draws x answers


def ppc(mask):
    obs = int(M.y[mask].sum()); sim = yrep[:, mask].sum(1)
    lo, hi = np.quantile(sim, [.025, .975])
    return dict(observed=obs, n=int(mask.sum()), pred_median=float(np.median(sim)), lo=float(lo), hi=float(hi),
                p_upper=round(float((sim >= obs).mean()), 3), inside=bool(lo <= obs <= hi))


out = dict(total=ppc(np.ones(len(M), bool)))
out["by_stage"] = {k: ppc((M.stage == k).values) for k in sorted(M.stage.unique())}
out["by_provider"] = {k: ppc((M.provider == k).values) for k in sorted(M.provider.unique())}
pp = {k: ppc((M.problem == k).values) for k in sorted(M.problem.unique())}
uu = {k: ppc((M.user == k).values) for k in sorted(M.user.unique())}
out["problems_inside"] = dict(k=sum(v["inside"] for v in pp.values()), n=len(pp))
out["participants_inside"] = dict(k=sum(v["inside"] for v in uu.values()), n=len(uu))
res["rq1_posterior_predictive"] = out
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
