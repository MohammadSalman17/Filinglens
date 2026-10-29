from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from chunking import chunk_text

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path = "vectorstore")
collection = client.get_or_create_collection(
    name = "reports", metadata = {"hnsw:space": "cosine"}
)

def build_index():
    for file in Path("data/processed").glob("*.txt"):
        ticker, accession = file.stem.split("_",1)
        text = file.read_text(encoding = "utf-8")
        chunks = chunk_text(text)
        vectors = model.encode(chunks, show_progress_bar = True)

        collection.upsert(
            ids=[f"{file.stem}_{i}" for i in range(len(chunks))],
            documents = chunks,
            embeddings = vectors.tolist(),
            metadatas = [
                {"ticker": ticker, "report":accession, "chunk" : i}
                for i in range(len(chunks))
            ],
        )
        print(f"{file.name}: {len(chunks)} chunks saved")

def search(question, n = 3):
    q_vec = model.encode([question]).tolist()
    return collection.query(query_embeddings = q_vec, n_results = n)

if __name__ == "__main__":
    build_index()
    print("total chunks in DB : ", collection.count())

    res = search("what are the risks related to suppliers and manufactuting ?")
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        print(f"\n {meta["ticker"]} | {meta["report"]} | chunk {meta["chunk"]}")
        print(doc[:300])