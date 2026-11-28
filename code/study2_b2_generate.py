r"""Study 2, baseline B2: local models given only the public problem statement (no participant data).

  python -I code/study2_b2_generate.py            (Windows; Ollama on localhost:11434)

Settings: four local models, temperature 0.2, seeds 1-3, context 32,768 tokens,
at most 4,096 output tokens; 13 problems x 3 languages (C, C++, Java) x 3 samples per model = 468 generations.
Prompt wording (fixed here, before any output is seen): see PROMPT. Output: raw responses, one JSON line each, in
<STUDY2_DIR>/b2\generations.jsonl (outside Git; public statements only). Resumable: finished keys are skipped. A
generation the server aborts (HTTP error, e.g. token repeat limit) is recorded with an empty response and the error in
done_reason; it yields no program and counts as not correct.
"""
import json, os, time, urllib.error, urllib.request
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E401
import config as cfg  # noqa: E402  (private input locations)

MODELS = {"qwen2.5-coder:7b": "dae161e27b0e", "llama3.1:8b": "46e0c10c039e",
          "granite-code:8b": "36c3c3b9683b", "phi4-mini": "78fad5d182a7"}
LANGS = ["C", "C++", "Java"]
STM = cfg.STATEMENTS_DIR
OUT = os.path.join(cfg.STUDY2_DIR, "b2", "generations.jsonl")
PROMPT = ("Solve the following competitive programming problem. Write one complete {lang} program that reads the "
          "input from standard input and writes the answer to standard output, exactly in the format required."
          "{java} Reply with the program in a single fenced code block.\n\n{statement}")
JAVA = " The public class must be named Main."


def ask(model, prompt, seed):
    body = dict(model=model, prompt=prompt, stream=False,
                options=dict(temperature=0.2, seed=seed, num_ctx=32768, num_predict=4096))
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    done = set()
    if os.path.exists(OUT):
        for ln in open(OUT, encoding="utf-8"):
            j = json.loads(ln); done.add((j["model"], j["problem"], j["lang"], j["seed"]))
    tags = {m["name"]: m["digest"][:12] for m in json.load(urllib.request.urlopen("http://localhost:11434/api/tags"))["models"]}
    ver = json.load(urllib.request.urlopen("http://localhost:11434/api/version"))["version"]
    for m, dg in MODELS.items():
        key = m if m in tags else m + ":latest"
        assert tags.get(key) == dg, (m, tags.get(key), dg)
    t0 = time.time()
    with open(OUT, "a", encoding="utf-8") as fh:
        for m in MODELS:                     # model-major order: one model loaded at a time
            for n in range(1, 14):
                st = open(os.path.join(STM, f"{n}.md"), encoding="utf-8").read()
                for lang in LANGS:
                    p = PROMPT.format(lang=lang, java=JAVA if lang == "Java" else "", statement=st)
                    for seed in (1, 2, 3):
                        if (m, n, lang, seed) in done:
                            continue
                        try:
                            r = ask(m, p, seed)
                        except urllib.error.HTTPError as e:     # e.g. Ollama aborts a degenerate repetition
                            r = dict(response="", done_reason=f"error {e.code}: {e.read()[:200].decode('utf-8', 'replace')}")
                        fh.write(json.dumps(dict(model=m, digest=MODELS[m], ollama=ver, problem=n, lang=lang, seed=seed,
                                                 response=r.get("response", ""), eval_count=r.get("eval_count"),
                                                 prompt_eval_count=r.get("prompt_eval_count"),
                                                 done_reason=r.get("done_reason"))) + "\n")
                        fh.flush()
                print(f"{m} problem {n} done, {time.time() - t0:.0f} s", flush=True)
    # unload models when finished (GPU is shared with other jobs)
    for m in MODELS:
        try:
            urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate",
                                   data=json.dumps(dict(model=m, keep_alive=0)).encode()), timeout=60)
        except Exception:
            pass


if __name__ == "__main__":
    main()
