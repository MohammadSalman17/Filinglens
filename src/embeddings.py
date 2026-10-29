from sentence_transformers import SentenceTransformer
from chunking import chunk_text
from pathlib import Path

model = SentenceTransformer("all-MiniLM-L6-v2")

if __name__ == "__main__":
    file = next(Path("data/processed").glob("*.txt"))
    text = file.read_text(encoding="utf-8")
    chunks = chunk_text(text)

    vectors = model.encode(chunks, show_progress_bar = True)
    print("Vector's Shape : ", vectors.shape)

    from sentence_transformers import util
    sawal = "what are the risks related to suppliers and manufatureing ?"
    sawal_vec = model.encode([sawal])

    scores = util.cos_sim(sawal_vec, vectors)[0]

    top3 = scores.argsort(descending = True)[:3]
    for rank, idx in enumerate(top3, start = 1):
        print(f"\nrank {rank} | chunk {int(idx)} | score {float(scores[idx]):.3f}")
        print(chunks[int(idx)])