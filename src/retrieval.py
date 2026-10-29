import re
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from vector_store import collection, model

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Har report kis saal (fiscal year) ki hai
REPORT_YEAR = {
    ("AAPL", "0000320193-24-000123"): 2024,
    ("AAPL", "0000320193-25-000079"): 2025,
    ("GOOGL", "0001652044-25-000014"): 2024,
    ("GOOGL", "0001652044-26-000018"): 2025,
    ("AMZN", "0001018724-25-000004"): 2024,
    ("AMZN", "0001018724-26-000004"): 2025,
    ("MSFT", "0000950170-25-100235"): 2025,
    ("MSFT", "0001193125-26-323660"): 2026,
    ("TSLA", "0001628280-25-003063"): 2024,
    ("TSLA", "0001628280-26-003952"): 2025,
}

# Sawal mein kaunsa shabd kaunsi company batata hai
COMPANY_WORDS = {
    "apple": "AAPL",
    "alphabet": "GOOGL", "google": "GOOGL",
    "amazon": "AMZN", "aws": "AMZN",
    "microsoft": "MSFT", "azure": "MSFT",
    "tesla": "TSLA",
}


def tokenize(text):
    return re.findall(r"\w+", text.lower())


# DB ke saare chunks ek baar load karo, BM25 ke liye
data = collection.get(include=["documents", "metadatas"])
all_ids = data["ids"]
all_docs = data["documents"]
all_metas = data["metadatas"]
bm25 = BM25Okapi([tokenize(d) for d in all_docs])


def detect_filters(question):
    words = set(tokenize(question))
    tickers = {COMPANY_WORDS[w] for w in words if w in COMPANY_WORDS}
    years = set(re.findall(r"\b(20\d\d)\b", question))
    ticker = tickers.pop() if len(tickers) == 1 else None
    year = int(years.pop()) if len(years) == 1 else None
    return ticker, year


def build_filter(question, use_ticker=True, use_year=True):
    if not use_ticker:
        return None, None
    ticker, year = detect_filters(question)
    if ticker is None:
        return None, None

    reports = [r for (t, r), y in REPORT_YEAR.items()
               if t == ticker and (not use_year or year is None or y == year)]
    if not reports:  # us saal ki report DB mein nahi hai, toh sirf company filter
        reports = [r for (t, r) in REPORT_YEAR if t == ticker]

    where = {"$and": [{"ticker": ticker}, {"report": {"$in": reports}}]}
    allowed = [i for i, m in enumerate(all_metas)
               if m["ticker"] == ticker and m["report"] in reports]
    return where, allowed


def keyword_search(question, n=20, allowed=None):
    scores = bm25.get_scores(tokenize(question))
    indices = range(len(scores)) if allowed is None else allowed
    top = sorted(indices, key=lambda i: scores[i], reverse=True)[:n]
    return [all_ids[i] for i in top]


def semantic_search(question, n=20, where=None):
    q_vec = model.encode([question]).tolist()
    res = collection.query(query_embeddings=q_vec, n_results=n, where=where)
    return res["ids"][0]


def hybrid_search(question, n=20, k=60, where=None, allowed=None):
    # Reciprocal Rank Fusion: dono lists ke rank milao
    scores = {}
    for ranked in (keyword_search(question, n, allowed), semantic_search(question, n, where)):
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)[:n]


def retrieve(question, final_n=5, pool=50, use_reranker=True,
             use_ticker=True, use_year=True):
    where, allowed = build_filter(question, use_ticker, use_year)
    candidate_ids = hybrid_search(question, n=pool, where=where, allowed=allowed)
    id_to_index = {doc_id: i for i, doc_id in enumerate(all_ids)}
    candidates = [(all_docs[id_to_index[i]], all_metas[id_to_index[i]]) for i in candidate_ids]

    if not use_reranker:
        return [(0.0, doc, meta) for doc, meta in candidates[:final_n]]

    pairs = [(question, doc) for doc, _ in candidates]
    rerank_scores = reranker.predict(pairs)

    ranked = sorted(zip(rerank_scores, candidates), key=lambda x: x[0], reverse=True)
    return [(float(s), doc, meta) for s, (doc, meta) in ranked[:final_n]]


if __name__ == "__main__":
    question = "What was Alphabet's total revenue in 2025?"
    for score, doc, meta in retrieve(question):
        print(f"\n--- {meta['ticker']} | {meta['report']} | chunk {meta['chunk']} | score {score:.2f} ---")
        print(doc[:300])