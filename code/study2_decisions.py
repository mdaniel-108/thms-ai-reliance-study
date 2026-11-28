r"""Study 2: decisions, answer attribution, use classification and the G0 validation.

  python -I code/study2_decisions.py

Uses no correctness of any answer. Steps:
  1. answers after a failure (same rules as study2_scorable_answers.py) and their applied programs (full program, or
     edit proposal applied to the failed code); 587 scorable expected;
  2. decisions: failure + >= 1 scorable answer + next submission; attributed answer by the fixed order (applied
     proposal in telemetry, else unique best match >= 0.80 with a 0.02 margin, else ambiguous, else not used);
  3. use level of the next submission against the attributed answer: unchanged >= 0.99, adapted 0.80-0.99, not used;
  4. G0: (a) applied-proposal answers classified as used; (b) Accepted pairs of different participants that are both
     < 0.80 to every earlier AI block (convergence; >= 20 pairs over >= 5 problems needed); (c) similarity distribution.
Private outputs (participant data, outside Git): <STUDY2_DIR>/answers.pkl, decisions.csv. Aggregate output:
results/use_validation.json.
"""
import collections, csv, difflib, itertools, json, os, pickle, re, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, ts, tok, response_text, _tool_arguments  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

ZIP = cfg.HANDOFF_ZIP
PRIV = cfg.STUDY2_DIR
LABELS = os.path.join(cfg.AUDIT_DIR, "tlt_labels.csv")
AGG = os.path.join(HERE, "..", "results", "use_validation.json")
FENCE = re.compile(r"```([A-Za-z0-9+#]*)[^\n]*\n(.*?)```", re.S)
LANG = {"c": "C", "cpp": "C++", "c++": "C++", "cc": "C++", "cxx": "C++", "java": "Java"}
UNCH, ADAPT, MARGIN = 0.99, 0.80, 0.02


def compiles(src, lang):
    with tempfile.TemporaryDirectory() as td:
        return d.build(src, lang, td) is not None


def applied_program(job):
    """(form, program, language) by the extraction rule; program None when there is no executable fix."""
    text, args, fail_src, fail_lang = job
    for tag, body in reversed(FENCE.findall(text)):
        lang = LANG.get(tag.lower(), fail_lang if tag == "" else None)
        if lang and re.search(r"\bmain\s*\(", body) and compiles(body, lang):
            return "full_program", body, lang
    edits = []
    for raw in args:
        try:
            edits += [e for e in json.loads(raw).get("edits") or [] if isinstance(e, dict)]
        except (TypeError, ValueError):
            pass
    if edits:
        if all((e.get("search") or "") in fail_src for e in edits):
            new = fail_src
            for e in edits:
                new = new.replace(e.get("search") or "", e.get("replace") or "", 1)
            if compiles(new, fail_lang):
                return "proposal_applied_compiles", new, fail_lang
            return "proposal_applied_no_compile", None, None
        return "proposal_not_applicable", None, None
    return ("code_fragments_only" if FENCE.findall(text) else "no_code"), None, None


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def main():
    os.makedirs(PRIV, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    req, seen = collections.defaultdict(list), set()
    for r in jsonl(z, "data/analysis/proxy_calls.jsonl"):
        if r.get("operation") not in (None, "None") or r.get("status") != "success" or not r.get("created_at"):
            continue
        if r.get("call_index") not in ("primary", None):
            continue
        n = pno(r.get("problem_id"))
        if n is None or r["chat_request_id"] in seen:
            continue
        seen.add(r["chat_request_id"])
        req[(r["participant"], n)].append((ts(r["created_at"]), r))
    applied = collections.defaultdict(list)                       # chat_request_id -> [applied times]
    for r in jsonl(z, "data/analysis/telemetry.jsonl"):
        if r["type"] == "edit_proposal" and r["payload"].get("outcome") == "applied":
            t = ts(r.get("client_ts") or r.get("server_ts"))
            if t:
                applied[r["payload"]["message_id"]].append(t)
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
    sb = collections.defaultdict(list)
    for s in subs:
        sb[(s["user_id"], int(s["problem_id"]) - 794)].append((ts(s["submitted_at"]), s))
    for v in list(sb.values()) + list(req.values()):
        v.sort(key=lambda x: x[0])
    src = lambda s: open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8", errors="replace").read()

    jobs, meta = [], []
    for key, ss in sb.items():
        for i, (t, s) in enumerate(ss):
            if s["verdict"] not in ("WA", "TLE"):
                continue
            nxt = ss[i + 1] if i + 1 < len(ss) else None
            fsrc = src(s)
            for rt, r in req.get(key, []):
                if rt > t and (nxt is None or rt < nxt[0]):
                    jobs.append((response_text(r), _tool_arguments(r), fsrc, s["language"]))
                    ap = [x for x in applied.get(r["chat_request_id"], []) if x > rt and (nxt is None or x < nxt[0])]
                    meta.append(dict(rid=r["chat_request_id"], t=rt, user=key[0], problem=key[1], fail=s["submission_id"],
                                     fail_verdict=s["verdict"], fail_lang=s["language"],
                                     next=nxt[1]["submission_id"] if nxt else None,
                                     stage=r.get("attempt_selected_stage"), provider=r.get("attempt_provider"),
                                     model=r.get("attempt_model") or r.get("model"),
                                     attempt=r.get("attempt_number"), applied_at=max(ap) if ap else None,
                                     req_len=len(json.dumps(r.get("messages") or [])[-4000:])))
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(applied_program, jobs))
    answers = []
    for m, (form, prog, lang) in zip(meta, res):
        m.update(form=form, program=prog, lang=lang, scorable=prog is not None)
        answers.append(m)
    sub_by_id = {s["submission_id"]: s for s in subs}
    pickle.dump(answers, open(f"{PRIV}/answers.pkl", "wb"))

    # ---- decisions ----
    by_fail = collections.defaultdict(list)
    for a in answers:
        by_fail[a["fail"]].append(a)
    decisions, applied_val, dist = [], [], []
    no_next = 0
    for fid, al in by_fail.items():
        sc = sorted([a for a in al if a["scorable"]], key=lambda a: a["t"])
        if not sc:
            continue
        if sc[0]["next"] is None:
            no_next += 1
            continue
        nsub = sub_by_id[sc[0]["next"]]
        ntok = tok(src(nsub))
        for a in sc:
            a["sim_next"] = sim(ntok, tok(a["program"]))
        for a in sc:
            if a["applied_at"]:
                applied_val.append(a["sim_next"])
        rule, att = None, None
        app = [a for a in sc if a["applied_at"]]
        if app:
            att, rule = max(app, key=lambda a: a["applied_at"]), "applied_proposal"
        else:
            progs = {}
            for a in sc:                                   # identical programs count as one, latest kept
                progs[a["program"]] = a
            ranked = sorted(progs.values(), key=lambda a: -a["sim_next"])
            if ranked[0]["sim_next"] >= ADAPT:
                if len(ranked) > 1 and ranked[1]["sim_next"] >= ADAPT and ranked[0]["sim_next"] - ranked[1]["sim_next"] < MARGIN:
                    rule, att = "ambiguous", max(ranked[:2], key=lambda a: a["t"])
                else:
                    rule, att = "best_match", ranked[0]
            else:
                rule, att = "not_used", sc[-1]
        s_att = att["sim_next"]
        use = "not_used" if rule == "not_used" else ("unchanged" if s_att >= UNCH else "adapted" if s_att >= ADAPT else "not_used")
        dist.append(s_att)
        decisions.append(dict(fail=fid, user=att["user"], problem=att["problem"], next=nsub["submission_id"],
                              next_verdict=nsub["verdict"], attributed_rid=att["rid"], last_rid=sc[-1]["rid"],
                              n_scorable=len(sc), rule=rule, use=use, sim=round(s_att, 4),
                              stage=att["stage"], provider=att["provider"], form=att["form"]))
    with open(f"{PRIV}/decisions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(decisions[0])); w.writeheader(); w.writerows(decisions)
    pickle.dump(answers, open(f"{PRIV}/answers.pkl", "wb"))   # now with sim_next

    # ---- G0 (b): convergence of independent Accepted solutions ----
    lab = {r["submission_id"]: float(r["best_similarity"]) for r in csv.DictReader(open(LABELS, encoding="utf-8"))}
    indep = collections.defaultdict(list)
    for s in subs:
        if s["verdict"] == "AC" and lab.get(s["submission_id"], 1.0) < ADAPT:
            indep[int(s["problem_id"]) - 794].append(s)
    pair_sims, per_problem = [], {}
    for n, L in indep.items():
        pairs = [(a, b) for a, b in itertools.combinations(L, 2) if a["user_id"] != b["user_id"]]
        per_problem[n] = len(pairs)
        for a, b in pairs:
            pair_sims.append(sim(tok(src(a)), tok(src(b))))
    np_ = len(pair_sims)
    probs = sum(v > 0 for v in per_problem.values())
    conv_ok = np_ >= 20 and probs >= 5
    share80 = sum(x >= ADAPT for x in pair_sims) / np_ if np_ else None
    share99 = sum(x >= UNCH for x in pair_sims) / np_ if np_ else None
    app_used = sum(x >= ADAPT for x in applied_val) / len(applied_val) if applied_val else None

    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None
    C = collections.Counter
    out = dict(
        note="Use classification and G0 validation; no correctness of any answer used.",
        answers_after_failure=len(answers), scorable=sum(a["scorable"] for a in answers),
        forms=dict(C(a["form"] for a in answers).most_common()),
        decisions=len(decisions), failures_with_scorable_answer_but_no_next_submission=no_next,
        participants_with_decisions=len({x["user"] for x in decisions}),
        attribution_rule=dict(C(x["rule"] for x in decisions).most_common()),
        use=dict(C(x["use"] for x in decisions).most_common()),
        use_by_rule={r: dict(C(x["use"] for x in decisions if x["rule"] == r)) for r in C(x["rule"] for x in decisions)},
        scorable_answers_per_decision=dict(sorted(C(x["n_scorable"] for x in decisions).items())),
        participants_with_ge6_decisions=sum(v >= 6 for v in C(x["user"] for x in decisions).values()),
        decisions_per_participant=sorted(C(x["user"] for x in decisions).values()),
        not_used_participants=len({x["user"] for x in decisions if x["use"] == "not_used"}),
        G0=dict(
            applied_proposal_answers=len(applied_val), applied_classified_used=app_used,
            independent_accepted_pairs=np_, problems_with_pairs=probs, pairs_per_problem=per_problem,
            convergence_source_a_usable=conv_ok, pairs_ge_080=share80, pairs_ge_099=share99,
            pair_similarity_p99=q(pair_sims, 0.99),
            rule_applied_lt_80pct=(app_used is not None and app_used < 0.80),
            rule_pairs_080_gt_10pct=(conv_ok and share80 > 0.10),
            rule_pairs_099_gt_5pct=(conv_ok and share99 > 0.05),
            source_b="pending: B2 correct programs vs these Accepted submissions (needs B2 scoring)"),
        decision_similarity_deciles=[round(q(dist, p / 10), 4) for p in range(11)],
    )
    os.makedirs(os.path.dirname(AGG), exist_ok=True)
    json.dump(out, open(AGG, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
