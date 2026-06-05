from pathlib import Path
import chromadb
from embeddings import Embedder

model = Embedder()

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(name="notes")

notes_dir = Path("notes")

for file in notes_dir.rglob("*.md"):
    text = file.read_text()

    embedding = model.encode(text).tolist()

    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[str(file)]
    )

    print(f"Added: {file}")

print("Indexing complete.")
