# scripts/run_all.py
import subprocess
import sys
from pathlib import Path

# Dossier de base du projet
BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # Python du venv actif


def run_script(script_name):
    """Exécute un script Python et affiche le résultat."""
    script_path = BASE_DIR / script_name
    print(f"\nExécution de {script_name} ...")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Erreurs ou avertissements :")
        print(result.stderr)


if __name__ == "__main__":
    # 🔁 Ordre d’exécution des scripts
    run_script("preprocess_stock.py")   # 1️⃣ Prétraitement des fonctions utilitaires
    run_script("prepare_data.py")       # 2️⃣ Préparation et génération du cache parquet
    run_script("utils_stock.py")        # 3️⃣ Fonctions d’assistance

    # 🚀 Lancement de l’application Streamlit
    print("\nLancement de l'application Streamlit...")
    subprocess.run([PYTHON, "-m", "streamlit", "run", str(BASE_DIR.parent / "IDL_app.py")])



