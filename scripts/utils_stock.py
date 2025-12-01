#scripts/utils_stock.py
import os
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import ImageFont
import subprocess

# --- Dossier cache local sur Render ---
# Render place les fichiers persistants dans le dossier /opt/render/project/src/render_cache
GIT_REPO_DIR = Path("/opt/render/project/src")  # ton repo local
LOCAL_CACHE_DIR = GIT_REPO_DIR / "Cache"
LOCAL_CACHE_DIR.mkdir(exist_ok=True)

# --- Dossiers ---
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR.parent / "Cache"
RENDER_CACHE_DIR = Path("/opt/render/project/src/render_cache")  # lecture seule
RENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- GitHub RAW pour Data_IDL ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = "IDLAurelienMartin"
GITHUB_REPO = "Data_IDL"
GITHUB_BRANCH = "main"
GIT_REPO_URL = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/Cache/"

# --- Dossiers ---
PARQUET_FILE = LOCAL_CACHE_DIR / "ecart_stock_last.parquet"

# --- Chargement police compatible Render ---

FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"

def ajouter_totaux(df, colonnes_totaux):
    if df.empty:
        return {col: 0 for col in colonnes_totaux}
    return {col: df[col].sum() if col in df.columns else 0 for col in colonnes_totaux}

def color_rows(row):
    if row.get('Synchro_MMS') == 'Oui':
        return ['background-color: lightgreen'] * len(row)
    else:
        return ['background-color: lightcoral'] * len(row)

def update_emplacement(row):
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

def commit_and_push_github(local_repo: Path, branch: str, token_env_var: str = "GITHUB_TOKEN"):
    """
    Commit et push des changements depuis le repo local vers GitHub.
    local_repo: dossier racine du repo
    branch: branche GitHub
    token_env_var: nom de la variable d'environnement contenant le token
    """
    token = os.environ.get(token_env_var)
    if not token:
        print("⚠️ GitHub token non trouvé dans les variables d'environnement.")
        return

    # Configurer le remote temporaire avec token
    remote_url = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=local_repo,
        capture_output=True,
        text=True
    ).stdout.strip()

    if remote_url.startswith("https://"):
        auth_remote = remote_url.replace("https://", f"https://{token}@")
    else:
        print("⚠️ URL du remote non HTTPS, push impossible via token.")
        return

    # Ajouter tous les fichiers modifiés
    subprocess.run(["git", "add", "."], cwd=local_repo, check=False)

    # Vérifier s'il y a quelque chose à committer
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=local_repo)
    if result.returncode == 0:
        print("Aucun changement à committer.")
        return

    # Commit
    commit_message = f"Update parquets {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        subprocess.run(["git", "commit", "-m", commit_message], cwd=local_repo, check=True)
        # Push
        subprocess.run(["git", "push", auth_remote, branch], cwd=local_repo, check=True)
        print("✅ Push GitHub terminé avec succès.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du commit ou push : {e}")

def harmoniser_et_trier(df, date_col="Date", heure_col="Heure"):
    # Conversion des colonnes
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if heure_col in df.columns:
        # Convertir en time uniquement
        df[heure_col] = pd.to_datetime(df[heure_col], format="%H:%M:%S", errors="coerce").dt.time

    # Créer colonne temporaire pour le tri
    if date_col in df.columns:
        if heure_col in df.columns:
            df["DateHeure"] = df.apply(
                lambda row: datetime.combine(row[date_col].date(), row[heure_col])
                if pd.notna(row[heure_col]) else row[date_col],
                axis=1
            )
            df.sort_values(by="DateHeure", ascending=False, inplace=True)
        else:
            df.sort_values(by=date_col, ascending=False, inplace=True)

    # Harmoniser l'affichage
    if date_col in df.columns:
        df[date_col] = df[date_col].dt.strftime("%d/%m/%Y")
    if heure_col in df.columns:
        df[heure_col] = df[heure_col].apply(lambda t: t.strftime("%H:%M:%S") if pd.notna(t) else "")

    # Supprimer colonne temporaire
    if "DateHeure" in df.columns:
        df.drop(columns="DateHeure", inplace=True)

    return df

def load_parquet(file_name):
    """
    Charge un parquet en suivant cet ordre :
    1) Render cache
    2) Local cache interne (Cache/)
    3) GitHub RAW (Data_IDL)
    """
    # 1) Render cache
    render_path = RENDER_CACHE_DIR / file_name
    if render_path.exists():
        return pd.read_parquet(render_path)
    
    # 2) Local cache
    local_path = LOCAL_CACHE_DIR / file_name
    if local_path.exists():
        return pd.read_parquet(local_path)
    
    # 3) GitHub RAW fallback
    github_url = RAW_BASE + file_name
    try:
        r = requests.get(github_url)
        r.raise_for_status()
        df = pd.read_parquet(BytesIO(r.content))
        return df
    except Exception as e:
        st.error(f"Impossible de charger {file_name} depuis GitHub : {e}")
        return pd.DataFrame()

def save_parquet_local(df, file_name):
    """
    Sauvegarde UNIQUE dans le dossier Cache/ interne.
    Render ne permet pas d'écrire dans render_cache (lecture seule).
    """
    local_path = LOCAL_CACHE_DIR / file_name
    df.to_parquet(local_path, index=False)
    st.success(f"{file_name} sauvegardé dans Cache/")

def load_font(font_size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), font_size)
    except Exception as e:
        st.error(f"Erreur chargement police : {e}")
        return ImageFont.load_default()
