import os
import time
from dotenv import load_dotenv
from google import genai
from retrieval import retrieve

load_dotenv()
client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.1-flash-lite"

def build_prompt(question, results):
    context = "" 
    for i, (score, doc, meta) in enumerate(results, start = 1):
        context += (
            f"[Source {i}: {meta["ticker"]} | report {meta['report']} | chunk {meta['chunk']}] \n"
            f"{doc}\n\n"
        )

    return f"""You are a helpful assistant that answers questions about company annual reports (10-K filings).

Rules:
1. Answer ONLY using the context below.
2. If the answer is not in the context, say "I don't know based on the provided documents."
3. After each fact, cite the source like [Source 1].
4. Keep the answer short and clear.

Context:
{context}

Question: {question}

Answer:"""

def answer(question):
    results = retrieve(question, final_n=5)
    prompt = build_prompt(question, results)

    for attempt in range(4):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text, results
        except Exception as e:
            if "503" in str(e) and attempt < 3:
                print(f"Server busy, {10 * (attempt + 1)} second baad dobara try...")
                time.sleep(10 * (attempt + 1))
            else:
                raise

# def answer(question):
#     results = retrieve(question, final_n = 5)
#     prompt = build_prompt(question, results)
#     response = client.models.generate_content(model = MODEL, contents = prompt)
#     return response.text, results

if __name__ == "__main__":
    question = "what is the capital of India?"
    text, results = answer(question)

    print("SAWAL : ", question)
    print("\nJAWAB : \n", text)
    print("\nSOURCES : ")

    for i, (score, doc, meta) in enumerate(results, start = 1):
        print(f"[source {i}] {meta["ticker"]} | {meta["report"]} | chunk {meta['chunk']}")
