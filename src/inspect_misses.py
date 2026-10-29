import json
from pathlib import Path
from retrieval import retrieve
from evaluation import is_hit

questions = json.loads(Path("data/eval/questions.json").read_text(encoding = "utf-8"))

for q in questions:
    top5 = retrieve(q["question"], final_n = 5)
    if is_hit(top5, q["ticker"], q["keywords"]):
        continue

    ranked = retrieve(q["question"], final_n = 50, pool = 50)
    gold_rank = None
    gold_rank = None
    for rank, (score, doc, meta) in enumerate(ranked, start = 1):
        if meta["ticker"] == q["ticker"] and all(k.lower() in doc.lower() for k in q["keywords"]):
            gold_rank, gold_text = rank, doc
            break

    print("=" * 80)
    print("Question : ",q["question"])
    print("Keywords : ",q["keywords"])
    print("rank of right chunk : ",gold_rank if gold_rank else "not in 50")
    if gold_text:
        print("right chunk : ",gold_text[:250].replace("\n", " "))

    print("retrieved top 3 :")
    for score, doc, meta in top5[:3]:
        line = f"  {meta["ticker"]} {meta["report"]} chunk {meta["chunk"]} | {doc[:150]}"
        print(line.replace("\n", " "))