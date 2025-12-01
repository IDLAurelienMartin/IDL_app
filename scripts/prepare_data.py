# scripts/prepare_data.py
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import subprocess
import os
import shutil
import streamlit as st

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
    github_cache = us.GITHUB_LOCAL / "Cache"
    github_cache.mkdir(parents=True, exist_ok=True)
    st.info(f"Dossier local GitHub pour parquets : {github_cache}")

    datasets = {
        "mvt_stock": df_mvt_stock,
        "reception": df_reception,
        "sorties": df_sorties,
        "inventaire": df_inventaire,
        "ecart_stock_last": df_ecart_stock_last,
        "ecart_stock_prev": df_ecart_stock_prev,
        "article_euros": df_article_euros,
        "etat_stock" : df_etat_stock,
    }

    for name, df in datasets.items():
        path = github_cache / f"{name}.parquet"
        # Toujours sauvegarder, même si vide
        df.to_parquet(path, index=False)
        st.info(f"{name}.parquet sauvegardé ({len(df)} lignes)")


    # Enregistrer le dernier fichier traité
    file_last_parquet = github_cache / "ecart_stock_last.parquet"
    with open(github_cache / "file_last.txt", "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet))
    st.info(f"Dernier fichier écart stock : {file_last_parquet}")

    # Commit & push via fonction centralisée
    try:
        us.commit_and_push_github(us.GITHUB_LOCAL, us.GITHUB_BRANCH)
        st.info("Tous les fichiers parquets commités et poussés sur GitHub.")
    except Exception as e:
        st.error(f"Erreur lors du commit/push GitHub : {e}")

    print("\n=== FIN DU TRAITEMENT ===\n")


# =====================================================
# Copier les Parquet depuis GitHub local vers Render cache
# =====================================================
def copy_parquets_to_render_cache(github_local: Path, render_cache: Path):
    render_cache.mkdir(parents=True, exist_ok=True)
    github_cache = github_local / "Cache"

    for file in github_cache.glob("*.parquet"):
        shutil.copy(file, render_cache)
    shutil.copy(github_cache / "file_last.txt", render_cache)
    print(f"Parquets copiés dans le cache Render : {render_cache}")


# =====================================================
# Exécution principale
# =====================================================
if __name__ == "__main__":
    prepare_stock_data()
    copy_parquets_to_render_cache(us.GITHUB_LOCAL, us.RENDER_CACHE)
