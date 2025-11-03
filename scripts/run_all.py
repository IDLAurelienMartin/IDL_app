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
    if not script_path.exists():
        print(f"Script introuvable : {script_name}")
        return
    print(f"\nExécution de {script_name} ...")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Erreurs ou avertissements :")
        print(result.stderr)

if __name__ == "__main__":
    # Ordre d’exécution des scripts
    run_script("preprocess_stock.py")   # Chargement et preprocessing des fichiers Excel
    run_script("prepare_data.py")       # Préparation et génération du cache parquet
    
    # Lancement de l’application Streamlit
    streamlit_app = BASE_DIR.parent / "IDL_app.py"
    if streamlit_app.exists():
        print("\nLancement de l'application Streamlit...")
        subprocess.run([PYTHON, "-m", "streamlit", "run", str(streamlit_app)])
    else:
        print(f"Application Streamlit introuvable : {streamlit_app}")
