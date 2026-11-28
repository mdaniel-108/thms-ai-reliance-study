r"""Study 2, additional checks T1-T2.

  python -I code/study2_additional4.py

T1 answer availability: for every decision, the proxy record of the attributed answer (for a not-used decision, the
   last scorable answer before the next submission) was created before the next submission
T2 loops that ended with no further submission on the problem: whether the participant submitted anything afterwards,
   and how long before the last submission of the session the loop ended
Aggregates only: results/additional_4.json.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import study2_additional2 as E  # noqa: E402

OUT = os.path.join(HERE, "..", "results", "additional_4.json")


def main():
    A, byrid, cls, sc, fz, subs, stime, sb, arr, lat_ms, reqs, edits, dec, by_next, by_fail = E.load()
    res = {}

    # ---------- T1 answer availability ----------
    order = collections.defaultdict(collections.Counter)
    mins = {}
    for x in dec:
        t0 = arr.get(x["rid"])
        c = order[x["use"]]
        if t0 is None:
            c["no_proxy_record"] += 1
            continue
        dt = (x["t_next"] - t0).total_seconds()
        c["n"] += 1
        c["before_next"] += dt > 0
        c["negative"] += dt < 0
        mins[x["use"]] = min(mins.get(x["use"], float("inf")), dt)
    res["T1_answer_before_next_submission"] = {
        k: dict(v, min_seconds=round(mins[k], 1)) for k, v in order.items()}

    # ---------- T2 loops with no further submission ----------
    session_last = max(stime.values())
    user_last = {}
    for s in subs:
        t = stime[s["submission_id"]]
        if s["user_id"] not in user_last or t > user_last[s["user_id"]]:
            user_last[s["user_id"]] = t
    ends = []
    for x in sorted(dec, key=lambda x: x["t_fail"]):
        if not x["ai_fail"]:
            continue
        prev = by_next.get(x["fail"])
        if prev and prev["ai_fail"]:
            continue                                        # not a loop start
        L = [x]
        while True:
            nx = by_fail.get(L[-1]["next"])
            if nx and nx["ai_fail"]:
                L.append(nx)
            else:
                break
        if by_fail.get(L[-1]["next"]):
            continue                                        # loop ended with a further decision
        key = (L[-1]["user"], int(L[-1]["problem"]))
        if any(stime[s["submission_id"]] > L[-1]["t_next"] for s in sb[key]):
            continue                                        # further submission without a decision
        t = L[-1]["t_next"]
        ends.append(dict(last_of_participant=user_last[L[-1]["user"]] == t,
                         minutes=round((session_last - t).total_seconds() / 60, 1)))
    m = sorted(e["minutes"] for e in ends)
    res["T2_loops_with_no_further_submission"] = dict(
        n=len(ends), participant_submitted_nothing_afterwards=sum(e["last_of_participant"] for e in ends),
        within_30_min_of_last_session_submission=sum(v <= 30 for v in m),
        minutes_before_last_session_submission=m)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
