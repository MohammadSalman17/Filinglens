import json
import re
import sys
import time
from pathlib import Path

from streaming import answer_text as answer

FILES = ["data/eval/questions.json", "data/eval/holdout.json"]
CACHE = Path("data/eval/answers.json")

# Deliberately unanswerable questions (the answer is not in the reports): the model must say "I don't know"
UNANSWERABLE = [
    "What is the capital of France?",
    "What was Netflix's total revenue in 2025?",
    "What is Apple's stock price today?",
    "What is the weather in Mumbai today?",
    "Who won the FIFA World Cup in 2022?",
]


def load_questions():
    qs = []
    for f in FILES:
        qs += json.loads(Path(f).read_text(encoding="utf-8"))
    return qs


def numbers_in(keywords):
    nums = []
    for k in keywords:
        nums += re.findall(r"\d[\d,\.]*\d%?", k)
    return nums


def refused(text):
    t = text.lower()
    return "i don't know" in t or "i do not know" in t


def get_answers(all_questions, limit):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    new_calls = 0
    for q in all_questions:
        if q in cache:
            continue
        if limit is not None and new_calls >= limit:
            break
        try:
            text, results = answer(q)
        except Exception as e:
            print("STOPPED (rate limit or error):", str(e)[:200])
            break
        cache[q] = {
            "answer": text,
            "sources": [f"{m['ticker']} {m['report']} chunk {m['chunk']}" for s, d, m in results],
        }
        CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        new_calls += 1
        print(f"[{len(cache)}] {q[:70]}")
        time.sleep(6)
    return cache


def score(questions, cache):
    num_ok = num_total = refusals = cited = answered = 0
    manual = []
    print("\n===== NUMBER QUESTIONS (auto check) =====")
    for q in questions:
        item = cache.get(q["question"])
        if item is None:
            continue
        text = item["answer"]
        is_refusal = refused(text)
        refusals += is_refusal
        if not is_refusal:
            answered += 1
            cited += "[Source" in text

        nums = numbers_in(q["keywords"])
        if not nums:
            manual.append((q, text))
            continue
        flat = text.replace(",", "")
        ok = all(n in text or n.replace(",", "") in flat for n in nums)
        num_total += 1
        num_ok += ok
        status = "OK     " if ok else ("REFUSED" if is_refusal else "CHECK  ")
        print(f"{status} {q['question'][:75]}")

    print("\n===== TEXT QUESTIONS (read these yourself) =====")
    for q, text in manual:
        print(f"\nQ: {q['question']}\nA: {text[:350]}")

    print("\n===== UNANSWERABLE QUESTIONS (should answer \"I don't know\") =====")
    un_ok = un_total = 0
    for u in UNANSWERABLE:
        item = cache.get(u)
        if item is None:
            continue
        un_total += 1
        good = refused(item["answer"])
        un_ok += good
        print(("OK       " if good else "HALLUCINATED? ") + u + "\n   -> " + item["answer"][:160].replace("\n", " "))

    print("\n===== SUMMARY =====")
    print(f"Number questions with the right number in the answer: {num_ok}/{num_total}")
    print(f"Wrong refusals (an answer existed): {refusals}")
    print(f"Answers with a [Source n] citation: {cited}/{answered}")
    print(f"Correct refusals on unanswerable questions: {un_ok}/{un_total}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    questions = load_questions()
    all_q = [q["question"] for q in questions] + UNANSWERABLE
    cache = get_answers(all_q, limit)
    score(questions, cache)