# scripts/prepare_data.py
from pathlib import Path
import pandas as pd
from preprocess_stock import load_data, preprocess_data

def prepare_stock_data():

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

    output_dir = Path(__file__).resolve().parent.parent / "Data" / "Cache"
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
        df.to_parquet(output_dir / f"{name}.parquet", index=False)

    # Sauvegarde du chemin du dernier fichier parquet fixe (pas celui du Excel source)
    file_last_path = output_dir / "file_last.txt"
    file_last_parquet = output_dir / "ecart_stock_last.parquet"

    with open(file_last_path, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))

if __name__ == "__main__":
    prepare_stock_data()

