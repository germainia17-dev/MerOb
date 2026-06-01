import subprocess
import sys

print("\n===== AI OS MEMORY PIPELINE =====\n")

print("1. Extraction des mémoires...")
extract_result = subprocess.run(
    [sys.executable, "memory_extract_v2.py"]
)

if extract_result.returncode != 0:
    print("Erreur pendant l'extraction.")
    exit()

print("\n2. Validation des mémoires...")
review_result = subprocess.run(
    [sys.executable, "memory_review.py"]
)

if review_result.returncode != 0:
    print("Erreur pendant la validation.")
    exit()

print("\n===== PIPELINE TERMINÉ =====")