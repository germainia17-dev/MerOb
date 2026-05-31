import ollama
from pathlib import Path

dossier_notes = Path("notes")
contenu_notes = ""

for fichier in dossier_notes.rglob("*.md"):
    texte = fichier.read_text()
    contenu_notes += f"\n\n--- {fichier.name} ---\n{texte}"

messages = [
    {
        "role": "system",
        "content": f"Tu es un assistant personnel. Voici les notes de l'utilisateur : {contenu_notes}"
    }
]

while True:
    question = input("\nToi : ")

    if question.lower() == "quit":
        break

    messages.append({
        "role": "user",
        "content": question
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