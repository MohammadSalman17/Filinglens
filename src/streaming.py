import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from generation import build_prompt
from retrieval import REPORT_YEAR, retrieve
from tracking import cache_get, cache_put, log_event

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def source_dict(doc, meta):
    return {
        "ticker": meta["ticker"],
        "report": meta["report"],
        "chunk": meta["chunk"],
        "year": REPORT_YEAR.get((meta["ticker"], meta["report"])),
        "text": doc,
    }


# Speed test results: the lite models answered in about 1-3 s, the older one in about 6 s.
PRIMARY_MODEL = "gemini-3.5-flash-lite"
# If the main model is busy, try these in order
FALLBACK_MODELS = ["gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
THINKING_LEVEL = "minimal"


def make_thinking_config():
    # Ask the model to think as little as possible, so the first word comes faster.
    # If this SDK version does not know the setting, we simply run without it.
    try:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL)
        )
    except Exception:
        return None


THINK_CONFIG = make_thinking_config()


def generate(question, results, t0, t_retrieval, info=None):
    """Yields ('status', str) and ('token', str) events for already retrieved results."""
    info = info if info is not None else {}
    prompt = build_prompt(question, results)
    models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    configs = [THINK_CONFIG, None] if THINK_CONFIG is not None else [None]
    last_error = None

    for round_no in range(2):
        for model in models:
            for config in configs:
                started = False
                usage = None
                try:
                    for chunk in client.models.generate_content_stream(
                        model=model, contents=prompt, config=config
                    ):
                        if getattr(chunk, "usage_metadata", None) is not None:
                            usage = chunk.usage_metadata  # the last chunk has the final numbers
                        if chunk.text:
                            if not started:
                                t_first = time.time() - t0
                            started = True
                            yield "token", chunk.text
                    total = time.time() - t0
                    info.update(
                        model=model,
                        first_word_s=round(t_first, 2),
                        thinking_config=config is not None,
                        input_tokens=getattr(usage, "prompt_token_count", None),
                        output_tokens=getattr(usage, "candidates_token_count", None),
                        thought_tokens=getattr(usage, "thoughts_token_count", None),
                    )
                    print(
                        f"[timing] retrieval {t_retrieval:.1f}s | first word {t_first:.1f}s "
                        f"| total {total:.1f}s | model {model} | thinking config "
                        f"{'on' if config else 'off'}"
                    )
                    return
                except Exception as e:
                    if started:
                        raise  # answer already partly shown, do not restart
                    msg = str(e)
                    if config is not None and any(
                        w in msg for w in ("thinking", "Thinking", "INVALID_ARGUMENT", "400")
                    ):
                        print(f"[{model}] thinking setting not accepted, retrying without it")
                        continue  # same model, without the thinking setting
                    last_error = e
                    print(f"[{model}] failed: {msg[:120]}")
                    yield "status", f"{model} is busy, trying another model…"
                    break  # go to the next model
        time.sleep(5)

    raise last_error


def stream_answer(question):
    """Yields events: ('sources', list), ('status', str), ('token', str)."""
    t0 = time.time()

    # 1. Same question asked before? Answer instantly, no search and no Gemini call.
    cached = cache_get(question)
    if cached:
        text, sources = cached
        yield "sources", sources
        for i in range(0, len(text), 30):
            yield "token", text[i : i + 30]
            time.sleep(0.01)
        log_event(
            question=question, cached=True, total_s=round(time.time() - t0, 2),
            answer_chars=len(text),
        )
        print(f"[timing] answered from cache in {time.time() - t0:.2f}s")
        return

    # 2. New question: search, then ask Gemini
    results = retrieve(question)
    t_retrieval = time.time() - t0
    sources = [source_dict(doc, meta) for score, doc, meta in results]
    yield "sources", sources

    text = ""
    info = {}
    try:
        for kind, value in generate(question, results, t0, t_retrieval, info):
            if kind == "token":
                text += value
            yield kind, value
    except Exception as e:
        log_event(
            question=question, cached=False, error=str(e)[:300],
            retrieval_s=round(t_retrieval, 2), total_s=round(time.time() - t0, 2),
        )
        raise

    log_event(
        question=question, cached=False, retrieval_s=round(t_retrieval, 2),
        total_s=round(time.time() - t0, 2), answer_chars=len(text), **info,
    )
    if text.strip():
        cache_put(question, text, sources)


def answer_text(question):
    """Non-streaming version with the same model settings. Returns (text, results)."""
    t0 = time.time()
    results = retrieve(question)
    t_retrieval = time.time() - t0
    text = ""
    for kind, value in generate(question, results, t0, t_retrieval):
        if kind == "token":
            text += value
    return text, results