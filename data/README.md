# Pseudonymised, code-free tables

Written by `code/export_pseudonymised.py` from the private session records. The participant, failure, answer and
decision IDs are new random IDs drawn from the operating-system random source; the mapping to the original records
was not stored. Rows are shuffled, so their order carries no time information. The tables contain no source code,
prompt, assistant answer, timestamp, judge submission ID or account ID.

## `answers.csv`: one row per assistant answer given after a failed submission (895 rows, 20 participants)

| Column | Meaning |
|---|---|
| `answer_id` | Pseudonymous answer ID (`A0001` ...) |
| `participant` | Pseudonymous participant ID (`P01` ... `P20`) |
| `problem` | Problem number, 1 to 13 |
| `failure_id` | Pseudonymous ID of the failed submission the answer followed |
| `failed_verdict`, `failed_language` | Judge verdict and language of that failed submission |
| `stage`, `provider`, `model` | Assistant stage (1 to 5), provider and model alias that produced the answer |
| `form` | Form of the answer: `full_program`, `proposal_applied_compiles`, `proposal_applied_no_compile`, `proposal_not_applicable`, `code_fragments_only`, `no_code` |
| `answer_language` | Language of the answer's program (empty if none) |
| `scorable` | 1 if the answer contained a runnable program that was scored on the oracle |
| `similarity_to_next_submission` | Token similarity between the answer's program and the next submission (0 to 1) |
| `failed_compiles`, `failed_<kind>_passed`, `failed_<kind>_n` | Frozen-oracle result of the failed submission, per input kind (`sample`, `random`, `edge`, `large`) |
| `answer_compiles`, `answer_<kind>_passed`, `answer_<kind>_n` | Frozen-oracle result of the answer's program (empty if not scorable) |
| `answer_large_timeouts` | Number of large inputs on which the answer's program timed out |

An answer is **correct** if it compiles and passes every input of every kind; a wrong answer is **detectable** if it
fails the statement's sample inputs and **undetectable** otherwise.

## `decisions.csv`: one row per decision after a failure with a scorable answer (499 rows)

| Column | Meaning |
|---|---|
| `decision_id` | Pseudonymous decision ID |
| `participant`, `problem`, `failure_id` | As above |
| `attributed_answer_id` | Answer the next submission was attributed to (empty if no answer was used) |
| `last_answer_id` | Last scorable answer before the next submission |
| `scorable_answers` | Number of scorable answers between the failure and the next submission |
| `attribution_rule` | How the answer was attributed: `applied_proposal`, `best_match`, `not_used`, `ambiguous` (ambiguous decisions are excluded from RQ2) |
| `use` | `unchanged` (similarity at least 0.99), `adapted` (0.80 to 0.99) or `not_used` |
| `similarity` | Similarity between the attributed answer and the next submission |
| `stage`, `provider`, `form` | Stage, provider and form of the attributed answer |
| `next_judge_verdict` | Judge verdict of the next submission |
| `next_compiles`, `next_<kind>_passed`, `next_<kind>_n` | Frozen-oracle result of the next submission |

The rules that turn these columns into the paper's answer classes and reliance categories are in
`reproduce/reproduce_rq1_rq2.py` and, in full, in `code/study2_analyse.py`.
