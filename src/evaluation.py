import json
import sys
from pathlib import Path
from retrieval import retrieve


def is_hit(results, ticker, keywords):
    for score, doc, meta in results:
        if meta["ticker"] != ticker:
            continue
        text = doc.lower()
        if all(k.lower() in text for k in keywords):
            return True
    return False


def run_eval(path="data/eval/questions.json", k=5):
    questions = json.loads(Path(path).read_text(encoding="utf-8"))
    hits = 0

    for q in questions:
        results = retrieve(q["question"], final_n=k)
        hit = is_hit(results, q["ticker"], q["keywords"])
        hits += hit
        label = f"[{q['type']}|{q.get('tag', 'dev')}]"
        print(("HIT  " if hit else "MISS ") + label + " " + q["question"])

    print(f"\n{path}")
    print(f"Hit rate @ {k}: {hits}/{len(questions)} = {hits / len(questions):.0%}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/eval/questions.json"
    run_eval(path)