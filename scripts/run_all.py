# scripts/run_all.py
import subprocess
import sys
from pathlib import Path

# Dossier de base du projet
BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # Python du venv actif

# Dossier local pour le cache
CACHE_DIR = BASE_DIR.parent / "Cache"

# URL du dépôt GitHub contenant les fichiers parquet
GITHUB_REPO = "https://github.com/IDLAurelienMartin/Data_IDL.git"

def run_script(script_name):
    """Exécute un script Python et affiche le résultat."""
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f"Script introuvable : {script_name}")
        return
    print(f"\nExécution de {script_name} ...")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Erreurs ou avertissements :")
        print(result.stderr)

def ensure_cache_cloned():
    """Clone le dépôt GitHub si le cache n'existe pas localement."""
    if not CACHE_DIR.exists():
        print("🌀 Cache local introuvable. Clonage depuis GitHub...")
        result = subprocess.run(["git", "clone", GITHUB_REPO, str(CACHE_DIR)], capture_output=True, text=True)
        if result.returncode != 0:
            print("Erreur lors du clonage du dépôt :")
            print(result.stderr)
        else:
            print("Cache cloné avec succès depuis GitHub.")
    else:
        print("Cache local déjà présent.")

if __name__ == "__main__":
    ensure_cache_cloned()

    # Exécution des scripts de préparation
    run_script("preprocess_stock.py")
    run_script("prepare_data.py")

    # Lancement de l’application Streamlit
    streamlit_app = BASE_DIR.parent / "IDL_app.py"
    if streamlit_app.exists():
        print("\nLancement de l'application Streamlit...")
        subprocess.run([PYTHON, "-m", "streamlit", "run", str(streamlit_app)])
    else:
        print(f"Application Streamlit introuvable : {streamlit_app}")

