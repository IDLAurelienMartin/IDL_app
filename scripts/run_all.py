import subprocess
import sys
from pathlib import Path

# --------------------------
# Configuration
# --------------------------
BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # Python du venv actif

# --------------------------
# Fonction pour exécuter un script
# --------------------------
def run_script(script_name: str):
    """
    Exécute un script Python et affiche les logs stdout/stderr.
    """
    script_path = BASE_DIR / script_name
    print(f"\n=== Exécution de {script_name} ===")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)

    # Affichage stdout
    if result.stdout:
        print(result.stdout)

    # Affichage stderr
    if result.stderr:
        print("⚠️ Erreurs / avertissements :")
        print(result.stderr)

# --------------------------
# Script principal
# --------------------------
if __name__ == "__main__":
    # 1️⃣ Prétraitement des données
    run_script("preprocess_stock.py")  # Chargement / nettoyage / OAuth Google Drive

    # 2️⃣ Préparation et génération du cache parquet
    run_script("prepare_data.py")      # Prépare les fichiers .parquet et upload Drive

    # 3️⃣ Fonctions utilitaires (optionnel selon usage)
    run_script("utils_stock.py")       # Fonctions utilitaires pour affichage / totaux

    # 4️⃣ Lancement de l'application Streamlit
    app_path = BASE_DIR.parent / "IDL_app.py"
    print(f"\n🚀 Lancement de l'application Streamlit : {app_path}")
    subprocess.run([PYTHON, "-m", "streamlit", "run", str(app_path)])
