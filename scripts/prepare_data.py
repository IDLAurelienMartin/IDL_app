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
    us.RENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
        df["update_ts"] = datetime.now()  # forcage commit
        local_path = us.LOCAL_CACHE_DIR / f"{name}.parquet"
        render_path = us.RENDER_CACHE_DIR / f"{name}.parquet"
        
        df.to_parquet(local_path, index=False)   # sauvegarde locale
        shutil.copy(local_path, render_path)     # copie dans Render cache
        
        st.info(f"{name}.parquet sauvegardé ({len(df)} lignes) et copié dans Render cache")
        
    # Dernier fichier traité
    file_last_parquet = us.LOCAL_CACHE_DIR / "ecart_stock_last.parquet"
    with open(us.LOCAL_CACHE_DIR / "file_last.txt", "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet))
    shutil.copy(us.LOCAL_CACHE_DIR / "file_last.txt", us.RENDER_CACHE_DIR)
    st.info(f"Dernier fichier écart stock : {file_last_parquet} copié dans Render cache")

    # Commit & push via fonction centralisée
    try:
        us.commit_and_push_github()
        st.info("Tous les fichiers parquets commités et poussés sur GitHub.")
    except Exception as e:
        st.error(f"Erreur lors du commit/push GitHub : {e}")

    print("\n=== FIN DU TRAITEMENT ===\n")

# =====================================================
# Exécution principale
# =====================================================
if __name__ == "__main__":
    prepare_stock_data()