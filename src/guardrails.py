"""Input checks and rate limiting. First layer of protection, before anything expensive runs."""
import re
import threading
import time
from collections import deque

MAX_QUESTION_CHARS = 500
MIN_QUESTION_CHARS = 3

# Typical "jailbreak" phrases. This list is a first filter, not a complete defence.
INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?(previous|prior|above|earlier|preceding) (instructions?|rules?|prompts?|messages?)",
    r"disregard (all |any |the |your )?(previous|prior|above|earlier|preceding)",
    r"forget (all |everything |your |the )?(previous |prior |above )?(instructions?|rules?|prompts?)",
    r"(reveal|show|print|repeat|display|leak|tell me)( me)? (your|the) (system |hidden |initial |original )?(prompt|instructions?|rules)",
    r"what (is|are) your (system |initial |hidden )?(prompt|instructions)",
    r"you are now (a|an|in)\b",
    r"\bdeveloper mode\b",
    r"\bjailbreak",
    r"\bdan mode\b",
    r"pretend (that )?(you are|to be)",
    r"override (your|the|all) (rules|instructions|safety)",
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

MESSAGES = {
    "empty": "Please type a question about the annual reports.",
    "too_long": f"Please keep your question under {MAX_QUESTION_CHARS} characters.",
    "injection": "I can only answer questions about the annual reports of Apple, Microsoft, Alphabet, Amazon and Tesla. Please rephrase your question.",
    "busy": "The service is busy right now. Please try again in a minute.",
    "fast": "You are asking too fast. Please wait a few seconds and try again.",
}


def clean_text(text):
    """Remove control characters and extra spaces."""
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def check_question(question):
    """Returns (ok, code, message, cleaned_question)."""
    cleaned = clean_text(question or "")
    if len(cleaned) < MIN_QUESTION_CHARS:
        return False, "empty", MESSAGES["empty"], cleaned
    if len(cleaned) > MAX_QUESTION_CHARS:
        return False, "too_long", MESSAGES["too_long"], cleaned
    if INJECTION_RE.search(cleaned):
        return False, "injection", MESSAGES["injection"], cleaned
    return True, None, None, cleaned


class RateLimiter:
    """Allows at most max_calls per per_seconds for each key (sliding window)."""

    def __init__(self, max_calls, per_seconds):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = {}
        self.lock = threading.Lock()

    def allow(self, key="all"):
        now = time.time()
        with self.lock:
            q = self.calls.setdefault(key, deque())
            while q and now - q[0] > self.per_seconds:
                q.popleft()
            if len(q) >= self.max_calls:
                return False
            q.append(now)
            return True


# One shared limit for the whole API, so nobody can use up the Gemini quota
GLOBAL_LIMITER = RateLimiter(max_calls=30, per_seconds=60)