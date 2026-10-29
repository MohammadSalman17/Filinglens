import json
import sys
from pathlib import Path

needle = sys.argv[1].lower()
cache = json.loads(Path("data/eval/answers.json").read_text(encoding = "utf-8"))

for question, item in cache.items():
    if needle in question.lower():
        print("Q : ",question)
        print("A : ", item["answer"])
        print()