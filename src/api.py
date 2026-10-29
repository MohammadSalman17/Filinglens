import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from generation import answer
from guardrails import GLOBAL_LIMITER, MESSAGES, check_question
from retrieval import REPORT_YEAR
from streaming import stream_answer
from tracking import log_event

app = FastAPI(title="10-K Q&A API")


class AskRequest(BaseModel):
    question: str = Field(max_length=5000)


class Source(BaseModel):
    ticker: str
    report: str
    chunk: int
    year: int | None = None
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


def validate(raw_question):
    """Checks length, jailbreak phrases and the global rate limit. Returns the cleaned question."""
    ok, code, message, cleaned = check_question(raw_question)
    if not ok:
        log_event(question=cleaned[:200], blocked=code)
        raise HTTPException(status_code=400, detail=message)
    if not GLOBAL_LIMITER.allow("all"):
        log_event(question=cleaned[:200], blocked="rate_limit")
        raise HTTPException(status_code=429, detail=MESSAGES["busy"])
    return cleaned


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = validate(req.question)

    try:
        text, results = answer(question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Answer generation failed: {e}")

    sources = [
        Source(
            ticker=m["ticker"],
            report=m["report"],
            chunk=m["chunk"],
            year=REPORT_YEAR.get((m["ticker"], m["report"])),
            text=doc,
        )
        for score, doc, m in results
    ]
    return AskResponse(answer=text, sources=sources)


@app.post("/ask_stream")
def ask_stream(req: AskRequest):
    question = validate(req.question)

    def events():
        try:
            for kind, value in stream_answer(question):
                if kind == "sources":
                    yield json.dumps({"type": "sources", "sources": value}) + "\n"
                elif kind == "status":
                    yield json.dumps({"type": "status", "text": value}) + "\n"
                else:
                    yield json.dumps({"type": "token", "text": value}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")