# scripts/preprocess_stock.py
import os
import glob
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime
import re
import git
from openpyxl import load_workbook
import streamlit as st

def load_data():
    """
    Charge toutes les données Excel depuis GitHub sur Render.
    Ne conserve que les fichiers postérieurs à la date de création réelle de l'inventaire.
    Inclut les sous-dossiers.
    """

    # === Repo GitHub ===
    GIT_REPO_URL = "https://github.com/IDLAurelienMartin/Data_IDL.git"
    GIT_BRANCH = "main"  # Branche à utiliser
    base_dir = Path("/app/render_data_source")  # emplacement local sur Render

    # Cloner ou mettre à jour le repo
    if base_dir.exists():
        repo = git.Repo(base_dir)
        repo.remotes.origin.pull(GIT_BRANCH)
        print("Repo Git mis à jour depuis GitHub")
    else:
        repo = git.Repo.clone_from(GIT_REPO_URL, base_dir, branch=GIT_BRANCH)
        print("Repo Git cloné depuis GitHub")
    # === Dossier Parquet ===
    cache_dir = base_dir / "Cache"

    # === Lecture des Parquet ===
    def load_parquet_safe(file_path: Path):
        if file_path.exists():
            return pd.read_parquet(file_path)
        else:
            st.warning(f"Impossible de charger {file_path.name} depuis GitHub / Cache")
            return pd.DataFrame()
        
    # === Dossiers / fichiers ===
    dossier_mvt_stock = base_dir / "Mvt_stock"
    dossier_reception = base_dir / "Historique_Reception"
    dossier_sorties = base_dir / "Historique_des_Sorties"
    dossier_ecart_stock = base_dir / "Ecart_Stock"
    file_article = base_dir / "Article_euros.xlsx"
    file_inventaire = base_dir / "Inventory_21_09_2025.xlsx"

    # === Dossier pour cache Parquet ===
    cache_dir = Path("/app/render_data")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # === Lecture de la date de référence ===
    if not file_inventaire.exists():
        raise FileNotFoundError(f"Fichier inventaire manquant : {file_inventaire}")

    def get_excel_creation_date(file_path: Path) -> datetime:
        wb = load_workbook(file_path, read_only=True)
        props = wb.properties
        wb.close()
        return props.created or datetime.fromtimestamp(file_path.stat().st_ctime)

    date_ref = get_excel_creation_date(file_inventaire)
    print(f"Date de création réelle du contenu : {date_ref.strftime('%d/%m/%Y %H:%M')}")

    # === Fonction récursive de concaténation ===
    def concat_excel_from_folder(folder: Path, date_ref: datetime) -> pd.DataFrame:
        if not folder.exists():
            print(f"Dossier introuvable : {folder}")
            return pd.DataFrame()

        fichiers = [
            Path(f) for f in glob.glob(str(folder / "**" / "*.xlsx"), recursive=True)
            if Path(f).stat().st_mtime > date_ref.timestamp()
        ]
        print(f"{len(fichiers)} fichier(s) récents trouvés dans {folder}")
        if not fichiers:
            return pd.DataFrame()
        return pd.concat((pd.read_excel(f) for f in fichiers), ignore_index=True)

    # === Chargement des datasets ===
    df_mvt_stock = concat_excel_from_folder(dossier_mvt_stock, date_ref)
    df_reception = concat_excel_from_folder(dossier_reception, date_ref)
    df_sorties = concat_excel_from_folder(dossier_sorties, date_ref)

    # === ECART STOCK ===
    files = sorted(dossier_ecart_stock.glob("*.xlsx"), key=os.path.getmtime)
    if len(files) < 2:
        raise FileNotFoundError(f"Pas assez de fichiers dans {dossier_ecart_stock} pour comparaison.")
    file_prev, file_last = files[-2], files[-1]

    df_ecart_stock_prev = pd.read_excel(file_prev)
    df_ecart_stock_last = pd.read_excel(file_last)

    # === Fichiers de référence ===
    df_article_euros = pd.read_excel(file_article) if file_article.exists() else pd.DataFrame()
    df_inventaire = pd.read_excel(file_inventaire)

    # === Gestion du cache (Render) ===
    file_last_parquet = cache_dir / "ecart_stock_last.parquet"
    file_last_txt = cache_dir / "file_last.txt"
    with open(file_last_txt, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet))

    # === Synthèse ===
    print("\n=== SYNTHÈSE DU CHARGEMENT ===")
    print(f"Mvt_Stock : {len(df_mvt_stock)} lignes")
    print(f"Réception : {len(df_reception)} lignes")
    print(f"Sorties   : {len(df_sorties)} lignes")
    print(f"Ecart_Stock : {len(df_ecart_stock_last)} lignes")
    print(f"Article_euros : {len(df_article_euros)} lignes")
    print(f"Inventaire : {len(df_inventaire)} lignes")

    return (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last_parquet,
    )


# =========================
# === PREPROCESSING
# =========================
def preprocess_data(
    df_ecart_stock_prev, df_ecart_stock_last, df_reception,
    df_sorties, df_inventaire, df_article_euros, df_mvt_stock, file_last_parquet
):

    # --- Fonctions utilitaires ---
    def remove_duplicate_columns(df):
        if df is None or df.empty:
            return df
        return df.loc[:, ~df.columns.duplicated()]

    def remove_full_duplicate_rows(df):
        if df is None or df.empty:
            return df
        return df.drop_duplicates(keep='first')

    # ================================
    # === Nettoyage ECART STOCK ===
    # ================================
    for df in [df_ecart_stock_prev, df_ecart_stock_last]:
        df.drop(columns=['Var','Locations','MMS Stock (1 piece)','WMS Stock (1 piece)',
                         'Pick qty (1 piece)','Pick qty','Difference (1 piece)'], errors='ignore', inplace=True)
        df.rename(columns={
            "Article Name": "Désignation",
            "Article number (MGB)": "MGB_6",
            "MMS Stock": "MMS_Stock",
            "WMS Stock": "WMS_Stock",
            "Difference": "Difference_MMS-WMS"
        }, inplace=True)
        df['MGB_6'] = df['MGB_6'].astype(str)
        for col in ["MMS_Stock","WMS_Stock","Difference_MMS-WMS"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

    # Colonnes supplémentaires
    for col in ["Date_Dernier_Commentaire", "Commentaire"]:
        if col not in df_ecart_stock_last.columns:
            df_ecart_stock_last[col] = None
        else:
            df_ecart_stock_last[col] = df_ecart_stock_last[col].where(df_ecart_stock_last[col].notna(), None)

    df_ecart_stock_last['Deja_Present'] = df_ecart_stock_last['MGB_6'].isin(df_ecart_stock_prev['MGB_6'])

    # ================================
    # === Nettoyage INVENTAIRE ===
    # ================================
    sys.stdout.reconfigure(encoding='utf-8')
    if not df_inventaire.empty:
        first_col = df_inventaire.columns[0]
        if df_inventaire[first_col].astype(str).str.contains(",").any():
            df_split = df_inventaire[first_col].astype(str).str.split(",", expand=True).iloc[:, :7]
            df_split.columns = ["MGB", "SubSys", "Description", "Initial Quantity", "Final Quantity", "Difference", "Difference (%)"]
            df_inventaire = df_split.copy()
        df_inventaire.rename(columns={
            "SubSys": "Ref_MERTO",
            "Initial Quantity": "Initial_Quantity",
            "Final Quantity": "Inventaire_Final_Quantity",
            "Difference (%)": "Difference_%"
        }, inplace=True)
        if "Inventaire_Final_Quantity" in df_inventaire.columns:
            df_inventaire["Inventaire_Final_Quantity"] = pd.to_numeric(df_inventaire["Inventaire_Final_Quantity"], errors="coerce")
        df_inventaire['MGB'] = df_inventaire['MGB'].astype(str)
        df_inventaire['MGB_6'] = df_inventaire['MGB'].str[:-6]

        remplacement = {"Å“": "œ", "Ã‚": "â", "Ã´": "ô", "Ã¨": "ë", "Ã¢": "â", "Ã§": "ç",
                        "Ãª": "ê", "Ã®": "î", "Ã©": "é", "Â°": "°", "Ã": "à", "¤": "", "«": "", "»": ""}
        if 'Description' in df_inventaire.columns:
            for ancien, nouveau in remplacement.items():
                df_inventaire["Description"] = df_inventaire["Description"].str.replace(ancien, nouveau, regex=False)
    else:
        print("Aucun fichier inventaire trouvé ou vide.")

    # ================================
    # === Fusion anciens commentaires / Render
    # ================================
    if file_last_parquet.exists():
        try:
            df_old = pd.read_parquet(file_last_parquet)
            cols_to_merge = ["MGB_6", "Commentaire", "Date_Dernier_Commentaire"]
            for col in cols_to_merge:
                if col not in df_ecart_stock_last.columns and col in df_old.columns:
                    df_ecart_stock_last[col] = df_old[col]
            print("Anciennes données fusionnées avec succès depuis parquet.")
        except Exception as e:
            print(f"Erreur fusion parquet : {e}")

    # ================================
    # === Sauvegarde finale Render
    # ================================
    df_ecart_stock_last.to_parquet(file_last_parquet, index=False)
    print(f"Fichier ECART STOCK final sauvegardé : {file_last_parquet}")

    return df_ecart_stock_last, df_inventaire

# =========================
# === EXECUTION PRINCIPALE
# =========================
if __name__ == "__main__":
    df_mvt_stock, df_reception, df_sorties, df_inventaire, \
    df_ecart_stock_prev, df_ecart_stock_last, df_article_euros, file_last_parquet = load_data()

    df_ecart_stock_last_clean, df_inventaire_clean = preprocess_data(
        df_ecart_stock_prev, df_ecart_stock_last, df_reception,
        df_sorties, df_inventaire, df_article_euros, df_mvt_stock, file_last_parquet
    )

    print("✅ Préprocessing terminé avec succès !")
