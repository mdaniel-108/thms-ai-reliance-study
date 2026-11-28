r"""Study 2, additional check S1: same-request echo.

  python -I code/study2_additional5.py

For every decision in which an answer was used (unchanged or adapted), the next submission's tokens are matched
against the attributed answer and against all participant text sent in the same request (prompts and attached files,
as in the companion study). The answer counts as mostly new when at least half of the submission's tokens are
matched by the answer and not by that participant text; otherwise it is a same-request echo. Headline rates are
recomputed without same-request echoes.
Aggregates only: results/additional_5.json.
"""
import collections, json, os, random, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import study2_additional2 as E  # noqa: E402
import tlt_pck_difftest as d  # noqa: E402
from build_episode_audit import jsonl, tok  # noqa: E402
import difflib  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "additional_5.json")


def user_text(r):
    """all participant text of one request: prompts and attached files"""
    parts = []
    for m in r.get("messages") or []:
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                parts += [x.get("text", "") for x in c if isinstance(x, dict)]
    return "\n".join(parts)


def matched_positions(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    pos = set()
    for i, _, n in sm.get_matching_blocks():
        pos.update(range(i, i + n))
    return pos, sm.ratio()
A, byrid, cls, sc, fz, subs, stime, sb, arr, lat_ms, reqs, edits, dec, by_next, by_fail = E.load()
code = {s["submission_id"]: open(os.path.join(d.PROJ, s["code_path"]), encoding="utf-8", errors="replace").read() for s in subs}
need = {x["rid"] for x in dec if x["use"] != "not_used"}
msgs = {}
for r in jsonl(zipfile.ZipFile(E.S2.ZIP), "data/analysis/proxy_calls.jsonl"):
    if r.get("chat_request_id") in need and r["chat_request_id"] not in msgs and r.get("messages"):
        msgs[r["chat_request_id"]] = user_text(r)

for x in dec:
    x["over"] = x["cls"] != "correct" and x["use"] != "not_used" and not x["next_ok_oracle"]
    x["sr_echo"] = False
    if x["use"] == "not_used":
        continue
    T = tok(code[x["next"]])
    pa, _ = matched_positions(T, tok(byrid[x["rid"]]["program"]))
    ut = tok(msgs.get(x["rid"], ""))
    pr = matched_positions(T, ut)[0] if ut else set()
    x["new_share"] = len(pa - pr) / max(1, len(T))
    x["sr_echo"] = x["new_share"] < 0.5


def boot(rows, key, n=2000, seed=2026):
    by = collections.defaultdict(list)
    for x in rows:
        by[x["user"]].append(x)
    us = sorted(by); rnd = random.Random(seed); v = []
    for _ in range(n):
        s = [rnd.choice(us) for _ in us]
        num = sum(sum(y[key] for y in by[u]) for u in s); den = sum(len(by[u]) for u in s)
        v.append(num / den)
    v.sort()
    k = sum(x[key] for x in rows)
    return dict(k=k, n=len(rows), rate=round(k / len(rows), 4), lo=round(v[49], 4), hi=round(v[1949], 4))


used = [x for x in dec if x["use"] != "not_used"]
for x in dec:
    x["unch"] = x["use"] == "unchanged"
keep = [x for x in dec if not x["sr_echo"]]
ns = sorted(x["new_share"] for x in used)
res = dict(
    note="Same-request echo: under half of the next submission's tokens matched by the answer and not by participant text of the same request.",
    used_decisions=len(used), with_request_text=sum(1 for x in used if msgs.get(x["rid"])),
    same_request_echo=sum(x["sr_echo"] for x in used),
    same_request_echo_participants=len({x["user"] for x in used if x["sr_echo"]}),
    same_request_echo_by_use=dict(collections.Counter(x["use"] for x in used if x["sr_echo"])),
    same_request_echo_by_class=dict(collections.Counter(x["cls"] for x in used if x["sr_echo"])),
    same_request_echo_among_over_reliance=sum(x["sr_echo"] for x in dec if x["over"]),
    new_share_median=round(ns[len(ns) // 2], 4), new_share_q1=round(ns[len(ns) // 4], 4),
    all_decisions=dict(unchanged=boot(dec, "unch"), over_reliance=boot(dec, "over")),
    without_same_request_echo=dict(unchanged=boot(keep, "unch"), over_reliance=boot(keep, "over")))
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
