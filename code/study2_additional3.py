r"""Study 2, additional checks V1-V4.

  python -I code/study2_additional3.py

V1 echo check: does the attributed answer only repeat the participant's failed program? Similarity of the answer's
   runnable code to the failed submission c_t, the share of answer tokens not matched in c_t, and the headline rates
   recomputed without echo decisions.
V2 escalation with availability: stage moves at the next request split into up / down / same, restricted to requests
   where a higher stage than the previous one was unlocked; AI-attributable rejection vs other failure.
V3 exact vs near-verbatim: unchanged decisions whose submission is token-identical (s = 1) or identical after
   whitespace normalisation; over-reliance with only identical submissions counted as unchanged.
V4 who reached each stage: participants, problems and request number per stage (scorable answers).
Aggregates only: results/additional_3.json.
"""
import collections, csv, difflib, json, os, re, sys, zipfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, tok  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import study2_analyse as S2  # noqa: E402
import study2_additional2 as X2  # noqa: E402

OUT = os.path.join(HERE, "..", "results", "additional_3.json")


def sm(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False)


def code_of(sid, sub):
    return open(os.path.join(d.PROJ, sub[sid]["code_path"]), encoding="utf-8", errors="replace").read()


def main():
    A, byrid, cls, sc, fz, subs, stime, sb, arr, lat_ms, reqs, edits, dec, by_next, by_fail = X2.load()
    sub = {s["submission_id"]: s for s in subs}
    boot = X2.boot
    res = {"note": "Additional checks V1-V4. Aggregates only."}

    # ---------- V1 echo ----------
    rows = []
    for x in dec:
        if x["use"] == "not_used":
            continue
        a = byrid[x["rid"]]
        ta, tf = tok(a["program"]), tok(code_of(x["fail"], sub))
        m = sm(ta, tf)
        s_af = m.ratio()
        new_share = 1 - sum(bl.size for bl in m.get_matching_blocks()) / max(1, len(ta))
        rows.append(dict(user=x["user"], use=x["use"], cls=x["cls"], s_af=s_af, new_share=new_share,
                         over=(x["cls"] != "correct") and not x["next_ok_oracle"],
                         ai_fail=x["ai_fail"], next_verdict=x["next_verdict"]))
    E = pd.DataFrame(rows)
    E["echo"] = E.s_af >= 0.99
    E["near_echo"] = (E.s_af >= 0.95) & ~E.echo
    v1 = dict(used_decisions=len(E),
              similarity_answer_to_failed_program=X2.q(E.s_af),
              share_new_tokens_in_answer=X2.q(E.new_share),
              echo_ge_099=boot(E, "echo"), near_echo_095_099=boot(E, "near_echo"),
              echo_by_class={c: int(E[(E.cls == c)].echo.sum()) for c in ("correct", "wrong_detectable", "wrong_undetectable")},
              echo_among_ai_rejections=dict(k=int(E[E.ai_fail].echo.sum()), n=int(E.ai_fail.sum())))
    # headline rates without echo (and without echo or near-echo)
    R = pd.DataFrame(dec)
    R["over"] = (R.cls != "correct") & (R.use != "not_used") & ~R.next_ok_oracle
    R["unchanged"] = R.use == "unchanged"
    simf = {}
    for x in dec:
        if x["use"] != "not_used":
            simf[x["fail"]] = sm(tok(byrid[x["rid"]]["program"]), tok(code_of(x["fail"], sub))).ratio()
    R["s_af"] = R.fail.map(simf).fillna(0.0)
    for name, keep in (("without_echo", R.s_af < 0.99), ("without_echo_or_near_echo", R.s_af < 0.95)):
        Rk = R[keep]
        v1[name] = dict(decisions=len(Rk), participants=int(Rk.user.nunique()),
                        unchanged=boot(Rk, "unchanged"), over_reliance=boot(Rk, "over"),
                        ai_rejections=int((Rk.unchanged & (Rk.next_verdict != "AC")).sum()))
    # RQ1 correctness of answers that differ from the failed program
    Sc = [a for a in A if a["scorable"]]
    rq1 = []
    for a in Sc:
        tf = tok(code_of(a["fail"], sub))
        rq1.append(dict(user=a["user"], correct=cls[a["rid"]] == "correct", s=sm(tok(a["program"]), tf).ratio()))
    Q = pd.DataFrame(rq1)
    v1["rq1_answers_echoing_failed_program"] = dict(k=int((Q.s >= 0.99).sum()), n=len(Q),
                                                    correct_among_echo=int(Q[Q.s >= 0.99].correct.sum()))
    v1["rq1_correct_without_echo"] = boot(Q[Q.s < 0.99], "correct")
    res["V1_echo"] = v1

    # ---------- V2 escalation with availability ----------
    z = zipfile.ZipFile(S2.ZIP)
    rq, seen = collections.defaultdict(list), set()
    for r in jsonl(z, "data/analysis/proxy_calls.jsonl"):
        if r.get("operation") not in (None, "None") or r.get("status") != "success" or not r.get("created_at"):
            continue
        if r.get("call_index") not in ("primary", None) or r["chat_request_id"] in seen:
            continue
        n = pno(r.get("problem_id"))
        if n is None or r.get("attempt_selected_stage") is None:
            continue
        seen.add(r["chat_request_id"])
        rq[(r["participant"], n)].append((X2.ts(r["created_at"]), int(r["attempt_selected_stage"]),
                                          int(r.get("attempt_unlocked_stage") or r["attempt_selected_stage"]), r.get("attempt_provider")))
    for v in rq.values():
        v.sort(key=lambda t: t[0])
    base = collections.Counter()
    for L in rq.values():
        for a, b in zip(L, L[1:]):
            if b[2] > a[1]:
                base["n_higher_available"] += 1; base["up"] += b[1] > a[1]
            base["n"] += 1; base["up_any"] += b[1] > a[1]; base["down_any"] += b[1] < a[1]
    ev = []
    for x in dec:
        key = (x["user"], int(x["problem"]))
        before = [r for r in rq.get(key, []) if r[0] < x["t_fail"]]
        after = [r for r in rq.get(key, []) if x["t_fail"] < r[0] < x["t_next"]]
        if not before or not after:
            continue
        p, nx = before[-1], after[0]
        ev.append(dict(user=x["user"], ai=x["prev_type"] == "ai_attributable", k=x["k"],
                       up=nx[1] > p[1], down=nx[1] < p[1], same=nx[1] == p[1],
                       higher_available=nx[2] > p[1], unlocked_since=nx[2] > p[2]))
    V = pd.DataFrame(ev)
    v2 = dict(base_rate_consecutive_requests=dict(base))
    for t, lab in ((True, "ai_rejection"), (False, "other_failure")):
        e = V[V.ai == t]; ea = e[e.higher_available]
        v2[lab] = dict(n=len(e), up=int(e.up.sum()), down=int(e.down.sum()), same=int(e.same.sum()),
                       higher_available=int(e.higher_available.sum()), new_stage_unlocked_since_previous=int(e.unlocked_since.sum()),
                       up_given_available=boot(ea, "up"))
    import statsmodels.api as sm_, statsmodels.formula.api as smf
    Va = V[V.higher_available].assign(up_i=lambda f: f.up.astype(int), ai_i=lambda f: f.ai.astype(int))
    try:
        g = smf.gee("up_i ~ ai_i", "user", Va, family=sm_.families.Binomial(), cov_struct=sm_.cov_struct.Independence()).fit()
        ci = g.conf_int().loc["ai_i"]
        v2["gee_up_given_available_ai_vs_other"] = dict(OR=round(float(np.exp(g.params["ai_i"])), 3), lo=round(float(np.exp(ci[0])), 3),
                                                        hi=round(float(np.exp(ci[1])), 3), n=len(Va), participants=int(Va.user.nunique()))
        g = smf.gee("up_i ~ ai_i + kf", "user", Va.assign(kf=Va.k.astype(float)), family=sm_.families.Binomial(),
                    cov_struct=sm_.cov_struct.Independence()).fit()
        ci = g.conf_int().loc["ai_i"]
        v2["gee_up_given_available_ai_vs_other_adj_k"] = dict(OR=round(float(np.exp(g.params["ai_i"])), 3), lo=round(float(np.exp(ci[0])), 3),
                                                              hi=round(float(np.exp(ci[1])), 3))
    except Exception as e:  # pragma: no cover
        v2["gee"] = f"not estimable: {e}"
    v2["up_given_available_by_k"] = {str(k): boot(Va[Va.k == k], "up") for k in range(4)}
    res["V2_escalation_availability"] = v2

    # ---------- V3 exact vs near-verbatim ----------
    ws = lambda s: re.sub(r"\s+", "", s)
    ex = collections.Counter()
    R["exact_tok"] = False; R["exact_ws"] = False
    for i, x in enumerate(dec):
        if x["use"] != "unchanged":
            continue
        a = byrid[x["rid"]]["program"]; c = code_of(x["next"], sub)
        et = tok(a) == tok(c); ew = ws(a) == ws(c)
        R.loc[i, "exact_tok"] = et; R.loc[i, "exact_ws"] = ew
        ex["unchanged"] += 1; ex["token_identical"] += et; ex["identical_ignoring_whitespace"] += ew
    Rx = R.copy()
    Rx["unchanged_exact"] = Rx.unchanged & Rx.exact_tok
    res["V3_exact"] = dict(dict(ex), unchanged_exact_rate=boot(Rx, "unchanged_exact"),
                           over_reliance_unchanged_exact=int((Rx.over & Rx.unchanged_exact).sum()),
                           over_reliance_unchanged_near_only=int((Rx.over & Rx.unchanged & ~Rx.exact_tok).sum()),
                           note="over-reliance does not depend on the unchanged/adapted split (both count as used)")

    # ---------- V4 who reached each stage ----------
    att = {}
    for r in jsonl(z, "data/analysis/proxy_calls.jsonl"):
        if r.get("chat_request_id") and r.get("attempt_number") is not None:
            att.setdefault(r["chat_request_id"], int(r["attempt_number"]))
    v4 = {}
    for s in ("1", "2", "3+"):
        aa = [a for a in Sc if S2.stage3(a["stage"]) == s]
        v4[s] = dict(answers=len(aa), participants=len({a["user"] for a in aa}), problems=len({a["problem"] for a in aa}),
                     median_request_number=float(np.median([att.get(a["rid"], np.nan) for a in aa if a["rid"] in att])),
                     correct=int(sum(cls[a["rid"]] == "correct" for a in aa)),
                     top_problem_share=round(collections.Counter(a["problem"] for a in aa).most_common(1)[0][1] / len(aa), 3))
    res["V4_stage_composition"] = v4

    json.dump(res, open(OUT, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
