# scripts/prepare_data_drive.py
import pandas as pd
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
service_json = os.environ.get("GOOGLE_SERVICE_JSON")
if not service_json:
    raise ValueError("La variable d'environnement GOOGLE_SERVICE_JSON n'est pas définie.")

credentials_info = pd.json.loads(service_json)
SCOPES = ['https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# ID du dossier Google Drive où les fichiers traités seront uploadés
drive_folder_id = os.environ.get("GOOGLE_DRIVE_OUTPUT_FOLDER_ID")
if not drive_folder_id:
    raise ValueError("L'ID du dossier Google Drive OUTPUT_FOLDER_ID n'est pas défini.")

def upload_to_drive(local_file: Path, folder_id: str):
    """Upload un fichier local vers Google Drive dans le dossier spécifié"""
    file_metadata = {
        'name': local_file.name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(str(local_file), resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"Upload vers Google Drive : {local_file.name} -> ID {uploaded_file.get('id')}")

# --------------------------
# Préparation des données
# --------------------------
def prepare_stock_data_drive():
    print("\n=== DÉMARRAGE DU SCRIPT prepare_stock_data_drive ===")

    # === 1️ Chargement depuis Google Drive ===
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last_parquet,
    ) = load_data()  # load_data adapté pour Google Drive

    # === 2️ Prétraitement ===
    (
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock,
    ) = preprocess_data(
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock,
    )

    # === 3️ Dossier Cache local ===
    output_dir = Path("cache")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Dossier de sortie local : {output_dir}")

    # === 4️ Sauvegarde locale en Parquet ===
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
        else:
            print(f"{name} est vide — non sauvegardé")

    # === 5️ Upload des fichiers traités vers Google Drive ===
    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if file_path.exists():
            upload_to_drive(file_path, drive_folder_id)

    # Upload du fichier de référence
    file_last_path = output_dir / "file_last.txt"
    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))
    upload_to_drive(file_last_path, drive_folder_id)

    # === 6️ Synthèse ===
    print("\n=== SYNTHÈSE DU TRAITEMENT ===")
    print(f"Fichiers Parquet locaux dans : {output_dir}")
    print(f"Fichiers synchronisés vers Google Drive dans le dossier ID : {drive_folder_id}")
    print("\nPréparation terminée avec succès.")


if __name__ == "__main__":
    prepare_stock_data_drive()

