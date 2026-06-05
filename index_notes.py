from pathlib import Path
import chromadb
from embeddings import Embedder

model = Embedder()

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(name="notes")

dossier_notes = Path("notes")

for fichier in dossier_notes.rglob("*.md"):
    texte = fichier.read_text()

    embedding = model.encode(texte).tolist()

    collection.add(
        documents=[texte],
        embeddings=[embedding],
        ids=[str(fichier)]
    )

    print(f"Ajouté : {fichier}")

print("Index terminé.")