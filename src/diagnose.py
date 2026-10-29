import json
from collections import Counter
from pathlib import Path
from retrieval import (all_ids, all_docs, all_metas,
                       keyword_search, semantic_search, hybrid_search, retrieve)

questions = json.loads(Path("data/eval/questions.json").read_text(encoding="utf-8"))

print("DB mein chunks per company:", dict(Counter(m["ticker"] for m in all_metas)))
print()


def gold_ids(q):
    return {i for i, d, m in zip(all_ids, all_docs, all_metas)
            if m["ticker"] == q["ticker"]
            and all(k.lower() in d.lower() for k in q["keywords"])}


def yn(x):
    return "Y" if x else "N"


stages = Counter()
for q in questions:
    gold = gold_ids(q)
    sem = gold & set(semantic_search(q["question"], 20))
    kw = gold & set(keyword_search(q["question"], 20))
    hyb = gold & set(hybrid_search(q["question"], 20))
    final = gold & {f"{m['ticker']}_{m['report']}_{m['chunk']}"
                    for s, d, m in retrieve(q["question"], 5)}

    for name, val in [("in_db", gold), ("semantic20", sem), ("bm25_20", kw),
                      ("hybrid20", hyb), ("final5", final)]:
        stages[name] += bool(val)

    print(f"{q['ticker']} [{q['type']}] db={yn(gold)} sem={yn(sem)} bm25={yn(kw)} "
          f"hyb={yn(hyb)} top5={yn(final)} | {q['question'][:55]}")

print("\nKitne sawalon mein sahi chunk mila (total", len(questions), "):")
for name in ["in_db", "semantic20", "bm25_20", "hybrid20", "final5"]:
    print(f"  {name:11s}: {stages[name]}")