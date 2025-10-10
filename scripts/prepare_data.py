# scripts/prepare_data.py
import dropbox
import pandas as pd
from pathlib import Path
from io import BytesIO
from preprocess_stock import load_data
from preprocess_stock import preprocess_data
import streamlit as st
import os

def prepare_stock_data_dropbox():
    print("\n=== DÉMARRAGE DU SCRIPT prepare_stock_data_dropbox ===")

    # === 1️ Chargement depuis Dropbox ===
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last,
    ) = load_data()

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

    # === 5️ Upload des fichiers traités vers Dropbox ===
    ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN")
    dbx = dropbox.Dropbox(ACCESS_TOKEN)
    dropbox_output_dir = "/Data_app/Cache"

    def upload_to_dropbox(local_file, dropbox_path):
        """Envoie un fichier local vers Dropbox (remplace si existant)"""
        with open(local_file, "rb") as f:
            dbx.files_upload(
                f.read(),
                dropbox_path,
                mode=dropbox.files.WriteMode("overwrite"),
            )
        print(f"Upload vers Dropbox : {dropbox_path}")

    # Upload de chaque fichier parquet
    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if file_path.exists():
            dropbox_path = f"{dropbox_output_dir}/{file_path.name}"
            upload_to_dropbox(file_path, dropbox_path)

    # Upload du fichier de référence
    file_last_path = output_dir / "file_last.txt"
    file_last_parquet = output_dir / "ecart_stock_last.parquet"
    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))
    upload_to_dropbox(file_last_path, f"{dropbox_output_dir}/file_last.txt")

    # === 6️ Synthèse ===
    print("\n=== SYNTHÈSE DU TRAITEMENT ===")
    print(f"Fichiers Parquet locaux dans : {output_dir}")
    print(f"Fichiers synchronisés vers Dropbox dans : {dropbox_output_dir}")
    print("\nPréparation terminée avec succès.")

if __name__ == "__main__":
    prepare_stock_data_dropbox()
