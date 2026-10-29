import json
import statistics
from collections import Counter

from tracking import LOG_FILE

if not LOG_FILE.exists():
    raise SystemExit(f"No log yet. Ask some questions first ({LOG_FILE} will be created).")

rows = [json.loads(line) for line in LOG_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
if not rows:
    raise SystemExit("The log is empty.")


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))]


fresh = [r for r in rows if not r.get("cached") and not r.get("error") and not r.get("blocked")]
cached = [r for r in rows if r.get("cached")]
errors = [r for r in rows if r.get("error")]
blocked = [r for r in rows if r.get("blocked")]

print(f"Log file: {LOG_FILE}")
print(f"Questions asked : {len(rows)}")
print(f"  from cache    : {len(cached)} ({100 * len(cached) / len(rows):.0f}%)")
print(f"  new questions : {len(fresh)}")
print(f"  errors        : {len(errors)}")
print(f"  blocked       : {len(blocked)}" + (f"  ({dict(Counter(r['blocked'] for r in blocked))})" if blocked else ""))

if fresh:
    totals = [r["total_s"] for r in fresh]
    print()
    print("New questions, total time (seconds)")
    print(f"  average {statistics.mean(totals):.1f} | median {statistics.median(totals):.1f} | 90% under {pct(totals, 0.9):.1f}")
    firsts = [r["first_word_s"] for r in fresh if r.get("first_word_s") is not None]
    if firsts:
        print(f"  time to first word: average {statistics.mean(firsts):.1f}")
    searches = [r["retrieval_s"] for r in fresh if r.get("retrieval_s") is not None]
    if searches:
        print(f"  search part       : average {statistics.mean(searches):.1f}")

    inp = sum(r.get("input_tokens") or 0 for r in fresh)
    out = sum(r.get("output_tokens") or 0 for r in fresh)
    think = sum(r.get("thought_tokens") or 0 for r in fresh)
    print()
    print(f"Gemini tokens used: input {inp:,} | output {out:,} | thinking {think:,}")
    print(f"  per new question: input {inp // len(fresh):,} | output {out // len(fresh):,}")

    print()
    print("Models that answered:")
    for model, n in Counter(r.get("model", "?") for r in fresh).most_common():
        print(f"  {n:4d} x {model}")

    print()
    print("5 slowest questions:")
    for r in sorted(fresh, key=lambda r: r["total_s"], reverse=True)[:5]:
        print(f"  {r['total_s']:5.1f}s  {r['question'][:80]}")

if cached:
    print()
    print(f"Cache saved about {len(cached)} Gemini calls.")

repeats = Counter(r["question"].strip().lower() for r in rows).most_common(3)
repeats = [(q, n) for q, n in repeats if n > 1]
if repeats:
    print()
    print("Most repeated questions:")
    for q, n in repeats:
        print(f"  {n}x  {q[:80]}")

if errors:
    print()
    print("Last errors:")
    for r in errors[-3:]:
        print(f"  {r['time']}  {r['error'][:100]}")