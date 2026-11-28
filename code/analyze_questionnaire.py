"""Analysis of the post-exhibition questionnaire (44-item form).

Input (participant data, kept outside Git): the transcribed response sheet,
rows = items A1..J2, columns = respondents. Output: aggregate, anonymous files
in results/questionnaire/ only. No respondent IDs, no free text.

Rules:
- codes outside the printed form are treated as "unclear": excluded from
  distributions and counted in data_quality.md, never re-coded by guess;
- a single-choice item with several options ticked is reported as "multiple";
- SUS uses complete B1..B10 responses only (listwise), standard scoring;
- perception vs behaviour links only respondents whose ID is unambiguous.

Usage:
  python code/analyze_questionnaire.py --responses <reply.xlsx> \
      [--audit datasets/audit]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics as st
from pathlib import Path
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "outputs" / "questionnaire"

ITEMS = (["A1", "A2", "A3"] + [f"B{i}" for i in range(1, 11)]
         + ["C1", "C2", "C3", "C4", "C5", "D1", "D2", "D3", "D4", "E1", "E2", "E3", "E4",
            "F1", "F2", "F3", "F4", "F5", "G1", "G2", "G3", "G4", "H1", "H2", "H3", "H4", "H5",
            "I1", "I2", "J1", "J2"])

LIKERT = {  # 1 Strongly disagree .. 5 Strongly agree (form wording, shortened)
    "B1": "Would like to use the system frequently", "B2": "System unnecessarily complex",
    "B3": "System easy to use", "B4": "Would need a technical person's support",
    "B5": "Functions well integrated", "B6": "Too much inconsistency",
    "B7": "Most people would learn it quickly", "B8": "Very cumbersome to use",
    "B9": "Felt very confident using it", "B10": "Needed to learn a lot first",
    "C1": "AI responses fast enough for a timed competition",
    "C2": "Unlocking rule encouraged me to keep trying",
    "C3": "Gradual stronger stages made me reconsider my approach first",
    "C4": "Sometimes kept requesting mainly to unlock a higher stage",
    "D4": "Felt in control of what went into my code",
    "F1": "AI explanations helped me understand", "F2": "Diff view helped me understand proposed changes",
    "F3": "Understood the AI-assisted code I used", "F4": "Learned something I can use without AI",
    "G2": "More control than separate web AI chat (vs web)",
    "G3": "Workflow more cumbersome than web AI chat (vs web)",
    "H1": "Knowing I was recorded changed how I worked", "H2": "VS Code stayed fast and responsive",
}
SUS_ITEMS = [f"B{i}" for i in range(1, 11)]
MIN_CELL = 3   # linked groups smaller than this are suppressed in outputs
# multi-choice options that exclude all others ("None", "did not ...")
EXCLUSIVE = {"C5": 7, "D2": 9, "D3": 6, "E1": 1, "F5": 7, "H4": 9, "I2": 10}

CHOICE = {  # item -> (kind, option labels in form order)
    "A2": ("single", ["Yes, fully", "Yes, partially", "No"]),
    "A3": ("single", ["1 Not useful", "2 Slightly", "3 Moderately", "4 Very", "5 Extremely", "Not applicable"]),
    "C5": ("multi", ["Earlier responses not sufficient", "Needed more help on a difficult problem",
                     "Wanted a different explanation or approach", "Wanted a complete or more reliable solution",
                     "Wanted to save time", "Curious about the stronger model", "Did not switch to a higher stage", "Other"]),
    "D1": ("single", ["Apply button", "Copying or retyping from chat", "Both about equally", "Did not incorporate AI code"]),
    "D2": ("multi", ["Explain the problem", "Explain code or an algorithm", "Hints or approaches",
                     "Generate a complete solution", "Generate or modify part of my code", "Find or fix errors",
                     "Improve efficiency or complexity", "Translate or clarify the statement", "Did not use AI chat", "Other"]),
    "D3": ("multi", ["Modified the suggested code", "Compared with my own code", "Tested or verified the approach",
                     "Asked further questions", "Rejected or ignored suggestions", "Did not receive or use suggestions", "Other"]),
    "E1": ("multi", ["None", "ChatGPT", "Claude", "Gemini", "Copilot", "Cursor", "Prefer not to answer", "Other"]),
    "E2": ("single", ["Never", "Rarely", "Sometimes", "Often", "Very often"]),
    "E3": ("single", ["Never", "Rarely", "Sometimes", "Often", "Very often"]),
    "E4": ("single", ["Always", "Mostly", "Sometimes", "Rarely or never", "No submissions or give-ups"]),
    "F5": ("multi", ["AI explanations", "Diff view", "AI stages", "PDF translation", "File attachments",
                     "Separate problem conversations", "None", "Other"]),
    "G1": ("single", ["Yes", "No"]),
    "G4": ("single", ["This system", "Separate web-based AI chat", "A combination of both", "No preference", "Not sure"]),
    "H3": ("single", ["None", "Under 10 minutes", "10-30 minutes", "Over 30 minutes"]),
    "H4": ("multi", ["Login or session problem", "AI chat error", "AI response too slow", "Code proposal or diff problem",
                     "VS Code crash", "Network problem", "PDF or attachment problem", "Lost code or AI history",
                     "No technical problems", "Other"]),
    "H5": ("single", ["Fully", "Partially", "No", "No interruption"]),
    "I1": ("single", ["1 Very poor", "2 Poor", "3 Neither", "4 Good", "5 Very good"]),
    "I2": ("multi", ["Understanding the problems", "Developing or correcting solutions", "Managing the time limit",
                     "Communicating effectively with AI", "Understanding or evaluating AI responses",
                     "Deciding when or how to use AI", "Using the system", "Technical difficulties",
                     "Pressure from the setting", "No significant difficulties", "Other"]),
}


def parse(v):
    """-> None (blank), list[int] (codes), or str (unparseable)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    s = repr(v) if isinstance(v, float) else str(v).strip()
    parts = [p for p in re.split(r"[.,、\s]+", s) if p]
    if parts and all(p.isdigit() for p in parts):
        return [int(p) for p in parts]
    return s


def load(path: Path) -> dict[str, list]:
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)][1:]
    if len(rows) < len(ITEMS):
        raise SystemExit(f"expected {len(ITEMS)} item rows, found {len(rows)}")
    return {name: row for name, row in zip(ITEMS, rows)}


def quantiles(x: list[float]) -> tuple[float, float, float]:
    q = st.quantiles(x, n=4, method="inclusive") if len(x) > 1 else [x[0]] * 3
    return q[0], st.median(x), q[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True, type=Path)
    ap.add_argument("--audit", type=Path, default=Path(cfg.AUDIT_DIR))
    a = ap.parse_args()
    data = load(a.responses)
    n_resp = len(data["A1"])
    OUT.mkdir(parents=True, exist_ok=True)
    quality: list[dict] = []

    # ---- respondent IDs (never written out) ---------------------------------
    ids = []
    for v in data["A1"]:
        s = str(v).strip() if v is not None else ""
        ids.append(f"E{int(s):03d}" if s.isdigit() else None)
    unresolved = sum(1 for i in ids if i is None)
    dup = len([i for i in ids if i]) - len(set(i for i in ids if i))
    quality.append({"item": "A1", "issue": "participant ID not unambiguous (e.g. '8?')", "count": unresolved,
                    "handling": "excluded from linkage to logs; kept in all aggregates"})
    if dup:
        quality.append({"item": "A1", "issue": "duplicate participant IDs", "count": dup, "handling": "flagged"})

    # ---- Likert items -------------------------------------------------------
    lik_rows = []
    for item, label in LIKERT.items():
        vals = [parse(v) for v in data[item]]
        ok = [v[0] for v in vals if isinstance(v, list) and len(v) == 1 and 1 <= v[0] <= 5]
        unclear = [v for v in vals if v is not None and not (isinstance(v, list) and len(v) == 1 and 1 <= v[0] <= 5)]
        if unclear:
            codes = sorted({str(u) for u in unclear})
            quality.append({"item": item, "issue": f"code(s) outside 1-5: {', '.join(codes)}", "count": len(unclear),
                            "handling": "excluded as unclear"})
        q1, med, q3 = quantiles(ok) if ok else ("", "", "")
        lik_rows.append({"item": item, "statement": label, "sus": item in SUS_ITEMS, "n": len(ok),
                         "blank": sum(1 for v in vals if v is None), "unclear": len(unclear),
                         **{f"n_{k}": ok.count(k) for k in range(1, 6)},
                         "median": med, "q1": q1, "q3": q3, "mean": round(st.mean(ok), 2) if ok else "",
                         "pct_agree_4_5": round(100 * sum(x >= 4 for x in ok) / len(ok), 1) if ok else "",
                         "pct_disagree_1_2": round(100 * sum(x <= 2 for x in ok) / len(ok), 1) if ok else ""})
    write_csv(OUT / "likert_items.csv", lik_rows)

    # ---- SUS ------------------------------------------------------------------
    sus_scores = []
    for j in range(n_resp):
        resp = [parse(data[it][j]) for it in SUS_ITEMS]
        if all(isinstance(r, list) and len(r) == 1 and 1 <= r[0] <= 5 for r in resp):
            x = [r[0] for r in resp]
            sus_scores.append(2.5 * sum((x[i] - 1) if i % 2 == 0 else (5 - x[i]) for i in range(10)))
    rng = random.Random(2026)
    boots = sorted(st.mean(rng.choices(sus_scores, k=len(sus_scores))) for _ in range(10000))
    q1, med, q3 = quantiles(sus_scores)
    sus = {"n_complete": len(sus_scores), "n_respondents": n_resp, "mean": round(st.mean(sus_scores), 1),
           "sd": round(st.stdev(sus_scores), 1), "median": med, "q1": q1, "q3": q3,
           "min": min(sus_scores), "max": max(sus_scores),
           "bootstrap_95ci_mean": [round(boots[249], 1), round(boots[9749], 1)],
           "bootstrap": "percentile, 10,000 resamples, seed 2026",
           "scoring": "standard: odd items (x-1), even items (5-x), sum x 2.5; listwise for missing items",
           "n_at_or_above_68": sum(s >= 68 for s in sus_scores),
           "note": "68 is the commonly cited SUS average (Sauro 2011; Lewis and Sauro 2018)"}
    (OUT / "sus.json").write_text(json.dumps(sus, indent=2), encoding="utf-8")
    quality.append({"item": "B1-B10", "issue": "SUS responses with a blank or invalid item",
                    "count": n_resp - len(sus_scores), "handling": "excluded from SUS (listwise)"})

    # ---- single / multi choice -------------------------------------------------
    ch_rows = []
    for item, (kind, labels) in CHOICE.items():
        vals = [parse(v) for v in data[item]]
        answered = [v for v in vals if v is not None]
        valid, unclear, multiple = [], [], 0
        for v in answered:
            if not isinstance(v, list) or any(c < 1 or c > len(labels) for c in v):
                unclear.append(v)
            elif kind == "single" and len(v) > 1:
                multiple += 1
            else:
                valid.append(v)
        if unclear:
            quality.append({"item": item, "issue": f"code(s) not on the printed form: "
                                                   f"{', '.join(sorted({str(u) for u in unclear}))}",
                            "count": len(unclear), "handling": "excluded as unclear"})
        if item in EXCLUSIVE:
            ex = EXCLUSIVE[item]
            contradictory = sum(1 for v in valid if ex in v and len(v) > 1)
            if contradictory:
                quality.append({"item": item, "issue": f"exclusive option '{labels[ex - 1]}' ticked together with others",
                                "count": contradictory, "handling": "kept as ticked; counted under each option"})
        if multiple:
            quality.append({"item": item, "issue": "single-choice item with several options ticked",
                            "count": multiple, "handling": "reported as 'multiple', not split"})
        base = len(valid) + multiple
        for k, lab in enumerate(labels, start=1):
            c = sum(1 for v in valid if k in v)
            ch_rows.append({"item": item, "kind": kind, "option": k, "label": lab, "count": c,
                            "base_n": base, "pct_of_base": round(100 * c / base, 1) if base else ""})
        if multiple:
            ch_rows.append({"item": item, "kind": kind, "option": "multiple", "label": "several options ticked",
                            "count": multiple, "base_n": base, "pct_of_base": round(100 * multiple / base, 1)})
        ch_rows.append({"item": item, "kind": kind, "option": "-", "label": "(blank / unclear)",
                        "count": f"{n_resp - len(answered)} / {len(unclear)}", "base_n": "", "pct_of_base": ""})
    write_csv(OUT / "choice_items.csv", ch_rows)

    # ---- free text: counts only --------------------------------------------------
    free = {it: sum(1 for v in data[it] if v not in (None, "") and str(v).strip() not in ("", "None"))
            for it in ("J1", "J2")}

    # ---- perception vs behaviour (D1 vs logs), unambiguous IDs only ----------------
    pvb_rows = []
    pa = a.audit / "participant_audit.csv"
    ep = a.audit / "episode_audit.csv"
    if pa.exists() and ep.exists():
        part = {r["participant"]: r for r in csv.DictReader(open(pa, encoding="utf-8-sig"))}
        applied = {}
        for r in csv.DictReader(open(ep, encoding="utf-8-sig")):
            applied[r["participant"]] = applied.get(r["participant"], 0) + int(r["proposals_applied"])
        groups: dict[str, list] = {}
        for j, pid in enumerate(ids):
            v = parse(data["D1"][j])
            if not pid or pid not in part or not isinstance(v, list):
                continue
            key = CHOICE["D1"][1][v[0] - 1] if len(v) == 1 and 1 <= v[0] <= 4 else "several options ticked"
            groups.setdefault(key, []).append((applied.get(pid, 0), float(part[pid]["share_subs_verbatim_ai"] or 0)))
        for key, g in groups.items():
            small = len(g) < MIN_CELL                    # small-cell suppression: no near-individual values
            pvb_rows.append({"D1_self_report": key, "n_linked": len(g),
                             "median_applied_proposals": "suppressed (n<3)" if small else st.median(x for x, _ in g),
                             "median_share_submissions_verbatim_ai":
                                 "suppressed (n<3)" if small else round(st.median(y for _, y in g), 3)})
        write_csv(OUT / "perception_vs_behaviour_D1.csv", pvb_rows)

    # ---- figures ---------------------------------------------------------------------
    figures(lik_rows, sus_scores)

    # ---- quality report + summary -------------------------------------------------------
    write_csv(OUT / "data_quality.csv", quality)
    summary = {"respondents": n_resp, "ids_unresolved": unresolved, "sus": sus, "free_text_nonempty": free,
               "likert_items": len(lik_rows), "choice_items": len(CHOICE), "quality_flags": len(quality),
               "perception_vs_behaviour_linked": sum(r["n_linked"] for r in pvb_rows) if pvb_rows else 0}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def figures(lik_rows: list[dict], sus_scores: list[float]) -> None:
    import site
    import sys
    sys.path.append(site.getusersitepackages())
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [r for r in lik_rows if not r["sus"] and r["n"]]
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(rows) + 1.2))
    colors = ["#b2182b", "#ef8a62", "#d9d9d9", "#67a9cf", "#2166ac"]
    names = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
    for y, r in enumerate(reversed(rows)):
        pct = [100 * r[f"n_{k}"] / r["n"] for k in range(1, 6)]
        left = -(pct[0] + pct[1] + pct[2] / 2)
        for k in range(5):
            ax.barh(y, pct[k], left=left, color=colors[k], edgecolor="white",
                    label=names[k] if y == 0 else None)
            left += pct[k]
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f'{r["item"]}  {r["statement"]} (n={r["n"]})' for r in reversed(rows)], fontsize=8)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_xlabel("% of respondents (neutral split at 0)")
    ax.legend(ncol=5, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.01), frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "likert_items.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.hist(sus_scores, bins=range(0, 101, 10), color="#2166ac", edgecolor="white")
    ax.axvline(68, color="#b2182b", ls="--", lw=1, label="68 (commonly cited average)")
    ax.set_xlabel("SUS score")
    ax.set_ylabel("Respondents")
    ax.set_title(f"SUS (n={len(sus_scores)} complete responses)", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "sus_distribution.png", dpi=200)
    plt.close(fig)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
