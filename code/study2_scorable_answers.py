r"""Study 2 feasibility (not an outcome): how many answers after a failure can be scored by the RQ1 procedure?

  python code/study2_scorable_answers.py

Unit: successful primary answers to requests made after a WA/TLE submission and before the next submission on the same
problem. For each answer, the extraction rule is applied up to
compilation only: (1) full program = the last fenced block that compiles here as a complete program (fence language,
else the failed submission's language); (2) otherwise a proposal whose search texts are all found in the failed
submission's code; (3) otherwise no executable fix. NO program is run on any test input, so no fix rate is computed.
Prints aggregate counts only.
"""
import collections, csv, json, os, re, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_episode_audit import jsonl, pno, ts, response_text, _tool_arguments  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

ZIP = cfg.HANDOFF_ZIP
FENCE = re.compile(r"```([A-Za-z0-9+#]*)[^\n]*\n(.*?)```", re.S)
LANG = {"c": "C", "cpp": "C++", "c++": "C++", "cc": "C++", "cxx": "C++", "java": "Java"}


def compiles(src, lang):
    with tempfile.TemporaryDirectory() as td:
        return d.build(src, lang, td) is not None


def classify(job):
    text, args, fail_src, fail_lang = job
    blocks = FENCE.findall(text)
    for tag, body in reversed(blocks):
        lang = LANG.get(tag.lower(), fail_lang if tag == "" else None)
        if lang and re.search(r"\bmain\s*\(", body) and compiles(body, lang):
            return "full_program"
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
            return "proposal_applied_compiles" if compiles(new, fail_lang) else "proposal_applied_no_compile"
        return "proposal_not_applicable"
    return "code_fragments_only" if blocks else "no_code"


def main():
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
    subs = list(csv.DictReader(open(f"{d.PROJ}/submissions.csv", encoding="utf-8-sig")))
    sb = collections.defaultdict(list)
    for s in subs:
        sb[(s["user_id"], int(s["problem_id"]) - 794)].append((ts(s["submitted_at"]), s))
    for v in list(sb.values()) + list(req.values()):
        v.sort(key=lambda x: x[0])
    jobs, meta = [], []
    for key, ss in sb.items():
        for i, (t, s) in enumerate(ss):
            if s["verdict"] not in ("WA", "TLE"):
                continue
            nxt = ss[i + 1][0] if i + 1 < len(ss) else None
            src = open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8", errors="replace").read()
            for rt, r in req.get(key, []):
                if rt > t and (nxt is None or rt < nxt):
                    jobs.append((response_text(r), _tool_arguments(r), src, s["language"]))
                    meta.append(dict(fail=s["submission_id"], user=key[0], stage=r.get("attempt_selected_stage"),
                                     provider=r.get("attempt_provider"), last=False))
    with ThreadPoolExecutor(6) as ex:
        cls = list(ex.map(classify, jobs))
    scorable = {"full_program", "proposal_applied_compiles"}
    out = dict(answers=len(cls), failures_with_answers=len({m["fail"] for m in meta}),
               participants=len({m["user"] for m in meta}), forms=dict(collections.Counter(cls).most_common()),
               scorable=sum(c in scorable for c in cls))
    out["scorable_by_stage"] = {str(k): v for k, v in sorted(collections.Counter(
        m["stage"] for m, c in zip(meta, cls) if c in scorable).items(), key=lambda x: str(x[0]))}
    out["scorable_by_provider"] = dict(collections.Counter(m["provider"] for m, c in zip(meta, cls) if c in scorable))
    out["failures_with_a_scorable_answer"] = len({m["fail"] for m, c in zip(meta, cls) if c in scorable})
    out["participants_with_a_scorable_answer"] = len({m["user"] for m, c in zip(meta, cls) if c in scorable})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
