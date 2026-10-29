import json
from collections import defaultdict
from pathlib import Path
from retrieval import retrieve
from evaluation import is_hit

questions = json.loads(Path("data/eval/questions.json").read_text(encoding = "utf-8"))

configs = [
    ("B) pool 50 + reranker, koi filter nahi", dict(pool=50, use_ticker=False, use_year=False)),
    ("E1) + sirf company filter", dict(pool=50, use_ticker=True, use_year=False)),
    ("E2) + company aur saal filter", dict(pool=50, use_ticker=True, use_year=True)),
    
]

for name, cfg in configs:
    hits = 0
    by_ticker = defaultdict(lambda: [0, 0])
    missed = []

    for q in questions:
        results = retrieve(q["question"], final_n=5, **cfg)
        hit = is_hit(results, q["ticker"], q["keywords"])
        hits += hit
        by_ticker[q["ticker"]][0] += hit
        by_ticker[q["ticker"]][1] += 1
        if not hit:
            missed.append(q["question"][:60])

    print(f"\n   {name}    ")
    print(f"hit rate @ 5: {hits}/{len(questions)} = {hits / len(questions):.0%}")
    print("Company wised : ", {t: f"{h}/{n}" for t, (h, n) in by_ticker.items()})
    for m in missed:
        print(" miss :",m)