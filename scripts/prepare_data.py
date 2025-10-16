# prepare_data.py
import os
import json
from pathlib import Path
from preprocess_stock import load_data
from preprocess_stock import preprocess_data
import streamlit as st
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --------------------------
# Connexion Google Drive
# --------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']  # accès uniquement aux fichiers créés par l'app

def get_drive_service():
    """Initialise Google Drive API avec service account via GOOGLE_SERVICE_JSON"""
    service_json = os.environ.get("GOOGLE_SERVICE_JSON")
    if not service_json:
        raise ValueError("La variable d'environnement GOOGLE_SERVICE_JSON n'est pas définie.")
    
    creds_info = json.loads(service_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    return service

# --------------------------
# Upload vers Drive
# --------------------------
def upload_to_drive(local_file: Path, folder_id: str, service):
    """Upload un fichier local vers Google Drive dans le dossier spécifié"""
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
    print(f"Upload vers Google Drive : {local_file.name} -> ID {uploaded_file.get('id')}")

# --------------------------
# Préparation des données
# --------------------------
def prepare_stock_data_drive(drive_folder_id: str):
    print("\n=== DÉMARRAGE DU SCRIPT prepare_stock_data_drive ===")

    # Récupération du service Google Drive
    drive_service = get_drive_service()

    # --- Charger et prétraiter les données ---
    from preprocess_stock import load_data, preprocess_data  # ton module existant
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last_parquet
    ) = load_data()  # adapte load_data si nécessaire pour OAuth2

    df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock = preprocess_data(
        df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock
    )

    # === 3️ Dossier Cache local ===
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
            print(f"Fichier sauvegardé localement : {file_path} ({len(df)} lignes)")

    # === 5️ Upload des fichiers traités vers Google Drive ===
    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if file_path.exists():
            upload_to_drive(file_path, os.environ["GOOGLE_DRIVE_INPUT_FOLDER_ID"], drive_service)

    # Upload du fichier de référence
    file_last_path = output_dir / "file_last.txt"
    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))
    upload_to_drive(file_last_path, drive_folder_id, drive_service)

    # === 6️ Synthèse ===
    print("\n=== SYNTHÈSE DU TRAITEMENT ===")
    print(f"Fichiers Parquet locaux dans : {output_dir}")
    print(f"Fichiers synchronisés vers Google Drive dans le dossier ID : {drive_folder_id}")
    print("\nPréparation terminée avec succès.")


if __name__ == "__main__":
    DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_INPUT_FOLDER_ID")
    if not DRIVE_FOLDER_ID:
        raise ValueError("L'ID du dossier Google Drive INPUT_FOLDER_ID n'est pas défini.")
    prepare_stock_data_drive(DRIVE_FOLDER_ID)
