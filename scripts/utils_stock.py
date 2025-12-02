# scripts/utils_stock.py
import os
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import ImageFont
import base64
import shutil
import logging

# ===================== DOSSIERS =====================
GIT_REPO_DIR = Path("/opt/render/project/src")  
LOCAL_CACHE_DIR = GIT_REPO_DIR / "Cache"
LOCAL_CACHE_DIR.mkdir(exist_ok=True)

DATA_IDL_DIR = Path("/opt/render/project/src/Data_IDL")
DATA_IDL_CACHE = DATA_IDL_DIR / "Cache"
DATA_IDL_CACHE.mkdir(parents=True, exist_ok=True)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR.parent / "Cache"

RENDER_CACHE_DIR = Path("/opt/render/project/src/render_cache")
RENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

PARQUET_FILE = LOCAL_CACHE_DIR / "ecart_stock_last.parquet"

# ===================== GITHUB =====================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = "IDLAurelienMartin"
GITHUB_REPO = "Data_IDL"
GITHUB_BRANCH = "main"
GIT_REPO_URL = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/Cache"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/Cache/"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ===================== POLICE =====================
FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"

# Chemin absolu basé sur le script
LOG_FILE = BASE_DIR / "prepare_data.log"

logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)



# =====================================================
# Fonctions utilitaires
# =====================================================

def ajouter_totaux(df, colonnes_totaux):
    """Retourne la somme des colonnes spécifiées."""
    return {col: df[col].sum() if col in df.columns else 0 for col in colonnes_totaux} if not df.empty else {col: 0 for col in colonnes_totaux}

def color_rows(row):
    """Coloration conditionnelle pour DataFrame style."""
    return ['background-color: lightgreen' if row.get('Synchro_MMS') == 'Oui' else 'lightcoral'] * len(row)

def update_emplacement(row):
    """Met à jour l'emplacement selon le préfixe."""
    prefix = row.get('prefix_emplacement', '')
    emp = row.get('Emplacement', '')
    if prefix == 'IN':
        return f"{prefix}-{emp}"
    elif prefix == 'UNLOADING':
        return 'DECHARGEMENT'
    elif prefix == 'INSPECTION':
        return f"LITIGES-{emp}"
    else:
        return emp

def harmoniser_et_trier(df, date_col="Date", heure_col="Heure"):
    """Convertit, trie et formate les colonnes Date/Heure."""
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if heure_col in df.columns:
        df[heure_col] = pd.to_datetime(df[heure_col], format="%H:%M:%S", errors="coerce").dt.time

    if date_col in df.columns:
        if heure_col in df.columns:
            df["DateHeure"] = df.apply(
                lambda row: datetime.combine(row[date_col].date(), row[heure_col]) if pd.notna(row[heure_col]) else row[date_col],
                axis=1
            )
            df.sort_values(by="DateHeure", ascending=False, inplace=True)
        else:
            df.sort_values(by=date_col, ascending=False, inplace=True)

    if date_col in df.columns:
        df[date_col] = df[date_col].dt.strftime("%d/%m/%Y")
    if heure_col in df.columns:
        df[heure_col] = df[heure_col].apply(lambda t: t.strftime("%H:%M:%S") if pd.notna(t) else "")

    df.drop(columns="DateHeure", inplace=True, errors="ignore")
    return df

def load_parquet(file_name):
    """Charge un parquet en suivant l'ordre Render → Local → GitHub RAW."""
    # Render cache
    render_path = RENDER_CACHE_DIR / file_name
    if render_path.exists():
        return pd.read_parquet(render_path)

    # Local cache
    local_path = LOCAL_CACHE_DIR / file_name
    if local_path.exists():
        return pd.read_parquet(local_path)

    # GitHub RAW
    github_url = RAW_BASE + file_name
    try:
        r = requests.get(github_url)
        r.raise_for_status()
        return pd.read_parquet(BytesIO(r.content))
    except Exception as e:
        logging.error(f"Impossible de charger {file_name} depuis GitHub : {e}")
        return pd.DataFrame()

def save_parquet_local(df, file_name, copy_to_render=True):
    """Sauvegarde dans le cache local et copie dans Render si demandé."""
    local_path = LOCAL_CACHE_DIR / file_name
    df.to_parquet(local_path, index=False)
    logging.success(f"{file_name} sauvegardé dans Cache/")

    if copy_to_render and RENDER_CACHE_DIR.exists():
        shutil.copy(local_path, RENDER_CACHE_DIR)
        logging.info(f"{file_name} copié dans le cache Render")

def commit_and_push_github():
    """Push automatique sur GitHub via API."""
    if not GITHUB_TOKEN:
        logging.warning("GITHUB_TOKEN non défini, push GitHub ignoré.")
        return

    files_to_push = list(LOCAL_CACHE_DIR.glob("*.*"))
    if not files_to_push:
        logging.info("Aucun fichier à pousser depuis LOCAL_CACHE_DIR.")
        return

    for file_path in files_to_push:
        file_name = file_path.name
        url = f"{GITHUB_API_BASE}/{file_name}"
        content_bytes = file_path.read_bytes()
        encoded = base64.b64encode(content_bytes).decode()

        # Vérifie si le fichier existe déjà
        get_r = requests.get(url, headers=HEADERS)
        sha = get_r.json().get("sha") if get_r.status_code == 200 else None

        data = {
            "message": f"Auto-update {file_name} {datetime.utcnow()}",
            "content": encoded,
            "branch": GITHUB_BRANCH
        }
        if sha:
            data["sha"] = sha

        put_r = requests.put(url, headers=HEADERS, json=data)
        if put_r.status_code in (200, 201):
            logging.success(f"{file_name} mis à jour sur GitHub")
        else:
            logging.error(f"Erreur push {file_name}: {put_r.status_code} → {put_r.text}")
            raise Exception(f"Push failed for {file_name}")

def load_font(font_size: int):
    """Charge une police compatible Render."""
    try:
        return ImageFont.truetype(str(FONT_PATH), font_size)
    except Exception as e:
        logging.error(f"Erreur chargement police : {e}")
        return ImageFont.load_default()
