from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("notes")

question = input("Question : ")

embedding = model.encode(question).tolist()

resultats = collection.query(
    query_embeddings=[embedding],
    n_results=3
)

print("\nNotes trouvées :\n")

for note in resultats["ids"][0]:
    print(note)