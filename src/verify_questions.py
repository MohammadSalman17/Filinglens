import json
from pathlib import Path
from chunking import chunk_text
 
questions = json.loads(Path("data/eval/questions.json").read_text(encoding="utf-8"))
 
chunks_by_ticker = {}
for f in Path("data/processed").glob("*.txt"):
    ticker = f.stem.split("_")[0]
    chunks_by_ticker.setdefault(ticker, []).extend(
        chunk_text(f.read_text(encoding="utf-8")))
 
bad = 0
for q in questions:
    chunks = chunks_by_ticker.get(q["ticker"], [])
    found = any(all(k.lower() in c.lower() for k in q["keywords"]) for c in chunks)
    if not found:
        bad += 1
        print("NOT FOUND:", q["ticker"], "|", q["question"], "|", q["keywords"])
 
print(f"\n{len(questions) - bad}/{len(questions)} Questions verified")
 