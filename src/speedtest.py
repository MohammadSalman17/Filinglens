import time

from google.genai import types

from generation import MODEL, build_prompt
from retrieval import retrieve
from streaming import FALLBACK_MODELS, client

QUESTION = "What was Alphabet's total revenue in 2025?"
results = retrieve(QUESTION)
prompt = build_prompt(QUESTION, results)


def make_config(level):
    if level is None:
        return None
    return types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=level))


models = [MODEL] + [m for m in FALLBACK_MODELS + ["gemini-flash-lite-latest"] if m != MODEL]

for model in models:
    for level in [None, "minimal", "low"]:
        start = time.time()
        first = None
        chars = 0
        try:
            for chunk in client.models.generate_content_stream(
                model=model, contents=prompt, config=make_config(level)
            ):
                if chunk.text:
                    if first is None:
                        first = time.time() - start
                    chars += len(chunk.text)
            total = time.time() - start
            print(f"{model:28} thinking={str(level):8} first word {first or 0:.1f}s | total {total:.1f}s | {chars} chars")
        except Exception as e:
            print(f"{model:28} thinking={str(level):8} FAILED: {str(e)[:80]}")