# Aggregate results

Aggregates only: no participant code, prompt, answer or identifier. Per-participant values appear only as sorted,
anonymous distributions.

| File | Script | Contents |
|---|---|---|
| `results.json` | `code/study2_analyse.py` | RQ1 correctness and Bayesian model; RQ2 reliance table, categories, gates G1 and G2, oracle-vs-judge check, sensitivity; RQ3 self-report vs behavior; RQ4 gate G4, nested evaluation, C4, warning eligibility |
| `use_validation.json` | `code/study2_decisions.py` | Answers after a failure, decisions, answer attribution, use counts, G0 validation (no correctness information used) |
| `b2_results.json` | `code/study2_b2_analyse.py` | Baseline B2 (local models given the statement only) |
| `additional_1.json` | `code/study2_additional1.py` | Additional analyses E5.1 to E5.6 |
| `additional_2.json` | `code/study2_additional2.py` | Checks C1 to C6 and perspectives P (participants only as anonymous ranks) |
| `additional_3.json` | `code/study2_additional3.py` | Checks V1 to V4: echo, escalation with stage availability, exact reuse, stage composition |
| `additional_4.json` | `code/study2_additional4.py` | Checks T1 and T2: every answer followed by a submission, and every attributed or reference answer, arrived before that submission; loops that ended with no further submission |
| `additional_5.json` | `code/study2_additional5.py` | Check S1: same-request echo (answer compared with all participant text of the same request) and the main rates without such decisions |
| `additional_6.json` | `code/study2_additional6.py` | Checks M1 and M2: warning rules at matched false-alarm rates; posterior predictive check of the RQ1 model |
| `use_by_class_and_stage.json` | `reproduce/use_by_class_and_stage.py` | Use by answer class; correctness, unchanged use and over-reliance by stage |
| `within_stage.json` | `reproduce/within_participant_stage.py` | Unchanged use and over-reliance at stage 1 vs stages 2-5 within participants |
| `oracle/oracle2_input_validation.json` | `code/tlt_pck_validate.py` | Validity of the candidate oracle inputs per problem |
| `oracle/oracle2_frozen_validation.json` | `code/tlt_pck_oracle2_freeze.py analyse` | Frozen oracle: inputs kept, time limits, specificity and sensitivity with 95% intervals, settings, machine, sha256 manifest |
| `oracle/oracle_validation.json` | `code/tlt_pck_oracle2.py score` | Preliminary oracle run, superseded by the frozen run |
