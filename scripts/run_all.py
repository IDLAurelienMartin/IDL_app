import subprocess
import sys
from pathlib import Path
import threading
import logging
import streamlit as st
# Import local
sys.path.append(str(Path(__file__).resolve().parent))
import utils_stock as us

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
CACHE_DIR = BASE_DIR.parent / "Cache"
LOG_FILE = BASE_DIR / "prepare_data.log"

logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_script(script_name):
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        logging.error(f"Script introuvable : {script_name}")
        return
    logging.info(f"Exécution de {script_name} ...")
    result = subprocess.run([PYTHON, str(script_path)], capture_output=True, text=True)
    logging.info(result.stdout)
    if result.stderr:
        logging.error(result.stderr)

def ensure_cache_cloned():
    if not CACHE_DIR.exists():
        logging.info("🌀 Cache local introuvable. Clonage depuis GitHub...")
        result = subprocess.run(["git", "clone", us.GITHUB_REPO, str(CACHE_DIR)], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(result.stderr)
        else:
            logging.info("Cache cloné avec succès depuis GitHub.")
    else:
        logging.info("Cache local déjà présent.")

# --- Interface Streamlit ---
st.set_page_config(page_title="IDL App", layout="wide")
st.title("IDL App")
st.write("Préparation des données en cours... Merci de patienter.")

# --- Exécution en arrière-plan ---
def prepare_data():
    ensure_cache_cloned()
    run_script("preprocess_stock.py")
    run_script("prepare_data.py")
    st.success("Préparation terminée !")

threading.Thread(target=prepare_data).start()
