import os
import json
from pathlib import Path
from preprocess_stock import load_data, preprocess_data
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --------------------------
# Scopes Drive
# --------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --------------------------
# Connexion Google Drive
# --------------------------
def get_drive_service():
    """
    Initialise Google Drive API via service account.
    Priorité : variable d'environnement GOOGLE_SERVICE_JSON, sinon fichier local.
    """
    service_json = os.environ.get("GOOGLE_SERVICE_JSON")

    if service_json:
        credentials_info = json.loads(service_json)
    else:
        local_path = Path("IDL_DB/service_account.json")
        if not local_path.exists():
            raise ValueError(
                "GOOGLE_SERVICE_JSON non défini et fichier local service_account.json absent."
            )
        with open(local_path, "r", encoding="utf-8") as f:
            credentials_info = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    return service

# --------------------------
# Upload d'un fichier vers Drive
# --------------------------
def upload_to_drive(local_file: Path, folder_id: str, service):
    """Upload un fichier local vers Google Drive dans le dossier spécifié."""
    file_metadata = {
        'name': local_file.name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(str(local_file), resumable=True)
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"Upload Drive : {local_file.name} -> ID {uploaded_file.get('id')}")

# --------------------------
# Préparation complète des données
# --------------------------
def prepare_stock_data_drive(drive_folder_id: str):
    print("\n=== DÉMARRAGE DU SCRIPT prepare_stock_data_drive ===")

    # Connexion Drive
    drive_service = get_drive_service()

    # --------------------------
    # 1️⃣ Charger et prétraiter les données
    # --------------------------
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last_parquet,
    ) = load_data()

    (
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock
    ) = preprocess_data(
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock
    )

    # --------------------------
    # 2️⃣ Sauvegarde locale
    # --------------------------
    output_dir = Path("cache")
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "mvt_stock": df_mvt_stock,
        "reception": df_reception,
        "sorties": df_sorties,
        "inventaire": df_inventaire,
        "ecart_stock_last": df_ecart_stock_last,
        "ecart_stock_prev": df_ecart_stock_prev,
        "article_euros": df_article_euros,
    }

    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if not df.empty:
            df.to_parquet(file_path, index=False)
            print(f"Fichier local sauvegardé : {file_path} ({len(df)} lignes)")

    # --------------------------
    # 3️⃣ Upload vers Google Drive
    # --------------------------
    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if file_path.exists():
            upload_to_drive(file_path, os.environ["GOOGLE_DRIVE_INPUT_FOLDER_ID"], drive_service)

    # Upload fichier de référence
    file_last_path = output_dir / "file_last.txt"
    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))
    upload_to_drive(file_last_path, drive_folder_id, drive_service)

    # --------------------------
    # 4️⃣ Synthèse
    # --------------------------
    print("\n=== SYNTHÈSE DU TRAITEMENT ===")
    print(f"Fichiers Parquet locaux : {output_dir}")
    print(f"Fichiers synchronisés sur Google Drive dans le dossier ID : {drive_folder_id}")
    print("\nPréparation terminée avec succès.")

# --------------------------
# Script principal
# --------------------------
if __name__ == "__main__":
    DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_INPUT_FOLDER_ID")

    if DRIVE_FOLDER_ID:
        print(f"Utilisation du dossier Google Drive : {DRIVE_FOLDER_ID}")
        prepare_stock_data_drive(DRIVE_FOLDER_ID)
    else:
        LOCAL_PATH = r"1RFdl9UjyeZioxDFkkK_g0DiZUGwMUA4O"
        print(f"Aucun ID Drive défini, utilisation du dossier local : {LOCAL_PATH}")
        prepare_stock_data_drive(LOCAL_PATH)
