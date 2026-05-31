from sentence_transformers import SentenceTransformer

print("Chargement du modèle...")

model = SentenceTransformer("all-MiniLM-L6-v2")

texte = "Je travaille sur un OS IA personnel"

embedding = model.encode(texte)

print(f"Longueur du vecteur : {len(embedding)}")
print(embedding[:10])
