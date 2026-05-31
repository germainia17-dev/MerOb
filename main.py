import ollama
import chromadb
from sentence_transformers import SentenceTransformer

model_embedding = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("notes")

messages = []

while True:
    question = input("\nToi : ")

    if question.lower() == "quit":
        break

    question_embedding = model_embedding.encode(question).tolist()

    resultats = collection.query(
        query_embeddings=[question_embedding],
        n_results=3
    )

    notes_trouvees = resultats["ids"][0]
    contenus_notes = resultats["documents"][0]

    contexte = "\n\n".join(contenus_notes)

    print("\nNotes utilisées :")
    for note in notes_trouvees:
        print(f"- {note}")

    messages.append({
        "role": "user",
        "content": f"""
Voici les notes utiles :

{contexte}

Question de l'utilisateur :
{question}
"""
    })

    response = ollama.chat(
        model="llama3",
        messages=messages
    )

    reponse_ia = response["message"]["content"]

    print("\nIA :")
    print(reponse_ia)

    messages.append({
        "role": "assistant",
        "content": reponse_ia
    })
