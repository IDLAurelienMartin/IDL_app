# scripts/prepare_data.py
import sys
from pathlib import Path
import pandas as pd
import shutil
from datetime import datetime
import subprocess
import os

# Import local
sys.path.append(str(Path(__file__).resolve().parent))
from preprocess_stock import load_data, preprocess_data


# ===============================================
# Configuration Render / GitHub
# ===============================================
SOURCE_FOLDER = Path("/opt/render/project/src/render_cache")
DEST_FOLDER = Path("/opt/render/project/src/Data_app")


# =====================================================
# Sauvegarde automatique vers GitHub (push)
# =====================================================
def backup_to_github(source_path, dest_path, branch="main"):
    source = Path(source_path)
    dest = Path(dest_path)

    shutil.copytree(source, dest, dirs_exist_ok=True)
    print(f"Fichiers copiés de {source} vers {dest}")

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    subprocess.run(["git", "add", "."], cwd=dest, check=False)
    try:
        subprocess.run(["git", "commit", "-m", f"Backup automatique {now}"], cwd=dest, check=True)
    except subprocess.CalledProcessError:
        print("Aucun changement à committer.")

    subprocess.run(["git", "push", "origin", branch], cwd=dest, check=False)
    print("Push GitHub terminé.")


# =====================================================
# Fonctions utilitaires
# =====================================================
def ajouter_totaux(df, colonnes_totaux):
    if df.empty:
        return {col: 0 for col in colonnes_totaux}
    return {col: df[col].sum() if col in df.columns else 0 for col in colonnes_totaux}

def color_rows(row):
    return ['background-color: lightgreen'] * len(row) if row.get('Synchro_MMS') == 'Oui' else ['background-color: lightcoral'] * len(row)

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


# =====================================================
# Pipeline complet : GitHub → Preprocess → Parquet
# =====================================================
def prepare_stock_data():
    print("\n=== SCRIPT prepare_stock_data ===")

    # === 1) Chargement GitHub ===
    (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last_excel_path,
    ) = load_data()        # 100% GitHub !

    # === 2) Prétraitement ===
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

    # === 3) Sauvegarde Parquet sur Render ===
    output_dir = DEST_FOLDER / "render_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Dossier rendu : {output_dir}")

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
        path = output_dir / f"{name}.parquet"
        if not df.empty:
            df.to_parquet(path, index=False)
            print(f"{name}.parquet sauvegardé ({len(df)} lignes)")
        else:
            print(f"{name} est vide — ignoré.")

    # === 4) Enregistrer le dernier fichier traité ===
    file_last_parquet = output_dir / "ecart_stock_last.parquet"
    with open(output_dir / "file_last.txt", "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet))

    print("\n=== SYNTHÈSE ===")
    print(f"Parquets générés dans : {output_dir}")
    print(f"Dernier fichier écart stock : {file_last_parquet}")


    print("\n=== FIN DU TRAITEMENT ===\n")


# =====================================================
# Exécution principale
# =====================================================
if __name__ == "__main__":
    prepare_stock_data()
    backup_to_github(SOURCE_FOLDER, DEST_FOLDER)
