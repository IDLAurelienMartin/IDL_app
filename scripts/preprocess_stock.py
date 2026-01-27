# scripts/preprocess_stock_cloud.py
import pandas as pd
import numpy as np
import requests
import io
import unicodedata
import re
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
import glob
import os

def load_data():
    """
    Charge tous les fichiers Excel récents depuis un dossier GitHub.
    Ne garde que ceux plus récents que la date de référence.
    """

    # === Dossiers ===
    partage_base = Path("https://raw.githubusercontent.com/IDLAurelienMartin/Data_IDL/main")
    dossier_mvt_stock = partage_base / "Mvt_stock"
    dossier_reception = partage_base / "Historique_Reception"
    dossier_sorties = partage_base / "Historique_des_Sorties"
    dossier_ecart_stock = partage_base / "Ecart_Stock"
    dossier_etat_stock = partage_base / "Etat_Stock"
    Base_Article = partage_base / r"Base_Article\Base Article V2.xlsx"
    file_article = partage_base / r"Base_Article\Article €.xlsx"
    file_inventaire = partage_base / r"Inventory_21_09_2025.xlsx"
    cache_dir = Path("./Cache")
    file_excel_ean = partage_base / r"\Detrompeur\Liste detrompeur + EAN.xlsx"

    cache_dir.mkdir(parents=True, exist_ok=True)

    # --- Fichier état stock le plus récent (CSV ou Excel) ---
    fichiers = (
        list(dossier_etat_stock.glob("*.csv")) +
        list(dossier_etat_stock.glob("*.xlsx")) +
        list(dossier_etat_stock.glob("*.xls"))
    )

    if not fichiers:
        raise FileNotFoundError(
            "Aucun fichier CSV ou Excel trouve dans le dossier Etat_Stock"
        )

    # Dernier fichier modifié
    file_etat_stock = max(fichiers, key=lambda f: f.stat().st_mtime)
    print("Fichier Etat Stock utilise :", file_etat_stock)

    # file_etat_stock = dernier fichier sélectionné (CSV ou Excel)

    if file_etat_stock.suffix.lower() == ".csv":
        df_etat_stock = pd.read_csv(
            file_etat_stock,
            sep=None,          # auto-détection séparateur
            engine="python",
            encoding="latin-1",
            encoding_errors="ignore",
            on_bad_lines="skip"
        )
        # Si tout est dans une seule colonne, on peut splitter :
        if df_etat_stock.shape[1] == 1:
            df_etat_stock = df_etat_stock.iloc[:, 0].str.split(",", expand=True)
    else:
        # Excel
        df_etat_stock = pd.read_excel(
            file_etat_stock,
            sheet_name=0,
            engine='openpyxl'
        )

    # === Date de référence ===
    def get_excel_creation_date(file_path: Path) -> datetime:
        """Récupère la date de création interne d'un fichier Excel (.xlsx)."""
        wb = load_workbook(file_path, read_only=True)
        props = wb.properties
        wb.close()
        if props.created:
            return props.created
        raise ValueError("Date de creation non trouvee dans les metadonnees Excel")

    # Date inventaire (Excel obligatoire)
    if not file_inventaire.exists():
        raise FileNotFoundError(f"Fichier inventaire manquant : {file_inventaire}")

    try:
        date_ref = get_excel_creation_date(file_inventaire)
        print(f"Date de creation reelle du contenu : {date_ref.strftime('%d/%m/%Y')}")
    except Exception as e:
        print(f"Fallback date systeme inventaire : {e}")
        date_ref = datetime.fromtimestamp(file_inventaire.stat().st_ctime)

    # === Fonction récursive de concaténation ===
    def concat_excel_from_folder(folder: Path, date_ref: datetime) -> pd.DataFrame:
        """
        Charge tous les fichiers Excel récents depuis un dossier et ses sous-dossiers.
        Ne garde que ceux plus récents que la date de référence.
        Affiche les fichiers problématiques et la raison de l'échec.
        """
        if not folder.exists():
            print(f"Dossier introuvable : {folder}")
            return pd.DataFrame()

        fichiers = [
            Path(f) for f in glob.glob(str(folder / "**" / "*.xlsx"), recursive=True)
            if Path(f).stat().st_mtime > date_ref.timestamp()
        ]

        print(f"{len(fichiers)} fichier(s) recents trouves (y compris sous-dossiers) dans {folder}")

        if not fichiers:
            return pd.DataFrame()

        dfs = []
        for f in fichiers:
            try:
                df = pd.read_excel(f, dtype=str, sheet_name=0, engine='openpyxl')
                dfs.append(df)
            except Exception as e:
                msg = str(e).encode("utf-8", errors="replace").decode("utf-8")
                print(f"Impossible de lire le fichier {f}: {type(e).__name__} - {msg}")

        if not dfs:
            print("Aucun fichier valide n'a pu etre charge.")
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    # === Chargement des datasets ===
    df_mvt_stock = concat_excel_from_folder(dossier_mvt_stock, date_ref)
    df_reception = concat_excel_from_folder(dossier_reception, date_ref)
    df_sorties = concat_excel_from_folder(dossier_sorties, date_ref)

    # === Cas spécial : ECART STOCK ===
    files = sorted(dossier_ecart_stock.glob("*.xlsx"), key=os.path.getmtime)
    if len(files) < 2:
        raise FileNotFoundError(f"Pas assez de fichiers dans {dossier_ecart_stock} pour comparaison.")
    file_prev, file_last = files[-2], files[-1]

    df_ecart_stock_prev = pd.read_excel(file_prev)
    df_ecart_stock_last = pd.read_excel(file_last)
    Base_Article = pd.read_excel(Base_Article)
    
    # --- Lire le fichier Excel des EAN ---
    df_excel_ean = pd.read_excel(file_excel_ean, sheet_name=0, engine='openpyxl')

    # === Fichiers de référence ===
    df_article_euros = pd.read_excel(file_article) if file_article.exists() else pd.DataFrame()
    df_inventaire = pd.read_excel(file_inventaire)

    # === Gestion du cache ===
    file_last_parquet = cache_dir / "ecart_stock_last.parquet"
    file_last_txt = cache_dir / "file_last.txt"

    with open(file_last_txt, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))

    print("\n=== SYNTHÈSE DU CHARGEMENT ===")
    print(f"Mvt_Stock : {len(df_mvt_stock)} lignes")
    print(f"Réception : {len(df_reception)} lignes")
    print(f"Sorties   : {len(df_sorties)} lignes")
    print(f"Ecart_Stock : {len(df_ecart_stock_last)} lignes")
    print(f"Article_euros : {len(df_article_euros)} lignes")
    print(f"Inventaire : {len(df_inventaire)} lignes")
    print("=== df_etat_stock avant preprocess ===")
    print(type(df_etat_stock))
    print(df_etat_stock.info())
    print(df_etat_stock.head())  
    
    return (
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
        date_ref,
        Base_Article,
    )

# -------------------------------
# Preprocess data
# -------------------------------
def preprocess_data(
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        df_etat_stock,
        df_excel_ean,
        date_ref,
        Base_Article,
    ): 
        print("\n=== PREPROCESSING DES DONNEES ===")
        print(pd.__version__)
        print(f"date_ref : {date_ref}, type : {type(date_ref)}")
        

        df_ecart_stock_prev = df_ecart_stock_prev.drop(columns=['Var','Locations','MMS Stock (1 piece)','WMS Stock (1 piece)',
                                                    'Pick qty (1 piece)','Pick qty','Difference (1 piece)'], errors='ignore')
        df_ecart_stock_prev = df_ecart_stock_prev.rename(columns={
            "Article Name": "Désignation",
            "Article number (MGB)": "MGB_6",
            "MMS Stock": "MMS_Stock : Metro",
            "WMS Stock": "WMS_Stock : IDL",
            "Difference": "Difference_MMS-WMS"
        })
        df_ecart_stock_prev['MGB_6'] = df_ecart_stock_prev['MGB_6'].astype(str)
        for col in ["MMS_Stock : Metro","WMS_Stock : IDL","Difference_MMS-WMS"]:
            df_ecart_stock_prev[col] = pd.to_numeric(df_ecart_stock_prev[col], errors='coerce')

        df_ecart_stock_last = df_ecart_stock_last.drop(columns=['Var','Locations','MMS Stock (1 piece)','WMS Stock (1 piece)',
                                                    'Pick qty (1 piece)','Pick qty','Difference (1 piece)'], errors='ignore')
        df_ecart_stock_last = df_ecart_stock_last.rename(columns={
            "Article Name": "Désignation",
            "Article number (MGB)": "MGB_6",
            "MMS Stock": "MMS_Stock : Metro",
            "WMS Stock": "WMS_Stock : IDL",
            "Difference": "Difference_MMS-WMS"
        })
        df_ecart_stock_last['MGB_6'] = df_ecart_stock_last['MGB_6'].astype(str)

        colonnes_a_ajouter = ["Date_Dernier_Commentaire", "Commentaire"]
        for col in colonnes_a_ajouter:
            if col not in df_ecart_stock_last.columns:
                df_ecart_stock_last[col] = None
            else:
                df_ecart_stock_last[col] = df_ecart_stock_last[col].where(df_ecart_stock_last[col].notna(), None)

        for col in ["MMS_Stock : Metro","WMS_Stock : IDL","Difference_MMS-WMS"]:
            df_ecart_stock_last[col] = pd.to_numeric(df_ecart_stock_last[col], errors='coerce')
        
        df_ecart_stock_prev['MGB_6'] = df_ecart_stock_prev['MGB_6'].astype(str)
        df_ecart_stock_last['MGB_6'] = df_ecart_stock_last['MGB_6'].astype(str)

        df_ecart_stock_last['Deja_Present'] = df_ecart_stock_last['MGB_6'].isin(df_ecart_stock_prev['MGB_6'])
        
        print("Apercu df_ecart_stock_prev (head):")
        print(df_ecart_stock_prev.head(5))
        print("Colonnes df_ecart_stock_prev apres preprocess :", list(df_ecart_stock_prev.columns))
        print("Apercu df_ecart_stock_last (head):")
        print(df_ecart_stock_last.head(5))
        print("Colonnes df_ecart_stock_last apres preprocess :", list(df_ecart_stock_last.columns))


        # --- INVENTAIRE ---
        print("--- INVENTAIRE ---")
        sys.stdout.reconfigure(encoding='utf-8')

        if not df_inventaire.empty:

            first_col = df_inventaire.columns[0]

            # Vérifie si la première colonne contient des virgules → on découpe
            if df_inventaire[first_col].astype(str).str.contains(",").any():

                # Découpage en colonnes selon les virgules
                df_split = df_inventaire[first_col].astype(str).str.split(",", expand=True)

                # Ne garder que les 7 premières colonnes
                df_split = df_split.iloc[:, :7]

                # Renommer les colonnes
                df_split.columns = [
                    "MGB", "SubSys", "Description",
                    "Initial Quantity", "Final Quantity", "Difference", "Difference (%)"
                ]

                # Remplace df_inventaire par ce DataFrame propre
                df_inventaire = df_split.copy()

            # Renommer pour cohérence interne
            df_inventaire = df_inventaire.rename(columns={
                "SubSys": "Ref_Metro",
                "Initial Quantity": "Initial_Quantity",
                "Final Quantity": "Inventaire_Final_Quantity",
                "Difference (%)": "Difference_%"
            })

            # Conversion en numérique
            if "Inventaire_Final_Quantity" in df_inventaire.columns:
                df_inventaire["Inventaire_Final_Quantity"] = pd.to_numeric(
                    df_inventaire["Inventaire_Final_Quantity"], errors="coerce"
                )

        else:
            print("Aucun fichier inventaire trouvé ou vide.")

        if 'MGB' in df_inventaire.columns:
            df_inventaire['MGB'] = df_inventaire['MGB'].astype(str)
            df_inventaire['MGB_6'] = df_inventaire['MGB'].str[:-6]

        remplacement = {"Å“": "œ", "Ã‚": "â", "Ã´": "ô", "Ã¨": "ë", "Ã¢": "â", "Ã§": "ç",
                        "Ãª": "ê", "Ã®": "î", "Ã©": "é", "Â°": "°", "Ã ": "à ", "ÃŽ": "î", "Ã": "û", "¤": "", "«": "", "»": "", "Â": ""}
        if 'Description' in df_inventaire.columns:
            for ancien, nouveau in remplacement.items():
                df_inventaire["Description"] = df_inventaire["Description"].str.replace(ancien, nouveau, regex=False)
        
        print("Apercu df_inventaire (head):")
        print(df_inventaire.head(5))
        print("Colonnes apres nettoyage :", list(df_inventaire.columns))

        # --- MVT STOCK ---
        print("--- MVT STOCK ---")
        df_mvt_stock = df_mvt_stock.drop(columns=[
            'day_id','ste_nr','SGA','SSGA','colis_non_homogene','art_cont_gross','art_cont_gross_unit',
            'art_weight_gross_cust','type_mvt','qty_bb','pallet_homogene_count','unites_mvt_ccaf_pc','unites_mvt_ccvm_pc'
            ], errors='ignore')

        df_mvt_stock[["Date", "Heure"]] = df_mvt_stock["stk_mvt_datetime"].str.split(" ", expand=True)
        df_mvt_stock = df_mvt_stock.drop(columns=['stk_mvt_datetime'])
        # date_ref doit être au format 'YYYY-MM-DD' ou datetime
        
        print("Dates Mvt Stock :")
        print(f"date_ref : {df_mvt_stock['Date'].iloc[0]}, type : {type(df_mvt_stock['Date'].iloc[0])}")
        df_mvt_stock["Date"] = pd.to_datetime(df_mvt_stock["Date"], format="%Y-%m-%d", errors="coerce")
        print(f"date_ref : {df_mvt_stock['Date'].iloc[0]}, type : {type(df_mvt_stock['Date'].iloc[0])}")
        df_mvt_stock = df_mvt_stock[df_mvt_stock["Date"].notna() & (df_mvt_stock["Date"] >= date_ref)]
        
        df_mvt_stock["stk_chg_desc_details"] = df_mvt_stock["stk_chg_desc_details"].fillna("")
        df_mvt_stock["Code_Mouvement"] = df_mvt_stock["stk_chg_desc_details"].str.extract(r":(\d+)")
        df_mvt_stock["Intituler_Mouvement"] = df_mvt_stock["stk_chg_desc_details"].str.extract(r"::([^:]+)$")
        df_mvt_stock = df_mvt_stock.drop(columns=['stk_chg_desc_details'])

        # Créer Code_Agent uniquement si des valeurs valides existent
        if "emp_email" in df_mvt_stock.columns and df_mvt_stock["emp_email"].notna().any():
            df_mvt_stock["Code_Agent"] = df_mvt_stock["emp_email"].fillna("").str.split(".", expand=True).iloc[:, 0]
        else:
            df_mvt_stock["Code_Agent"] = pd.Series([""] * len(df_mvt_stock))
        df_mvt_stock = df_mvt_stock.drop(columns=['emp_email'])

        # Remplacer les NaN par chaîne vide
        location_filled = df_mvt_stock["location_nr"].fillna("")

        # Split en 2 colonnes, n=1
        split_cols = location_filled.str.split("-", n=1, expand=True)

        # Assigner les colonnes en vérifiant si elles existent
        df_mvt_stock["prefix_emplacement"] = split_cols[0] if 0 in split_cols.columns else ""
        df_mvt_stock["Emplacement"] = split_cols[1] if 1 in split_cols.columns else ""

        df_mvt_stock = df_mvt_stock.drop(columns=['location_nr'])

        df_mvt_stock = df_mvt_stock.rename(columns={
            "art_name": "Désignation",
            "Subsys": "Ref_Metro",
            "art_weight_ind": "Au_Kg",
            "sscc": "SSCC",
            "qty": "Qty_Mouvement",
            "stk_mvt_type": "Type_Mouvement",
            "stk_chg_desc": "Info_Mouvement",
            "cellule": "Cellule",
            'stk_sync_mms_ind':'Synchro_MMS',
            'MGB' : 'MGB_6',
            "art_mgb12": "MGB"
        })

        # Liste des colonnes dans l'ordre souhaité et suppression des doublons
        nouvel_ordre = ["Date", "Heure", "Code_Agent","MGB","MGB_6", "Désignation", "Ref_Metro",
                        "Au_Kg", "SSCC", "Type_Mouvement","Code_Mouvement","Intituler_Mouvement", "Info_Mouvement",
                        'Synchro_MMS',"Cellule", 'prefix_emplacement',"Emplacement","Qty_Mouvement"]
        nouvel_ordre = list(dict.fromkeys(nouvel_ordre))  # supprime les doublons
        df_mvt_stock = df_mvt_stock[nouvel_ordre]

        df_mvt_stock['Synchro_MMS'] = df_mvt_stock['Synchro_MMS'].fillna(0).astype(int).map({1:'Oui', 0:'Non'})
        df_mvt_stock['Type_Mouvement'] = df_mvt_stock['Type_Mouvement'].replace({
            'DELETE_STOCK': 'Suppression_Stock',
            'EDIT_QUANTITY': 'Modification_Stock',
            'CREATE_STOCK_FROM_MOBILE': 'Creation_Stock',
            'GR_SPLIT': 'Separation_Palette',
            'GR_MANUAL': 'Reception_Manuel'
        })
        df_mvt_stock['Info_Mouvement'] = df_mvt_stock['Info_Mouvement'].str.upper()
        df_mvt_stock['MGB_6'] = df_mvt_stock['MGB_6'].astype(str)

        print("Colonnes apres nettoyage :", list(df_mvt_stock.columns))
        
        # --- RECEPTION ---
        print("--- RECEPTION ---")
        df_reception = df_reception.drop(columns=['ste_nr','SSGA','job_type_fr','job_id','job_begin_datetime','job_started_datetime',
            'var_nr','bdl_nr','SGA','art_weight_gross','art_weight_gross_cust','art_weight_net',
            'art_weight_unit','art_weight_ind.1','art_volume_net','art_volume_unit',
            'job_line_duration_minutes','job_qty_pc','job_qty_gross_avg','gr_qty','pallet_homogene_count',
            'colis_non_homogene','unites_recues_ccaf_pc','unites_recues_ccvm_pc'], errors='ignore')

        df_reception[["Date", "Heure"]] = df_reception["job_done_datetime"].str.split(",", expand=True)
        df_reception = df_reception.drop(columns=['job_done_datetime'])
        # date_ref doit être au format 'YYYY-MM-DD' ou datetime)
        print("Dates Reception :")
        print(f"date_ref : {df_reception['Date'].iloc[0]}, type : {type(df_reception['Date'].iloc[0])}")
        # définir la locale française
        MOIS_FR = {
            "janv": "01",
            "fevr": "02",
            "fev": "02",
            "mars": "03",
            "avr": "04",
            "mai": "05",
            "juin": "06",
            "juil": "07",
            "aout": "08",
            "sept": "09",
            "oct": "10",
            "nov": "11",
            "dec": "12",
        }

        def parse_date_fr(val):
            if not isinstance(val, str):
                return pd.NaT

            # supprime accents (avr → avr, fév → fev)
            s = unicodedata.normalize("NFKD", val).encode("ascii", "ignore").decode()
            s = s.lower().strip()

            # supprime les points
            s = s.replace(".", "")

            # remplace mois français par chiffre
            for mois, num in MOIS_FR.items():
                s = re.sub(rf"\b{mois}\b", num, s)

            # ex: "30 04 2025"
            try:
                return pd.to_datetime(s, format="%d %m %Y")
            except Exception:
                return pd.NaT

        df_reception["Date"] = df_reception["Date"].apply(parse_date_fr)
        # Affichage formaté sans changer le type
        print(f"date_ref : {df_reception['Date'].iloc[0]}, type : {type(df_reception['Date'].iloc[0])}")
        df_reception = df_reception[df_reception["Date"].notna() & (df_reception["Date"] >= date_ref)]     

        # Partition de art_name en MGB et Désignation
        if "art_name" in df_reception.columns and df_reception["art_name"].notna().any():
            df_reception[["MGB","Désignation"]] = df_reception["art_name"].fillna("").str.split("-", n=1, expand=True)
        else:
            df_reception[["MGB","Désignation"]] = pd.DataFrame([["",""]] * len(df_reception), columns=["MGB","Désignation"])

        df_reception = df_reception.drop(columns=['art_name'])
        
        # Créer Code_Agent uniquement si des valeurs valides existent
        if "emp_upn" in df_reception.columns and df_reception["emp_upn"].notna().any():
            df_reception["Code_Agent"] = df_reception["emp_upn"].fillna("").str.split(".", expand=True).iloc[:, 0]
        else:
            df_reception["Code_Agent"] = pd.Series([""] * len(df_reception))
        df_reception = df_reception.drop(columns=['emp_upn'])

        df_reception = df_reception.rename(columns={
            "art_subsys": "Ref_Metro",
            "CCVM": "Conditionnement_Vente",
            "CCAF": "Conditionnement_Fournisseur",
            "gr_date": "Date_Camion",
            "delivery_id": "N°_Camion",
            "job_qty": "Qty_Reception",
            "job_qty_ccaf": "Qty_Colis_Reception",
            "cellule": "Cellule",
            "art_weight_ind": "Au_Kg",
            "sscc": "SSCC",
            "type_recep": "Type_Recep"
        })

        df_reception['MGB'] = df_reception['MGB'].astype(str)

        # S'assurer que MGB est bien une chaîne
        df_reception["MGB"] = df_reception["MGB"].astype(str).str.strip()

        def extraire_mgb6(mgb):
            if len(mgb) == 11:
                return mgb[:-6]   # enlève les 6 derniers
            elif len(mgb) == 12:
                return mgb[:6]    # garde les 6 premiers
            else:
                return mgb  # garde tel quel si longueur inattendue

        df_reception["MGB_6"] = df_reception["MGB"].apply(extraire_mgb6)

        nouvel_ordre = [
            "Date", "Heure", "Code_Agent", "MGB","MGB_6", "Désignation","SV", "SA", "GA",
            "Ref_Metro", "Conditionnement_Vente", "Conditionnement_Fournisseur","Au_Kg", "SSCC",
            "Date_Camion", "N°_Camion", "Cellule",  "Type_Recep","Qty_Reception", "Qty_Colis_Reception"
        ]
        df_reception = df_reception[nouvel_ordre]

        print("Colonnes apres nettoyage :", list(df_reception.columns))

        # --- SORTIES ---
        print("--- SORTIES ---")
        df_sorties = df_sorties.drop(columns=[
            'sto_nr','ord_datetime','cus_sto_nr','cus_nr','ord_status_datetime','inv_date','art_cont_gross','art_cont_gross_unit',
            'ord_line_code','ord_qty_follow','art_pick_tool','art_pick_area','art_pick_id','type_UO','unites_pickees','nb_UO',
            'cre_date','upd_date','art_weight_gross_cust'
        ], errors='ignore')

        df_sorties[["Date", "Heure"]] = df_sorties["art_pick_datetime"].str.split(" ", expand=True)
        df_sorties = df_sorties.drop(columns=['art_pick_datetime'])
        # date_ref doit être au format 'YYYY-MM-DD' ou datetime
        print(f"date_ref : {df_sorties['Date'].iloc[0]}, type : {type(df_sorties['Date'].iloc[0])}")
        df_sorties["Date"] = pd.to_datetime(df_sorties["Date"], format="%Y-%m-%d", errors="coerce")
        print(f"date_ref : {df_sorties['Date'].iloc[0]}, type : {type(df_sorties['Date'].iloc[0])}")
        # Supprimer les lignes antérieures à date_ref
        df_sorties = df_sorties[df_sorties["Date"] >= date_ref]

        df_sorties["Emplacement"] = df_sorties["art_pick_pos"].str.split("-", n=1, expand=True)[1]
        df_sorties = df_sorties.drop(columns=["art_pick_pos"])
        df_sorties["Code_Agent"] = df_sorties["art_picker_upn"].str.split(".", expand=True)[0]

        # Créer Code_Agent uniquement si des valeurs valides existent
        if "art_picker_upn" in df_sorties.columns and df_sorties["art_picker_upn"].notna().any():
            df_sorties["Code_Agent"] = df_sorties["art_picker_upn"].fillna("").str.split(".", expand=True).iloc[:, 0]
        else:
            df_sorties["Code_Agent"] = pd.Series([""] * len(df_sorties))

        df_sorties = df_sorties.drop(columns=['art_picker_upn'])

        df_sorties['Qty/Article/Poids'] = pd.to_numeric(df_sorties['art_pick_qty'], errors='coerce')

        print("Colonnes avant nettoyage :", list(df_sorties.columns))
        df_sorties = df_sorties.rename(columns={
            'dlv_date': "Date_de_livraison",
            'ord_qty' : "Qty_Commandé",
            "ord_picked_qty" : "Qty_Total_Préparé",
            "art_subsys" : "Ref_Metro",
            "art_name" : "Désignation",
            "art_weight_ind": "Au_Kg",
            "ord_nr": "N°_Commande",
            "cellule" : "Cellule"
        })

        df_sorties['MGB'] = df_sorties['art_mgb12'].astype(str)
        df_sorties['MGB_6'] = df_sorties['MGB'].str[:-6]

        nouvel_ordre_s = [
            "Date", "Heure", "Date_de_livraison", "Code_Agent", "MGB","MGB_6", "Désignation","SV","N°_Commande",
            "Ref_Metro","Au_Kg","Qty_Commandé","Qty_Total_Préparé","Qty/Article/Poids", "Cellule",  "Emplacement"
        ]
        df_sorties = df_sorties[nouvel_ordre_s]

        print("Colonnes apres nettoyage :", list(df_sorties.columns))
    
        # --- ARTICLES €---
        print("--- ARTICLES €---")
        # --- Nettoyage robuste du fichier Article_€.xlsx ---

        # 1) Si le DF est vide on sort
        if df_article_euros is None or df_article_euros.empty:
            print("df_article_euros vide ou non trouvé.")
        else:
            # Toujours travailler en str pour éviter surprises
            df_article_euros = df_article_euros.astype(str)

            # Nettoyage basique des noms de colonnes lus par pandas
            cols_raw = [str(c).strip() for c in df_article_euros.columns]
            cols_joined = " | ".join(cols_raw).lower()
            print("Colonnes lues initialement :", cols_raw)

            # 2) Détecter si pandas a pris la première ligne comme données (cas où cols_raw sont des valeurs)
            # heuristique : si la première colonne est numérique ou ressemble à une référence (ex: '68513')
            first_col_name = cols_raw[0]
            looks_like_data_header = False
            try:
                # si le nom de colonne est un entier numérique → pandas n'a pas lu l'en-tête
                float(first_col_name.replace(',', '.'))
                looks_like_data_header = True
            except Exception:
                # non numérique → vérifier si contient des mots attendus (ref/article/prix)
                if not re.search(r'(ref|article|unitaire|€|prix|sa)', cols_joined):
                    # si aucun des mots attendus n'apparaît dans les noms de colonnes, on considère que l'entête peut manquer
                    looks_like_data_header = True

            # 3) Si l'entête semble manquer : prendre la première ligne comme header
            if looks_like_data_header:
                print("Info: La premiere ligne semble contenir l'entête réelle → on l'utilise comme header.")
                # prendre la 1ère ligne comme header, puis supprimer cette ligne des données
                new_header = df_article_euros.iloc[0].astype(str).str.strip().tolist()
                df_article_euros = df_article_euros[1:].reset_index(drop=True)
                df_article_euros.columns = new_header

            # 4) Nettoyer les noms de colonnes (trim, BOM, normalisation)
            clean_cols = []
            for c in df_article_euros.columns:
                c = str(c).strip()
                c = c.replace('\ufeff', '')        # BOM
                c = c.replace('\xa0', ' ')         # non-break space -> normal space
                clean_cols.append(c)
            df_article_euros.columns = clean_cols

            print("Colonnes apres nettoyage :", list(df_article_euros.columns))

            # 5) Renommer la colonne prix (recherche fuzz : '€', 'unitaire', 'prix')
            euro_col = None
            for c in df_article_euros.columns:
                cl = str(c).lower()
                if '€' in c or 'unitaire' in cl or 'prix' in cl:
                    euro_col = c
                    break
            if euro_col:
                df_article_euros = df_article_euros.rename(columns={euro_col: "Prix_Unitaire"})
                print(f"-> Colonne prix detectee et renommee : '{euro_col}' -> 'Prix_Unitaire'")
            else:
                print("Colonne prix introuvable (ni '€', ni 'unitaire', ni 'prix').")

            # 6) Renommer la colonne référence si nécessaire (ex: 'ref', 'Ref', 'Réf', 'MGB', ...)
            ref_col = None
            for c in df_article_euros.columns:
                cl = str(c).lower()
                if cl in ('ref', 'réf', 'reference', 'reference_id', 'mgb', 'mgb_6'):
                    ref_col = c
                    break
            if ref_col and ref_col != 'ref':
                df_article_euros = df_article_euros.rename(columns={ref_col: 'ref'})
                print(f"-> Colonne reference renommee : '{ref_col}' -> 'ref'")
            elif not ref_col:
                # tenter de détecter la colonne référence par type (entier)
                for c in df_article_euros.columns:
                    sample = df_article_euros[c].dropna().astype(str).head(5).tolist()
                    if all(re.fullmatch(r'\d+', s) for s in sample):
                        df_article_euros = df_article_euros.rename(columns={c: 'ref'})
                        ref_col = 'ref'
                        print(f"-> Colonne reference detectee automatiquement : '{c}' -> 'ref'")
                        break
                if not ref_col:
                    print("Colonne reference introuvable automatiquement. Verifie le fichier Article_€.xlsx")

            # 7) Convertir Prix_Unitaire en float (retirer '€', remplacer virgule par point)
            if 'Prix_Unitaire' in df_article_euros.columns:
                s = df_article_euros['Prix_Unitaire'].astype(str)
                s = s.str.replace('€', '', regex=False)
                s = s.str.replace('\u00A0', '', regex=False)   # NBSP
                s = s.str.replace(' ', '', regex=False)
                s = s.str.replace(',', '.', regex=False)
                df_article_euros['Prix_Unitaire'] = pd.to_numeric(s, errors='coerce')
                print("-> Conversion 'Prix_Unitaire' en numerique effectuee.")
            else:
                print("'Prix_Unitaire' absent, conversion ignoree.")

        print("Apercu df_article_euros (head):")
        print(df_article_euros.head(5))

        #------------------------------------------------        
        #------- ETAT STOCK (Excel ou CSV “cassé”) ------
        #------------------------------------------------
        print("--- ETAT STOCK ---")
        print("Colonnes initiales df_etat_stock :", df_etat_stock.columns.tolist())

        if df_etat_stock.shape[1] == 1:  # Toutes les données sont dans une seule colonne
            # Séparer les colonnes par virgule
            df_etat_stock = df_etat_stock.iloc[:, 0].str.split(',', expand=True)
            df_etat_stock.columns = ['MGB', 'Description', 'Ref Metro'] + [f'col{i}' for i in range(4, df_etat_stock.shape[1]+1)]
            print("Colonnes apres split CSV mal forme :", df_etat_stock.columns.tolist())

        elif 'Ref Metro' not in df_etat_stock.columns and 'SubSys' in df_etat_stock.columns:
            df_etat_stock = df_etat_stock.rename(columns={'SubSys': 'Ref Metro'})
            print("Colonnes apres renommage si necessaire :", df_etat_stock.columns.tolist())
        
        # S'assurer que MGB est string
        df_etat_stock['MGB'] = df_etat_stock['MGB'].astype(str)

        # Vérifier que les colonnes essentielles existent
        essential_cols = ['MGB', 'Description', 'Ref Metro', 'Position', 'Quantity', 'Max Delivery Date']
        missing_cols = [c for c in essential_cols if c not in df_etat_stock.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes dans l'état stock : {missing_cols}")

        df_etat_stock = df_etat_stock[essential_cols].copy()
        print("Colonnes apres selection essentielles :", df_etat_stock.columns.tolist())

        # Nettoyage des caractères spéciaux dans Description
        remplacement = {"ÃŽ": "î", "Å“": "œ", "Ã‚": "â", "Ã´": "ô", "Ã¨": "ë", "Ã¢": "â", "Ã§": "ç",
                        "Ãª": "ê", "Ã®": "î", "Ã©": "é", "Â°": "°", " Ã ": " à ", "Ã": "û", "¤": "", "«": "", "»": "", "Â": ""}
        df_etat_stock["Description"] = df_etat_stock["Description"].replace(remplacement, regex=True)

        # Ajouter la colonne EAN depuis le fichier Excel
        df_excel_ean['MGB'] = df_excel_ean['MGB'].astype(str)

        # Merge outer pour conserver tous les MGB
        df_merged = df_etat_stock.merge(
            df_excel_ean[['MGB', 'Description', 'Ref Metro', 'CODE EAN']],
            on='MGB',
            how='outer',
            suffixes=('_stock', '_ean')
        )

        # Pour Description et Ref Metro, garder celle de df_etat_stock si présente, sinon prendre df_excel_ean
        for col in ['Description', 'Ref Metro']:
            df_merged[col] = df_merged[f'{col}_stock'].combine_first(df_merged[f'{col}_ean'])
            df_merged.drop([f'{col}_stock', f'{col}_ean'], axis=1, inplace=True)

        # Renommer CODE EAN → EAN
        df_merged.rename(columns={'CODE EAN': 'EAN'}, inplace=True)

        # Convertir les EAN float en str sans décimales
        df_merged['EAN'] = df_merged['EAN'].apply(
            lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, np.floating)) else (str(x) if pd.notna(x) else '')
        )
        # S'assurer que Ref Metro est string et supprimer .0 si présent
        df_merged['Ref Metro'] = df_merged['Ref Metro'].apply(
            lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, np.floating)) else (str(x) if pd.notna(x) else '')
        )
    
        # ordre des colonnes
        df_merged.rename(columns={'Description': 'Désignation'}, inplace=True)
        df_merged.rename(columns={'Max Delivery Date': 'DLC'}, inplace=True)
        df_merged.rename(columns={'Quantity': 'Qty_Stock'}, inplace=True)

        #ajout colonne de Base_Article
        df_merged['MGB'] = df_merged['MGB'].astype(str).str.strip()
        Base_Article['MGB'] = (Base_Article['MGB 12'].apply(lambda x: f"{int(x):d}" if pd.notna(x) else None)).astype(str).str.strip()
        print("df_merged MGB (exemples):", df_merged['MGB'].dropna().unique()[:10])
        print("Base_Article MGB (exemples):", Base_Article['MGB 12'].dropna().unique()[:10])
        # Merge pour récupérer SA, GA, Flux
        df_merged = df_merged.merge(
            Base_Article[['MGB', 'SA', 'GA', 'Flux ']],
            on='MGB',
            how='left'
        )
        # Merge pour recuperer les prix
        df_merged = df_merged.merge(
            df_article_euros[['ref', 'Prix_Unitaire']],
            left_on='Ref Metro',
            right_on='ref',
            how='left'
        )
        df_merged.drop(columns=['ref'], inplace=True)

        # Renommer Flux → Cellule et Prix_Unitaire → Prix et remplacer 'Alcool' par 'Ambiant'
        df_merged.rename(columns={'Flux ': 'Cellule'}, inplace=True)
        df_merged.rename(columns={'Prix_Unitaire': 'Prix'}, inplace=True)
        df_merged['Cellule'] = df_merged['Cellule'].replace('Alcool', 'Ambiant')

        # Résultat final
        df_etat_stock = df_merged

        print("Apercu df_etat_stock (head):")
        print(df_etat_stock.head(5))

        # ==================================================
        # AJOUT PRIX + AU_KG + VALEUR DIFFÉRENCE
        # ==================================================
        # Ajouter prix et valeur totale
        print("--- AJOUT PRIX + VALEUR DIFFÉRENCE ---")
        def add_price_and_value(df_target, df_price, target_key, price_key, quantity_col, value_col='Valeur_du_Stock', price_col='Prix_Unitaire', display_in_streamlit=True):
            if df_target.empty or df_price.empty:
                df_target[value_col] = 0
                return df_target

            df_target[target_key] = df_target[target_key].astype(str)
            df_price[price_key] = df_price[price_key].astype(str)

            df_target = df_target.merge(
                df_price[[price_key, price_col]],
                left_on=target_key,
                right_on=price_key,
                how='left'
            )
            df_target = df_target.drop(columns=[price_key])
            
            # Assurer que les colonnes sont numériques
            print("Valeurs uniques dans", quantity_col, ":", df_target[quantity_col].unique()[:10])
            print("Valeurs uniques dans", price_col, ":", df_target[price_col].unique()[:10])

            df_target[quantity_col] = pd.to_numeric(df_target[quantity_col], errors='coerce').fillna(0)
            df_target[price_col] = pd.to_numeric(df_target[price_col], errors='coerce').fillna(0).round(2)

            df_target[value_col] = df_target[quantity_col] * df_target[price_col]

            if display_in_streamlit:
                st.dataframe(df_target.style.format({price_col: "{:.2f}", value_col: "{:.2f}"}))

            return df_target
        
        # --- Valeur Difference ---
        df_inventaire = add_price_and_value(df_inventaire, df_article_euros, 'Ref_Metro', 'ref', 'Inventaire_Final_Quantity', display_in_streamlit=False)
        df_reception = add_price_and_value(df_reception, df_article_euros, 'Ref_Metro', 'ref', 'Qty_Reception', display_in_streamlit=False)
        df_sorties = add_price_and_value(df_sorties, df_article_euros, 'Ref_Metro', 'ref', 'Qty/Article/Poids', display_in_streamlit=False)
        df_mvt_stock = add_price_and_value(df_mvt_stock, df_article_euros, 'Ref_Metro', 'ref', 'Qty_Mouvement', display_in_streamlit=False)
        df_etat_stock = add_price_and_value(df_etat_stock, df_article_euros, 'Ref Metro', 'ref', 'Qty_Stock', display_in_streamlit=False)

        def safe_mapping(df):
            for col in ['MGB_6', 'Prix_Unitaire']:
                if col not in df.columns:
                    df[col] = pd.NA
            return df[['MGB_6', 'Prix_Unitaire']].drop_duplicates()

        mapping_inventaire = safe_mapping(df_inventaire)
        mapping_reception  = safe_mapping(df_reception)
        mapping_mvt        = safe_mapping(df_mvt_stock)

        dfs = [mapping_inventaire, mapping_reception, mapping_mvt]
        dfs = [df for df in dfs if not df.empty]

        mapping_global = (
            pd.concat(dfs)
            .drop_duplicates(subset="MGB_6", keep="first")
        )

        # Fusionner Prix_Unitaire dans df_ecart_stock_last
        df_ecart_stock_last = df_ecart_stock_last.merge(mapping_global, on='MGB_6', how='left')

        # Forcer arrondi à 2 chiffres pour Prix_Unitaire
        df_ecart_stock_last['Prix_Unitaire'] = (
            pd.to_numeric(df_ecart_stock_last['Prix_Unitaire'], errors='coerce')
            .fillna(0)
            .round(2)
        )

        # Calcul de la Valeur_Difference
        df_ecart_stock_last['Valeur_Difference'] = (
            df_ecart_stock_last['Prix_Unitaire'] * df_ecart_stock_last['Difference_MMS-WMS']
        ).round(2)


        # --- Valeur AU_KG ---
        print("--- AJOUT AU_KG ---")

        # Créer un mapping global
        mapping_aukg_reception = df_reception[['MGB_6', 'Au_Kg']].drop_duplicates()
        mapping_aukg_mvt       = df_mvt_stock[['MGB_6', 'Au_Kg']].drop_duplicates()
        mapping_aukg_sorties   = df_sorties[['MGB_6', 'Au_Kg']].drop_duplicates()

        mapping_aukg_global = pd.concat([
            mapping_aukg_reception,
            mapping_aukg_mvt,
            mapping_aukg_sorties
        ]).drop_duplicates(subset='MGB_6', keep='first')

        # Merge sans convertir en bool
        df_ecart_stock_last = df_ecart_stock_last.merge(mapping_aukg_global, on='MGB_6', how='left')

        # --- Réordonner colonnes finales ---
        nouvel_ordre = [
            "MGB_6", "Désignation", "MMS_Stock : Metro", "WMS_Stock : IDL",
            "Difference_MMS-WMS", 'Au_Kg', "Deja_Present", 'Prix_Unitaire',
            'Valeur_Difference', "Date_Dernier_Commentaire", "Commentaire"
        ]

        df_ecart_stock_last = df_ecart_stock_last[[col for col in nouvel_ordre if col in df_ecart_stock_last.columns]] 
        # Vérifier le type
        print(df_ecart_stock_last['Au_Kg'].dtype)
        print(df_ecart_stock_last['Au_Kg'].unique())    
        # Normaliser les valeurs en booléens
        df_ecart_stock_last['Au_Kg'] = df_ecart_stock_last['Au_Kg'].apply(
            lambda x: True if x in [True, 'true', 1] else (False if x in [False, 'false', 0] else pd.NA)
        ).astype('boolean')  # dtype nullable bool
        print(df_ecart_stock_last['Au_Kg'].dtype)
        # ============================================================
        # Préserver les anciens commentaires avant d'écraser le parquet
        # ============================================================
        print("--- RESTAURATION ANCIENS COMMENTAIRES ET CHOIX TRAITEMENT ---")
        parquet_path = Path(r"\\spwfs-metbre\Partage\11_Public\Data_app\Cache\ecart_stock_last.parquet")

        if parquet_path.exists():
            try:
                df_old = pd.read_parquet(parquet_path)
                print("df_ecart_stock_last avant merge:", df_ecart_stock_last.head(3))
                print("df_old:", df_old.head(3))
                print("Colonnes df_ecart_stock_last:", df_ecart_stock_last.columns.tolist())
                print("Colonnes df_old:", df_old.columns.tolist())
                print(df_ecart_stock_last.dtypes)
                print(df_old.dtypes)

                expected = {"MGB_6", "Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"}
                if expected.issubset(set(df_old.columns)):
                    print("Fusion des anciens commentaires et choix traitement avec les nouvelles données...")

                    # --- s'assurer qu'il n'y a pas de doublons côté ancien fichier (garder le dernier) ---
                    if df_old["MGB_6"].duplicated().any():
                        print(f"Attention : {df_old['MGB_6'].duplicated().sum()} doublons trouvés dans df_old -> on garde la dernière occurrence.")
                        df_old = df_old.sort_values("Date_Dernier_Commentaire", ascending=True).drop_duplicates(subset="MGB_6", keep="last")

                    # --- fusionner (suffixe _old) ---
                    df_ecart_stock_last = df_ecart_stock_last.merge(
                        df_old[["MGB_6", "Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"]],
                        on="MGB_6",
                        how="left",
                        suffixes=("", "_old")
                    )

                    # --- normaliser les noms de colonnes (strip) pour éviter espaces invisibles ---
                    df_ecart_stock_last.columns = [c.strip() if isinstance(c, str) else c for c in df_ecart_stock_last.columns]

                    # --- pour chaque colonne cible, remplacer les valeurs NULL ou "" par la valeur _old ---
                    for col in ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"]:
                        old_col = f"{col}_old"
                        if old_col in df_ecart_stock_last.columns:
                            # masque : NaN OU chaîne vide (après strip)
                            mask_missing = df_ecart_stock_last[col].isnull() | (df_ecart_stock_last[col].astype(str).str.strip() == "")
                            n_to_fill = mask_missing.sum()
                            if n_to_fill:
                                print(f"Remplissage {n_to_fill} valeurs manquantes dans '{col}' depuis '{old_col}'.")
                                df_ecart_stock_last.loc[mask_missing, col] = df_ecart_stock_last.loc[mask_missing, old_col]
                        else:
                            print(f"Colonne {old_col} non trouvée après merge (rien à fusionner pour {col}).")

                    # --- supprimer toutes les colonnes finissant par _old (robuste) ---
                    old_cols = [c for c in df_ecart_stock_last.columns if isinstance(c, str) and c.endswith("_old")]
                    if old_cols:
                        print(f"Suppression des colonnes temporaires : {old_cols}")
                        df_ecart_stock_last.drop(columns=old_cols, inplace=True, errors="ignore")
                    else:
                        print("Aucune colonne *_old à supprimer.")

                else:
                    print("Le parquet existant ne contient pas toutes les colonnes attendues :", expected & set(df_old.columns))

            except Exception as e:
                print(f"Impossible de restaurer les anciens commentaires ou choix traitement : {e}")
        else:
            print("Aucun ancien parquet trouvé sur OneDrive, création initiale du fichier.")

        # --- Supprimer les colonnes dupliquées après preprocess ---
        print("--- SUPPRESSION COLONNES DUPLIQUÉES APRÈS PREPROCESS ---")
        def remove_duplicate_columns(df):
            """
            Supprime les colonnes dupliquées dans un DataFrame en gardant la première occurrence.
            """
            if df is None or df.empty:
                return df
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        
        df_mvt_stock = remove_duplicate_columns(df_mvt_stock)
        df_reception = remove_duplicate_columns(df_reception)
        df_sorties = remove_duplicate_columns(df_sorties)
        df_inventaire = remove_duplicate_columns(df_inventaire)
        df_ecart_stock_last = remove_duplicate_columns(df_ecart_stock_last)
        df_ecart_stock_prev = remove_duplicate_columns(df_ecart_stock_prev)
        df_article_euros = remove_duplicate_columns(df_article_euros)

        # --- Supprimer les lignes dupliquées après preprocess ---
        print("--- SUPPRESSION LIGNES DUPLIQUÉES APRÈS PREPROCESS ---")
        df_reception = df_reception.drop_duplicates().reset_index(drop=True)
        df_sorties = df_sorties.drop_duplicates().reset_index(drop=True)    
        df_mvt_stock = df_mvt_stock.drop_duplicates().reset_index(drop=True)
        
        print("\n=== SYNTHÈSE APRÈS PREPROCESS ===")
        print(f"Mvt_Stock : {len(df_mvt_stock)} lignes")    
        print(f"Réception : {len(df_reception)} lignes")
        print(f"Sorties   : {len(df_sorties)} lignes")
        print(f"Ecart_Stock : {len(df_ecart_stock_last)} lignes")
        print(f"Ecart_Stock : {len(df_ecart_stock_prev)} lignes")
        print(f"Article_euros : {len(df_article_euros)} lignes")    
        print(f"Inventaire : {len(df_inventaire)} lignes")
        
        return df_mvt_stock, df_reception, df_sorties, df_inventaire, df_ecart_stock_prev, df_ecart_stock_last, df_article_euros, df_etat_stock, df_excel_ean, date_ref, Base_Article