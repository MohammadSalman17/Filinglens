from pathlib import Path 

def chunk_text(text, chunk_size = 1000, overlap = 200):
    chunks = []
    start = 0 
    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunks.append(text[start:end].strip())

        if end >= len(text):
            break

        next_start = end - overlap
        space = text.find(" ", next_start, end)
        start = space + 1 if space != -1 else end
    return chunks

if __name__ == "__main__":
    file = next(Path("data/processed").glob("*.txt"))
    text = file.read_text(encoding = "utf-8")
    chunks = chunk_text(text)

    print("file : ", file.name)
    print("Total chunks: ", len(chunks))
    print(chunks[50])
    print(chunks[51])