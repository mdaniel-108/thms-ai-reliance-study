"""Locations of the private inputs. None of them is in this repository; set the environment variables to run the
pipeline on a machine that holds the data (see README, "What is not included")."""
import os

_ROOT = os.environ.get("STUDY2_DATA_ROOT", "/data/pck2026")          # private data root
HANDOFF_ZIP = os.environ.get("STUDY2_HANDOFF_ZIP", os.path.join(_ROOT, "research-handoff-share.zip"))
JUDGE_DIR = os.environ.get("STUDY2_JUDGE_DIR", os.path.join(_ROOT, "pck2026_oln2026"))   # judge submissions + code
AUDIT_DIR = os.environ.get("STUDY2_AUDIT_DIR", os.path.join(_ROOT, "audit"))             # labels, oracle scores
WORK_DIR = os.environ.get("STUDY2_WORK_DIR", os.path.join(_ROOT, "work"))                # statements, tests, study2
STUDY2_DIR = os.path.join(WORK_DIR, "study2")            # private intermediate files (answers, decisions, scores)
STATEMENTS_DIR = os.path.join(WORK_DIR, "pck_statements")  # problem statements (contest copyright; not released)
TESTS_DIR = os.path.join(WORK_DIR, "pck_tests")            # generated oracle inputs and the frozen oracle
QUESTIONNAIRE_XLSX = os.environ.get("STUDY2_QUESTIONNAIRE", os.path.join(_ROOT, "questionnaire_responses.xlsx"))
