# scripts/run_all.py
import subprocess
import sys
from pathlib import Path
# Import local
sys.path.append(str(Path(__file__).resolve().parent))
import utils_stock as us
import base64
import logging

# Dossier de base du projet
BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # Python du venv actif

# Dossier local pour le cache
CACHE_DIR = BASE_DIR.parent / "Cache"

# Chemin absolu basé sur le script
SCRIPT_DIR = Path(__file__).parent.resolve() / "scripts"
LOG_FILE = SCRIPT_DIR / "prepare_data.log"

logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)




def run_script(script_name):
    """Exécute un script Python et affiche le résultat."""
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        logging.error(f"Script introuvable : {script_name}")
        return
    logging.info(f"\nExécution de {script_name} ...")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)
    logging.info(result.stdout)
    if result.stderr:
        logging.error("Erreurs ou avertissements :")
        logging.error(result.stderr)

def ensure_cache_cloned():
    """Clone le dépôt GitHub si le cache n'existe pas localement."""
    if not CACHE_DIR.exists():
        logging.error("🌀 Cache local introuvable. Clonage depuis GitHub...")
        result = subprocess.run(["git", "clone", us.GITHUB_REPO, str(CACHE_DIR)], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("Erreur lors du clonage du dépôt :")
            logging.error(result.stderr)
        else:
            logging.info("Cache cloné avec succès depuis GitHub.")
    else:
        logging.info("Cache local déjà présent.")

if __name__ == "__main__":
    ensure_cache_cloned()

    # Exécution des scripts de préparation
    run_script("preprocess_stock.py")
    run_script("prepare_data.py")

    # Lancement de l’application Streamlit
    streamlit_app = BASE_DIR.parent / "IDL_app.py"
    if streamlit_app.exists():
        logging.info("\nLancement de l'application Streamlit...")
        subprocess.run([PYTHON, "-m", "streamlit", "run", str(streamlit_app)])
    else:
        logging.error(f"Application Streamlit introuvable : {streamlit_app}")

