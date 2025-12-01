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

    # 3) Sauvegarder localement avant upload
    local_cache = Path("/opt/render/project/src/render_cache")
    local_cache.mkdir(exist_ok=True)
    datasets = {
        "mvt_stock.parquet": df_mvt_stock,
        "reception.parquet": df_reception,
        "sorties.parquet": df_sorties,
        "inventaire.parquet": df_inventaire,
        "ecart_stock_last.parquet": df_ecart_stock_last,
        "ecart_stock_prev.parquet": df_ecart_stock_prev,
        "article_euros.parquet": df_article_euros,
        "etat_stock.parquet": df_etat_stock,
    }

    for fname, df in datasets.items():
        local_path = local_cache / fname
        df.to_parquet(local_path, index=False)
        commit_msg = f"Update {fname} via Render {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        us.upload_file_to_github(local_path, fname, commit_msg)

    print("\n=== FIN DU TRAITEMENT ===\n")

# =====================================================
# Exécution principale
# =====================================================
if __name__ == "__main__":
    prepare_stock_data()
