# scripts/prepare_data.py
import sys
from pathlib import Path
import pandas as pd
sys.path.append(str(Path(__file__).resolve().parent))
from preprocess_stock import load_data, preprocess_data
import shutil
from datetime import datetime
import subprocess
import platform
import os

# ===============================================
# Configuration des chemins selon l'OS
# ===============================================
if platform.system() == "Windows":
    # Windows local
    SOURCE_FOLDER = Path(r"C:\Users\aumartin\Google Drive\DossierPartage")
    DEST_FOLDER = Path(r"C:\Users\aumartin\Desktop\VSCode\Data_app")
else:
    # Linux / Render.com
    # Remplacer par le chemin du dossier monté ou cloné sur Render
    SOURCE_FOLDER = Path("/mnt/drive/DossierPartage")  # exemple avec rclone
    DEST_FOLDER = Path("/opt/render/project/src/Data_app")

def backup_to_github(source_path, dest_path, branch="main"):
    """
    Copie les fichiers depuis source_path vers dest_path,
    commit et push sur GitHub.
    """
    source = Path(source_path)
    dest = Path(dest_path)

    # Copier les fichiers
    shutil.copytree(source, dest, dirs_exist_ok=True)
    print(f"Fichiers copiés de {source} vers {dest}")

    # Horodatage pour le commit
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Ajouter tous les fichiers
    subprocess.run(["git", "add", "."], cwd=dest, check=True)

    # Commit, ignore si aucun changement
    try:
        subprocess.run(["git", "commit", "-m", f"Backup automatique {now}"], cwd=dest, check=True)
    except subprocess.CalledProcessError:
        print("Aucun changement à committer.")

    # Push vers GitHub
    subprocess.run(["git", "push", "origin", branch], cwd=dest, check=True)
    print("Sauvegarde et push GitHub terminés !")

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
def prepare_stock_data():
    print("\n=== DÉMARRAGE DU SCRIPT prepare_stock_data ===")

    # === Chargement et prétraitement ===
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

    # === Dossier local Render pour les Parquet ≤10Mo ===
    output_dir = Path("/app/render_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Dossier de sortie (Render) : {output_dir}")

    # === Dictionnaire des DataFrames à sauvegarder ===
    datasets = {
        "mvt_stock": df_mvt_stock,
        "reception": df_reception,
        "sorties": df_sorties,
        "inventaire": df_inventaire,
        "ecart_stock_last": df_ecart_stock_last,
        "ecart_stock_prev": df_ecart_stock_prev,
        "article_euros": df_article_euros,
    }

    # === Sauvegarde en parquet dans Render ===
    for name, df in datasets.items():
        file_path = output_dir / f"{name}.parquet"
        if not df.empty:
            df.to_parquet(file_path, index=False)
            print(f"Fichier sauvegardé : {file_path} ({len(df)} lignes)")
        else:
            print(f"{name} est vide — non sauvegardé")

    # === Sauvegarde du chemin du dernier fichier Parquet ===
    file_last_path = output_dir / "file_last.txt"
    file_last_parquet = output_dir / "ecart_stock_last.parquet"

    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet))  # chemin compatible Render

    print("\n=== SYNTHÈSE DU TRAITEMENT ===")
    print(f"Fichiers Parquet créés dans : {output_dir}")
    print(f"Chemin du dernier Parquet enregistré dans : {file_last_path}")

    print("\nPréparation terminée avec succès.")

if __name__ == "__main__":
    prepare_stock_data()
    backup_to_github(SOURCE_FOLDER, DEST_FOLDER)
