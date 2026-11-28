r"""Study 2 figures for the manuscript, from aggregate outputs only.

  python -I code/study2_figures.py

Inputs: results/{results,additional_1,additional_2}.json. Output: figures/*.pdf
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(O, "results.json")))
E5 = json.load(open(os.path.join(O, "additional_1.json")))
E6 = json.load(open(os.path.join(O, "additional_2.json")))
P = E6["P_perspectives"]

plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 8, "axes.titlesize": 8,
                     "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "hatch.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
C = ["#3b6ea5", "#d1853a", "#5a9e5a", "#a14d6b", "#7f7f7f"]
H = ["////", "....", "xxxx", "\\\\\\\\", "oo"]
W1, W2 = 3.45, 7.1          # IEEE column and page widths (in)


def bars(ax, labels, vals, lo=None, hi=None, color=C[0], hatch=H[0], fmt="{:.1f}", width=0.62, x=None, label=None, note=None):
    x = np.arange(len(labels)) if x is None else x
    v = np.array(vals, float)
    err = None if lo is None else np.vstack([v - np.array(lo), np.array(hi) - v])
    ax.bar(x, v, width, color="white", edgecolor=color, hatch=hatch, linewidth=0.9, label=label)
    if err is not None:
        keep = (err[0] > 1e-9) | (err[1] > 1e-9)
        ax.errorbar(np.asarray(x)[keep], v[keep], yerr=err[:, keep], fmt="none", lw=0.7, capsize=2, ecolor="black")
    for i, xv in enumerate(x):
        top = v[i] if err is None else v[i] + err[1][i]
        txt = fmt.format(v[i]) + ("" if note is None else note[i])
        ax.text(xv, top + 1.2, txt, ha="center", va="bottom", fontsize=6.3, color=color)
    ax.set_xticks(np.arange(len(labels)) if x is None else x)
    ax.set_xticklabels(labels)
    return x


def pct(d):
    return 100 * d["rate"], 100 * d["lo"], 100 * d["hi"]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight")
    plt.close(fig)


# Fig. 4: RQ1 correctness by stage (a) and answer classes by stage (b)
fig, ax = plt.subplots(1, 2, figsize=(W2, 2.3))
st = ["1", "2", "3+"]
v = [pct(R["RQ1"]["correct_by_stage"][s]) for s in st]
bars(ax[0], ["Stage 1", "Stage 2", "Stages 3-5"], [a for a, _, _ in v], [b for _, b, _ in v], [c for _, _, c in v],
     note=[f"\n({R['RQ1']['correct_by_stage'][s]['k']}/{R['RQ1']['correct_by_stage'][s]['n']})" for s in st])
ax[0].set_ylabel("Correct on the oracle (%)"); ax[0].set_ylim(0, 85); ax[0].set_title("(a) Correct runnable code by stage")
cb = R["RQ1"]["class_by_stage"]
x = np.arange(3); bottom = np.zeros(3)
for j, (c, lab) in enumerate((("correct", "Correct"), ("wrong_detectable", "Wrong, fails a sample"),
                              ("wrong_undetectable", "Wrong, passes the samples"))):
    n = np.array([sum(cb[s].values()) for s in st], float)
    val = np.array([cb[s].get(c, 0) for s in st]) / n * 100
    ax[1].bar(x, val, 0.6, bottom=bottom, color="white", edgecolor=C[j], hatch=H[j], lw=0.9, label=lab)
    for i in range(3):
        ax[1].text(x[i], bottom[i] + val[i] / 2, f"{cb[st[i]].get(c, 0)}", ha="center", va="center", fontsize=6.3)
    bottom += val
ax[1].set_xticks(x); ax[1].set_xticklabels(["Stage 1", "Stage 2", "Stages 3-5"]); ax[1].set_ylabel("Share of runnable answers (%)")
ax[1].set_title("(b) Answer classes by stage"); ax[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False)
save(fig, "F4_rq1_stage.pdf")

# Fig. 5: over-reliance under truth sources (a) and per participant (b)
fig, ax = plt.subplots(1, 2, figsize=(W2, 2.4), gridspec_kw=dict(width_ratios=[1.1, 1]))
src = [("Oracle", P["over_reliance_oracle"]["pooled"]), ("Judge,\nTLE correct", None),
       ("Judge,\nAC only", P["over_reliance_judge_strict"]["pooled"])]
tle = E5["E5_1"]["rq2_by_truth"]["judge_tle_ok"]["over_reliance"]
vals = [100 * src[0][1]["rate"], 100 * tle / 497, 100 * src[2][1]["rate"]]
lo = [100 * src[0][1]["lo"], vals[1], 100 * src[2][1]["lo"]]
hi = [100 * src[0][1]["hi"], vals[1], 100 * src[2][1]["hi"]]
ex = E5["E5_1"]["rq2_without_problems_10_11"]["oracle"]
labels = [s for s, _ in src] + ["Oracle,\nno P10-11"]
vals.append(100 * ex["over_reliance"] / ex["n"]); lo.append(vals[-1]); hi.append(vals[-1])
bars(ax[0], labels, vals, lo, hi, note=[f"\n({k}/{n})" for k, n in ((306, 497), (tle, 497), (383, 497), (ex["over_reliance"], ex["n"]))])
ax[0].set_ylim(0, 100); ax[0].set_ylabel("Over-reliance (% of decisions)"); ax[0].set_title("(a) By correctness source")
for i, (name, col, mk) in enumerate((("over_reliance_oracle", C[0], "o"), ("over_reliance_judge_strict", C[1], "s"))):
    pp = sorted(P[name]["per_participant_sorted"], key=lambda t: t[0] / t[1])
    r = [100 * a / b for a, b in pp]; n = [b for _, b in pp]
    ax[1].scatter(np.arange(1, len(r) + 1) + (i - 0.5) * 0.18, r, s=[6 + 1.2 * m for m in n], facecolor="white",
                  edgecolor=col, marker=mk, lw=0.9, label="Oracle" if i == 0 else "Judge, AC only")
ax[1].set_xlabel("Participant (ranked by rate; marker size = decisions)"); ax[1].set_ylabel("Over-reliance (%)")
ax[1].set_ylim(-5, 105); ax[1].set_xticks([1, 5, 10, 15, 20]); ax[1].legend(frameon=False, loc="lower right")
ax[1].set_title("(b) Per participant")
save(fig, "F5_over_reliance.pdf")

# Fig. 6: acceptance by earlier rejections (a), stage change by earlier rejections (b)
fig, ax = plt.subplots(1, 2, figsize=(W2, 2.3))
ks = ["0", "1", "2", "3"]; lab = ["0", "1", "2", "3+"]
v = [pct(E5["E5_2"]["unchanged_by_k"][k]) for k in ks]
bars(ax[0], lab, [a for a, _, _ in v], [b for _, b, _ in v], [c for _, _, c in v],
     note=[f"\n({E5['E5_2']['unchanged_by_k'][k]['k']}/{E5['E5_2']['unchanged_by_k'][k]['n']})" for k in ks])
ax[0].set_ylim(0, 118); ax[0].set_xlabel("Earlier rejected unchanged AI submissions on the problem")
ax[0].set_ylabel("Next answer submitted unchanged (%)"); ax[0].set_title("(a) Unchanged use")
E7 = json.load(open(os.path.join(O, "additional_3.json")))
c2 = E7["V2_escalation_availability"]["up_given_available_by_k"]
v = [pct(c2[k]) for k in ks]
bars(ax[1], lab, [a for a, _, _ in v], [b for _, b, _ in v], [c for _, _, c in v], color=C[1], hatch=H[1],
     note=[f"\n({c2[k]['k']}/{c2[k]['n']})" for k in ks])
ax[1].set_ylim(0, 110); ax[1].set_xlabel("Earlier rejected unchanged AI submissions on the problem")
ax[1].set_ylabel("Moved up, where a higher stage was open (%)"); ax[1].set_title("(b) Escalation when possible")
save(fig, "F6_adaptation.pdf")

# Fig. 7: loop survival (a) and what followed a rejection (b)
fig, ax = plt.subplots(1, 2, figsize=(W2, 2.3), gridspec_kw=dict(width_ratios=[1, 1.25]))
sv = P["loop_survival"]; k = np.array([int(x) for x in sv]); s = np.array([sv[x] for x in sv])
ax[0].step(np.r_[k, k[-1] + 1], np.r_[s, s[-1]], where="post", color=C[0], lw=1.2)
for xi, yi in zip(k, s):
    ax[0].text(xi + 0.5, yi + 0.02, f"{yi:.2f}", fontsize=6, ha="center", color=C[0])
ax[0].set_xlabel("Consecutive rejected unchanged submissions, $m$"); ax[0].set_ylabel("Share of loops with length $\\geq m$")
ax[0].set_ylim(0, 1.08); ax[0].set_title(f"(a) Loop survival ({P['loops']} loops)")
A4 = E6["C4_actions_after_rejection"]
order = [("asked_again_submitted_unchanged", "Asked again,\nunchanged"), ("asked_again_no_runnable_code", "Asked again,\nno code"),
         ("resubmitted_without_asking", "Resubmitted,\nno request"), ("asked_again_adapted_or_not_used", "Asked again,\nedited or\nset aside"),
         ("no_further_submission", "Stopped")]
v = [pct(A4[a]) for a, _ in order]
bars(ax[1], [b for _, b in order], [a for a, _, _ in v], [b for _, b, _ in v], [c for _, _, c in v], color=C[3], hatch=H[3],
     note=[f"\n({A4[a]['k']})" for a, _ in order])
ax[1].set_ylim(0, 100); ax[1].set_ylabel("Share of 378 rejections (%)"); ax[1].set_title("(b) Next action after a rejection")
ax[1].tick_params(axis="x", labelsize=6)
save(fig, "F7_loops.pdf")

# Fig. 8: heatmap participant x problem (oracle over-reliance counts)
hm = np.array(P["heatmap_over_reliance_oracle"]["counts"])
fig, ax = plt.subplots(figsize=(W1, 3.0))
im = ax.imshow(hm, cmap="Blues", aspect="auto")
for i in range(hm.shape[0]):
    for j in range(hm.shape[1]):
        if hm[i, j]:
            ax.text(j, i, hm[i, j], ha="center", va="center", fontsize=5.5, color="white" if hm[i, j] > hm.max() / 2 else "black")
ax.set_xticks(range(13)); ax.set_xticklabels(range(1, 14)); ax.set_yticks(range(hm.shape[0]))
ax.set_yticklabels([f"P{i + 1:02d}" for i in range(hm.shape[0])], fontsize=5.5)
ax.set_xlabel("Problem"); ax.set_ylabel("Participant (ranked by total)")
fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02).set_label("Over-reliance events")
save(fig, "F8_heatmap.pdf")

# Fig. 9: decision time by answer class (a) and by earlier rejections (b)
c1 = E6["C1_timing"]
fig, ax = plt.subplots(1, 2, figsize=(W2, 2.1))
for a_, key, labs, col in ((ax[0], "decision_seconds_by_class", [("correct", "Correct"), ("wrong_detectable", "Wrong,\nfails sample"),
                                                                  ("wrong_undetectable", "Wrong,\npasses samples")], C[0]),
                           (ax[1], "decision_seconds_by_k", [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3+")], C[2])):
    for i, (kk, ll) in enumerate(labs):
        d = c1[key][kk]
        a_.add_patch(plt.Rectangle((i - 0.25, d["q1"]), 0.5, d["q3"] - d["q1"], facecolor="white", edgecolor=col, hatch=H[2], lw=0.9))
        a_.plot([i - 0.25, i + 0.25], [d["median"]] * 2, color="black", lw=1.2)
        a_.text(i, d["q3"] + 1.2, f"{d['median']:.1f} s\n(n={d['n']})", ha="center", fontsize=6.2)
    a_.set_xticks(range(len(labs))); a_.set_xticklabels([l for _, l in labs]); a_.set_xlim(-0.6, len(labs) - 0.4)
    a_.set_ylim(0, 45); a_.set_ylabel("Answer arrival to submission (s)")
ax[0].set_title("(a) By answer class (median, IQR)"); ax[1].set_title("(b) By earlier rejections")
ax[1].set_xlabel("Earlier rejected unchanged AI submissions")
save(fig, "F9_timing.pdf")

# Fig. 10: warning in ROC space
L = R["RQ4"]["leave_one_participant_out"]
fig, ax = plt.subplots(figsize=(W1, 2.6))
ax.plot([0, 1], [0, 1], ":", color="gray", lw=0.8, label="Chance")
pts = E6["C6_stage_rule_points"]["points"]
sp = sorted([(p["false_alarm"], p["hit"]) for p in pts if p["rule"] in ("flag none", "flag stage 1 only", "flag stage 3+",
                                                                       "flag stage 2 or 3+", "flag all")])
ax.plot([a for a, _ in sp], [b for _, b in sp], "s", mfc="white", mec=C[1], label="Stage-only rule (all thresholds)")
for p in pts:
    if p["rule"] not in ("flag none", "flag all"):
        ax.annotate(p["rule"].replace("flag ", ""), (p["false_alarm"], p["hit"]), textcoords="offset points", xytext=(4, -9), fontsize=6)
for key, mk, col, lb in (("hgb_fa10", "o", C[0], "Gradient boosting, FA 10%"), ("hgb_fa20", "o", C[0], "Gradient boosting, FA 20%"),
                         ("lr_fa20", "^", C[2], "Logistic regression, FA 20%")):
    ax.plot(L[key]["false_alarm"], L[key]["hit"], mk, color=col, ms=5, label=lb if key != "hgb_fa10" else None)
ax.annotate("FA 10%", (L["hgb_fa10"]["false_alarm"], L["hgb_fa10"]["hit"]), textcoords="offset points", xytext=(4, 2), fontsize=6)
ax.set_xlabel("False-alarm rate (held-out participants)"); ax.set_ylabel("Hit rate")
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.legend(frameon=False, fontsize=6, loc="upper left")
save(fig, "F10_warning.pdf")

# Fig. 11: perspectives on the main rates (pooled / participant-weighted / problem-weighted)
fig, ax = plt.subplots(figsize=(W1, 2.3))
names = [("rq1_correct", "Correct\n(RQ1)"), ("unchanged_use", "Unchanged\nuse"), ("over_reliance_oracle", "Over-reliance,\noracle"),
         ("over_reliance_judge_strict", "Over-reliance,\njudge AC")]
x = np.arange(len(names)); w = 0.25
for j, (lab, f) in enumerate((("Pooled", lambda d: 100 * d["pooled"]["rate"]), ("Participant-weighted", lambda d: 100 * d["participant_macro"]),
                             ("Problem-weighted", lambda d: 100 * d["problem_macro"]))):
    vv = [f(P[n]) for n, _ in names]
    ax.bar(x + (j - 1) * w, vv, w, color="white", edgecolor=C[j], hatch=H[j], lw=0.9, label=lab)
    for i, t in enumerate(vv):
        ax.text(x[i] + (j - 1) * w, t + 1.5, f"{t:.0f}", ha="center", fontsize=5.8, color=C[j])
ax.set_xticks(x); ax.set_xticklabels([l for _, l in names], fontsize=6.2); ax.set_ylim(0, 115); ax.set_ylabel("%")
ax.legend(frameon=False, ncol=3, fontsize=6, loc="upper center")
save(fig, "F11_weighting.pdf")
print("figures written to", os.path.abspath(FIG))
