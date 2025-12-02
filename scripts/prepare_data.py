# scripts/prepare_data.py
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import subprocess
import os
import shutil
import streamlit as st
import requests
import base64
import logging

# Import local
sys.path.append(str(Path(__file__).resolve().parent))
from preprocess_stock import load_data, preprocess_data
import utils_stock as us

# =====================================================
# Pipeline complet : GitHub → Preprocess → Parquet → GitHub
# =====================================================
def prepare_stock_data():
    st.info("\n=== SCRIPT prepare_stock_data ===")

    # 1) Chargement depuis GitHub
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        df_etat_stock,
        df_excel_ean,
        file_last,
    ) = load_data()        # 100% GitHub

    # 2) Prétraitement
    (
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock,
        df_etat_stock, 
        df_excel_ean,
    ) = preprocess_data(
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_reception,
        df_sorties,
        df_inventaire,
        df_article_euros,
        df_mvt_stock,
        df_etat_stock, 
        df_excel_ean,
    )

    # 3) Sauvegarde Parquet dans GitHub local
    # --- Répertoire temporaire pour les fichiers parquet ---
    LOCAL_TEMP_DIR = Path("./temp_cache")
    LOCAL_TEMP_DIR.mkdir(exist_ok=True)

    #-------test----------
    LOG_FILE = Path("./prepare_data.log")
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # --- Fonction pour push un fichier sur GitHub ---
    def push_file_to_github(file_path: Path, filename: str):
        """Push un fichier directement dans le dossier Cache du repo GitHub."""
        url = f"{us.GITHUB_API_BASE}/{filename}"
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            b64_content = base64.b64encode(content).decode()

            # Vérifie si le fichier existe pour récupérer le SHA
            r = requests.get(url, headers=us.HEADERS)
            if r.status_code == 200:
                sha = r.json().get("sha")
                logging.info(f"{filename} existe déjà sur GitHub, SHA récupéré.")
            else:
                sha = None
                logging.info(f"{filename} n'existe pas encore sur GitHub, création d'un nouveau fichier.")

            data = {"message": f"Update {filename}", "content": b64_content, "branch": "main"}
            if sha:
                data["sha"] = sha

            r_put = requests.put(url, headers=us.HEADERS, json=data)

            if r_put.status_code in [200, 201]:
                logging.info(f"[OK] {filename} pushé sur GitHub")
            else:
                logging.error(f"[ERREUR] {filename} non pushé : {r_put.status_code} - {r_put.text}")
        except Exception as e:
            logging.exception(f"[EXCEPTION] Erreur lors du push de {filename} : {e}")

    # --- DataFrames à push ---
    datasets = {
        "mvt_stock": df_mvt_stock,
        "reception": df_reception,
        "sorties": df_sorties,
        "inventaire": df_inventaire,
        "ecart_stock_last": df_ecart_stock_last,
        "ecart_stock_prev": df_ecart_stock_prev,
        "article_euros": df_article_euros,
        "etat_stock": df_etat_stock,
    }

    # --- Push des fichiers parquet ---
    for name, df in datasets.items():
        temp_file = LOCAL_TEMP_DIR / f"{name}.parquet"
        df.to_parquet(temp_file, index=False)
        push_file_to_github(temp_file, f"{name}.parquet")

    # --- Mettre à jour file_last.txt sur GitHub ---
    file_last_path = LOCAL_TEMP_DIR / "file_last.txt"
    file_last_path.write_text("ecart_stock_last.parquet", encoding="utf-8")
    logging.info(f"Fichier temporaire créé : {temp_file}")
    push_file_to_github(file_last_path, "file_last.txt")

    # --- Nettoyage du répertoire temporaire ---
    shutil.rmtree(LOCAL_TEMP_DIR)

    logging.info("Tous les DataFrames ont été pushés sur GitHub avec file_last.txt mis à jour.")

    logging.info("\n=== FIN DU TRAITEMENT ===\n")

# =====================================================
# Exécution principale
# =====================================================
if __name__ == "__main__":
    prepare_stock_data()