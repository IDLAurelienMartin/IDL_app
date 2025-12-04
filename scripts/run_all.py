# scripts/run_all.py
import subprocess
import sys
from pathlib import Path
import time
# Import local
sys.path.append(str(Path(__file__).resolve().parent))
import utils_stock as us
import streamlit as st
import logging
import threading

# Dossier de base du projet
BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # Python du venv actif

# Dossier local pour le cache
CACHE_DIR = BASE_DIR.parent / "Cache"

# Chemin absolu basé sur le script
SCRIPT_DIR = Path(__file__).parent.resolve()
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
        logging.error("Cache local introuvable. Clonage depuis GitHub...")
        result = subprocess.run(["git", "clone", us.GITHUB_REPO, str(CACHE_DIR)], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("Erreur lors du clonage du dépôt :")
            logging.error(result.stderr)
        else:
            logging.info("Cache cloné avec succès depuis GitHub.")
    else:
        logging.info("Cache local déjà présent.")

def lancer_app():
    """Exécute les scripts de préparation et met à jour l'UI"""
    try:
        ensure_cache_cloned()
        # Liste des scripts de préparation
        scripts = ["preprocess_stock.py", "prepare_data.py"]
        total = len(scripts)
        for idx, script in enumerate(scripts, start=1):
            st.session_state.progress = f"Étape {idx}/{total} : Exécution de {script}..."
            run_script(script)

        st.session_state.progress = "✅ Préparation terminée !"
        logging.info("Préparation des données terminée avec succès.")
    except Exception as e:
        logging.exception("Erreur pendant la préparation des données")
        st.session_state.progress = f"❌ Erreur : {str(e)}"

# --- Streamlit UI ---
# --- Streamlit UI ---
if __name__ == "__main__":
    st.set_page_config(page_title="IDL App", layout="wide")
    st.title("IDL App")

    # Initialise l'état si nécessaire
    if "progress" not in st.session_state:
        st.session_state.progress = "Préparation des données en cours..."
    if "thread_started" not in st.session_state:
        threading.Thread(target=lancer_app, daemon=True).start()
        st.session_state.thread_started = True

    # Affiche l'avancement en continu
    placeholder = st.empty()
    while True:
        placeholder.text(st.session_state.progress)
        time.sleep(1)