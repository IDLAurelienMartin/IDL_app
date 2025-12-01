# scripts/preprocess_stock.py
import os
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime
import re
from openpyxl import load_workbook
import streamlit as st
import urllib.request
import io
import requests
import shutil
from io import BytesIO
import numpy as np


# ============================================================
# === CONFIG GITHUB
# ============================================================
GITHUB_OWNER = "IDLAurelienMartin"
GITHUB_REPO = "Data_IDL"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/"


# ============================================================
# === UTILITAIRES GITHUB
# ============================================================

def github_list_folder(folder_path: str):
    """
    Liste le contenu d’un dossier GitHub via l’API.
    Retourne une liste de dictionnaires :
    [{'name':..., 'path':..., 'type': 'file'/'dir', 'download_url': ...}, ...]
    """
    url = API_BASE + folder_path
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Dossier introuvable sur GitHub : {url}")
        return []
    return r.json()


def github_list_excel_files_recursive(folder_path: str):
    """
    Liste tous les fichiers .xlsx dans un dossier + sous-dossiers GitHub.
    """
    results = []
    stack = [folder_path]

    while stack:
        current = stack.pop()
        items = github_list_folder(current)

        for it in items:
            if it["type"] == "dir":
                stack.append(it["path"])
            elif it["type"] == "file" and it["name"].endswith(".xlsx"):
                results.append(it["path"])

    return results


def read_excel_from_github(path: str) -> pd.DataFrame:
    """Télécharge un Excel RAW depuis GitHub."""
    url = RAW_BASE + path
    try:
        r = requests.get(url)
        r.raise_for_status()
        return pd.read_excel(BytesIO(r.content))
    except:
        print(f"Échec lecture : {url}")
        return pd.DataFrame()


def get_excel_creation_date_from_github(path: str) -> datetime:
    """Récupère la date interne d’un Excel depuis GitHub."""
    url = RAW_BASE + path
    r = requests.get(url)
    r.raise_for_status()

    wb = load_workbook(filename=BytesIO(r.content), read_only=True)
    props = wb.properties
    wb.close()

    if props.created:
        return props.created
    raise ValueError("Métadonnée Excel 'created' introuvable.")


# ============================================================
# === CHARGEMENT DES DONNÉES
# ============================================================

def load_data():
    """
    Charge toutes les données depuis GitHub.
    Tous les fichiers sont récupérés dynamiquement via l'API GitHub.
    """

    # ----------------------------------------
    # Inventaire
    # ----------------------------------------
    INVENTORY_PATH = "Inventory_21_09_2025.xlsx"
    try:
        date_ref = get_excel_creation_date_from_github(INVENTORY_PATH)
        print("Date interne inventaire :", date_ref)
    except Exception as e:
        print("Erreur lecture métadonnées inventaire -> fallback now()", e)
        date_ref = datetime.now()

    df_inventaire = read_excel_from_github(INVENTORY_PATH)

    # ----------------------------------------
    # Fonction pour charger tous les fichiers Excel d'un dossier GitHub
    # ----------------------------------------
    def load_folder(folder):
        files = github_list_excel_files_recursive(folder)
        dfs = [read_excel_from_github(f) for f in files]
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    # Chargement des données
    df_mvt_stock = load_folder("Mvt_stock")
    df_reception = load_folder("Historique_Reception")
    df_sorties = load_folder("Historique_des_Sorties")

    # ----------------------------------------
    # ECART STOCK : dernier et avant-dernier fichiers
    # ----------------------------------------

    ecart_files = github_list_excel_files_recursive("Ecart_Stock")

    # Créer une liste tuples (fichier, date_interne)
    files_with_dates = []
    for f in ecart_files:
        try:
            date_creation = get_excel_creation_date_from_github(f)
            files_with_dates.append((f, date_creation))
        except Exception as e:
            print(f"Impossible de lire la date de {f} :", e)

    # Trier par date de création croissante
    files_with_dates.sort(key=lambda x: x[1])

    if len(files_with_dates) < 2:
        raise FileNotFoundError("Pas assez de fichiers d’écart stock avec date interne.")

    # Déterminer les fichiers avant-dernier et dernier
    file_prev = files_with_dates[-2][0]
    file_last = files_with_dates[-1][0]

    # Lecture des fichiers Excel
    df_ecart_stock_prev = read_excel_from_github(file_prev)
    df_ecart_stock_last = read_excel_from_github(file_last)

    # Sauvegarde du nom du dernier fichier pour référence (ex: cache Render)
    render_cache_dir = Path("/opt/render/project/src/render_cache")
    render_cache_dir.mkdir(parents=True, exist_ok=True)
    file_last_txt = render_cache_dir / "file_last.txt"
    file_last_txt.write_text(file_last)  # on écrit le chemin GitHub, pas local

    # ----------------------------------------
    # Article € (fichier unique)
    # ----------------------------------------
    df_article_euros = read_excel_from_github("Article_euros.xlsx")

    df_etat_stock = read_excel_from_github("etat_stock.xlsm")
    df_excel_ean = read_excel_from_github("Detrompeur/Liste detrompeur + EAN.xlsx")
    # ----------------------------------------
    # Synthèse
    # ----------------------------------------
    print("\n=== SYNTHÈSE GITHUB ===")
    print("Mvt Stock :", len(df_mvt_stock))
    print("Réception :", len(df_reception))
    print("Sorties   :", len(df_sorties))
    print("Écart prev:", len(df_ecart_stock_prev))
    print("Écart last:", len(df_ecart_stock_last))
    print("Articles €:", len(df_article_euros))
    print("Inventaire:", len(df_inventaire))

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
        file_last,  # chemin GitHub du dernier fichier
    )

# =========================
# === PREPROCESSING
# =========================
def preprocess_data(df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock, df_etat_stock, df_excel_ean,):  

        # --- ECART STOCK ---
        df_ecart_stock_prev = df_ecart_stock_prev.drop(columns=['Var','Locations','MMS Stock (1 piece)','WMS Stock (1 piece)',
                                                    'Pick qty (1 piece)','Pick qty','Difference (1 piece)'], errors='ignore')
        df_ecart_stock_prev = df_ecart_stock_prev.rename(columns={
            "Article Name": "Désignation",
            "Article number (MGB)": "MGB_6",
            "MMS Stock": "MMS_Stock",
            "WMS Stock": "WMS_Stock",
            "Difference": "Difference_MMS-WMS"
        })
        df_ecart_stock_prev['MGB_6'] = df_ecart_stock_prev['MGB_6'].astype(str)
        for col in ["MMS_Stock","WMS_Stock","Difference_MMS-WMS"]:
            df_ecart_stock_prev[col] = pd.to_numeric(df_ecart_stock_prev[col], errors='coerce')

        df_ecart_stock_last = df_ecart_stock_last.drop(columns=['Var','Locations','MMS Stock (1 piece)','WMS Stock (1 piece)',
                                                    'Pick qty (1 piece)','Pick qty','Difference (1 piece)'], errors='ignore')
        df_ecart_stock_last = df_ecart_stock_last.rename(columns={
            "Article Name": "Désignation",
            "Article number (MGB)": "MGB_6",
            "MMS Stock": "MMS_Stock",
            "WMS Stock": "WMS_Stock",
            "Difference": "Difference_MMS-WMS"
        })
        df_ecart_stock_last['MGB_6'] = df_ecart_stock_last['MGB_6'].astype(str)

        colonnes_a_ajouter = ["Date_Dernier_Commentaire", "Commentaire"]
        for col in colonnes_a_ajouter:
            if col not in df_ecart_stock_last.columns:
                df_ecart_stock_last[col] = None
            else:
                df_ecart_stock_last[col] = df_ecart_stock_last[col].where(df_ecart_stock_last[col].notna(), None)

        for col in ["MMS_Stock","WMS_Stock","Difference_MMS-WMS"]:
            df_ecart_stock_last[col] = pd.to_numeric(df_ecart_stock_last[col], errors='coerce')
        
        df_ecart_stock_prev['MGB_6'] = df_ecart_stock_prev['MGB_6'].astype(str)
        df_ecart_stock_last['MGB_6'] = df_ecart_stock_last['MGB_6'].astype(str)

        df_ecart_stock_last['Deja_Present'] = df_ecart_stock_last['MGB_6'].isin(df_ecart_stock_prev['MGB_6'])

        # --- INVENTAIRE ---
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
                "SubSys": "Ref_MERTO",
                "Initial Quantity": "Initial_Quantity",
                "Final Quantity": "Inventaire_Final_Quantity",
                "Difference (%)": "Difference_%"
            })

            # Conversion en numérique
            if "Inventaire_Final_Quantity" in df_inventaire.columns:
                df_inventaire["Inventaire_Final_Quantity"] = pd.to_numeric(
                    df_inventaire["Inventaire_Final_Quantity"], errors="coerce"
                )

        if 'MGB' in df_inventaire.columns:
            df_inventaire['MGB'] = df_inventaire['MGB'].astype(str)
            df_inventaire['MGB_6'] = df_inventaire['MGB'].str[:-6]

        remplacement = {"Å“": "œ", "Ã‚": "â", "Ã´": "ô", "Ã¨": "ë", "Ã¢": "â", "Ã§": "ç",
                        "Ãª": "ê", "Ã®": "î", "Ã©": "é", "Â°": "°", "Ã": "à", "¤": "", "«": "", "»": ""}
        if 'Description' in df_inventaire.columns:
            for ancien, nouveau in remplacement.items():
                df_inventaire["Description"] = df_inventaire["Description"].str.replace(ancien, nouveau, regex=False)

        # --- MVT STOCK ---
        df_mvt_stock = df_mvt_stock.drop(columns=[
            'day_id','ste_nr','SGA','SSGA','colis_non_homogene','art_cont_gross','art_cont_gross_unit',
            'art_weight_gross_cust','type_mvt','qty_bb','pallet_homogene_count','unites_mvt_ccaf_pc','unites_mvt_ccvm_pc'
            ], errors='ignore')

        df_mvt_stock[["Date", "Heure"]] = df_mvt_stock["stk_mvt_datetime"].str.split(" ", expand=True)
        df_mvt_stock = df_mvt_stock.drop(columns=['stk_mvt_datetime'])
        df_mvt_stock["stk_chg_desc_details"] = df_mvt_stock["stk_chg_desc_details"].fillna("")
        df_mvt_stock["Code_Mouvement"] = df_mvt_stock["stk_chg_desc_details"].str.extract(r":(\d+)")
        df_mvt_stock["Intituler_Mouvement"] = df_mvt_stock["stk_chg_desc_details"].str.extract(r"::([^:]+)$")
        df_mvt_stock = df_mvt_stock.drop(columns=['stk_chg_desc_details'])
        df_mvt_stock["Code_Agent"] = df_mvt_stock["emp_email"].str.split(".", expand=True)[0]
        df_mvt_stock = df_mvt_stock.drop(columns=['emp_email'])
        df_mvt_stock[["prefix_emplacement", "Emplacement"]] = df_mvt_stock["location_nr"].str.split("-", n=1, expand=True)
        df_mvt_stock = df_mvt_stock.drop(columns=['location_nr'])

        df_mvt_stock = df_mvt_stock.rename(columns={
            "art_name": "Désignation",
            "Subsys": "Ref_MERTO",
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
        nouvel_ordre = ["Date", "Heure", "Code_Agent","MGB","MGB_6", "Désignation", "Ref_MERTO",
                        "Au_Kg", "SSCC", "Type_Mouvement","Code_Mouvement","Intituler_Mouvement", "Info_Mouvement",
                        'Synchro_MMS',"Cellule", 'prefix_emplacement',"Emplacement","Qty_Mouvement"]
        nouvel_ordre = list(dict.fromkeys(nouvel_ordre))  # supprime les doublons
        df_mvt_stock = df_mvt_stock[nouvel_ordre]

        df_mvt_stock['Synchro_MMS'] = df_mvt_stock['Synchro_MMS'].replace({1: 'Oui', 0: 'Non'})
        df_mvt_stock['Type_Mouvement'] = df_mvt_stock['Type_Mouvement'].replace({
            'DELETE_STOCK': 'Suppression_Stock',
            'EDIT_QUANTITY': 'Modification_Stock',
            'CREATE_STOCK_FROM_MOBILE': 'Creation_Stock',
            'GR_SPLIT': 'Separation_Palette',
            'GR_MANUAL': 'Reception_Manuel'
        })
        df_mvt_stock['Info_Mouvement'] = df_mvt_stock['Info_Mouvement'].str.upper()
        df_mvt_stock['MGB_6'] = df_mvt_stock['MGB_6'].astype(str)

        # --- RECEPTION ---
        df_reception = df_reception.drop(columns=['ste_nr','SSGA','job_type_fr','job_id','job_begin_datetime','job_started_datetime',
            'var_nr','bdl_nr','SGA','art_weight_gross','art_weight_gross_cust','art_weight_net',
            'art_weight_unit','art_weight_ind.1','art_volume_net','art_volume_unit',
            'job_line_duration_minutes','job_qty_pc','job_qty_gross_avg','gr_qty','pallet_homogene_count',
            'colis_non_homogene','unites_recues_ccaf_pc','unites_recues_ccvm_pc'], errors='ignore')

        df_reception[["Date", "Heure"]] = df_reception["job_done_datetime"].str.split(",", expand=True)
        df_reception = df_reception.drop(columns=['job_done_datetime'])
        df_reception[["MGB","Désignation"]] = df_reception["art_name"].str.split("-",n=1, expand=True)
        df_reception = df_reception.drop(columns=['art_name'])
        df_reception["Code_Agent"] = df_reception["emp_upn"].str.split(".", expand=True)[0]
        df_reception = df_reception.drop(columns=['emp_upn'])
        
        df_reception = df_reception.rename(columns={
            "art_subsys": "Ref_MERTO",
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
            "Ref_MERTO", "Conditionnement_Vente", "Conditionnement_Fournisseur","Au_Kg", "SSCC",
            "Date_Camion", "N°_Camion", "Cellule",  "Type_Recep","Qty_Reception", "Qty_Colis_Reception"
        ]
        df_reception = df_reception[nouvel_ordre]

        # --- SORTIES ---
        df_sorties = df_sorties.drop(columns=[
            'sto_nr','ord_nr','ord_datetime','cus_sto_nr','cus_nr','ord_status_datetime','inv_date','art_cont_gross','art_cont_gross_unit',
            'ord_line_code','ord_qty_follow','art_pick_tool','art_pick_area','art_pick_id','type_UO','unites_pickees','nb_UO',
            'cre_date','upd_date','art_weight_gross_cust'
        ], errors='ignore')

        df_sorties[["Date", "Heure"]] = df_sorties["art_pick_datetime"].str.split(" ", expand=True)
        df_sorties = df_sorties.drop(columns=['art_pick_datetime'])
        df_sorties["Emplacement"] = df_sorties["art_pick_pos"].str.split("-", n=1, expand=True)[1]
        df_sorties = df_sorties.drop(columns=["art_pick_pos"])
        df_sorties["Code_Agent"] = df_sorties["art_picker_upn"].str.split(".", expand=True)[0]
        df_sorties = df_sorties.drop(columns=['art_picker_upn'])
        df_sorties['Qty/Article/Poids'] = pd.to_numeric(df_sorties['art_pick_qty'], errors='coerce')

        df_sorties = df_sorties.rename(columns={
            'dlv_date': "Date_de_livraison",
            'ord_qty' : "Qty_Commandé",
            "ord_picked_qty" : "Qty_Total_Préparé",
            "art_subsys" : "Ref_MERTO",
            "art_name" : "Désignation",
            "art_weight_ind": "Au_Kg",
            "cellule" : "Cellule"
        })

        df_sorties['MGB'] = df_sorties['art_mgb12'].astype(str)
        df_sorties['MGB_6'] = df_sorties['MGB'].str[:-6]

        nouvel_ordre_s = [
            "Date", "Heure", "Date_de_livraison", "Code_Agent", "MGB","MGB_6", "Désignation","SV",
            "Ref_MERTO","Au_Kg","Qty_Commandé","Qty_Total_Préparé","Qty/Article/Poids", "Cellule",  "Emplacement"
        ]
        df_sorties = df_sorties[nouvel_ordre_s]

        # --- ARTICLES €---
        # --- Nettoyage robuste du fichier Article_€.xlsx ---
        # (à placer juste après df_article_euros = pd.read_excel(file_article) ou
        # si df_article_euros est déjà lu plus haut)

        

        # 1) Si le DF est vide on sort
        if df_article_euros is None or df_article_euros.empty:
            print("df_article_euros vide ou non trouvé.")
        else:
            # Toujours travailler en str pour éviter surprises
            df_article_euros = df_article_euros.astype(str)

            # Nettoyage basique des noms de colonnes lus par pandas
            cols_raw = [str(c).strip() for c in df_article_euros.columns]
            cols_joined = " | ".join(cols_raw).lower()

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

            # 5) Renommer la colonne prix (recherche fuzz : '€', 'unitaire', 'prix')
            euro_col = None
            for c in df_article_euros.columns:
                cl = str(c).lower()
                if '€' in c or 'unitaire' in cl or 'prix' in cl:
                    euro_col = c
                    break
            if euro_col:
                df_article_euros = df_article_euros.rename(columns={euro_col: "Prix_Unitaire"})
 
            # 6) Renommer la colonne référence si nécessaire (ex: 'ref', 'Ref', 'Réf', 'MGB', ...)
            ref_col = None
            for c in df_article_euros.columns:
                cl = str(c).lower()
                if cl in ('ref', 'réf', 'reference', 'reference_id', 'mgb', 'mgb_6'):
                    ref_col = c
                    break
            if ref_col and ref_col != 'ref':
                df_article_euros = df_article_euros.rename(columns={ref_col: 'ref'})
            elif not ref_col:
                # tenter de détecter la colonne référence par type (entier)
                for c in df_article_euros.columns:
                    sample = df_article_euros[c].dropna().astype(str).head(5).tolist()
                    if all(re.fullmatch(r'\d+', s) for s in sample):
                        df_article_euros = df_article_euros.rename(columns={c: 'ref'})
                        ref_col = 'ref'
                        break
                if not ref_col: # toujours pas trouvé
                    print("Colonne référence non trouvée dans df_article_euros.")

            # 7) Convertir Prix_Unitaire en float (retirer '€', remplacer virgule par point)
            if 'Prix_Unitaire' in df_article_euros.columns:
                s = df_article_euros['Prix_Unitaire'].astype(str)
                s = s.str.replace('€', '', regex=False)
                s = s.str.replace('\u00A0', '', regex=False)   # NBSP
                s = s.str.replace(' ', '', regex=False)
                s = s.str.replace(',', '.', regex=False)
                df_article_euros['Prix_Unitaire'] = pd.to_numeric(s, errors='coerce')
            else:
                print("Colonne 'Prix_Unitaire' non trouvée dans df_article_euros.")

        #--- ETAT STOCK ---
        if 'Ref Metro' not in df_etat_stock.columns and 'SubSys' in df_etat_stock.columns:
            df_etat_stock = df_etat_stock.rename(columns={'SubSys': 'Ref Metro'})
            df_etat_stock ['MGB'] = df_etat_stock ['MGB'].astype(str)


            # Vérifier que les colonnes essentielles existent
            essential_cols = ['MGB', 'Description', 'Ref Metro']
            missing_cols = [c for c in essential_cols if c not in df_etat_stock.columns]
            if missing_cols:
                raise ValueError(f"Colonnes manquantes dans l'état stock : {missing_cols}")

            df_etat_stock = df_etat_stock[essential_cols].copy()

            # Ne garder qu'une seule ligne par MGB
            df_etat_stock = df_etat_stock.drop_duplicates(subset='MGB', keep='first')

            # --- Nettoyage des caractères spéciaux dans Description ---
            remplacement = {"Å“": "œ", "Ã‚": "â", "Ã´": "ô", "Ã¨": "ë", "Ã¢": "â", "Ã§": "ç",
                            "Ãª": "ê", "Ã®": "î", "Ã©": "é", "Â°": "°", "Ã": "à", "¤": "", "«": "", "»": "", "Â": ""}
            df_etat_stock["Description"] = df_etat_stock["Description"].replace(remplacement, regex=True)

            # --- Ajouter la colonne EAN depuis le fichier Excel ---
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

            # Gérer les doublons : priorité aux lignes avec EAN rempli
            df_merged.sort_values(by='EAN', key=lambda x: x.notna(), ascending=False, inplace=True)
            df_merged = df_merged.drop_duplicates(subset='MGB', keep='first')

            # Résultat final
            df_etat_stock = df_merged


        # ==================================================
        # AJOUT PRIX + AU_KG + VALEUR DIFFÉRENCE
        # ==================================================
        # Ajouter prix et valeur totale
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
            df_target[value_col] = df_target[quantity_col] * df_target[price_col]

            if display_in_streamlit:
                st.dataframe(df_target.style.format({price_col: "{:.2f}", value_col: "{:.2f}"}))

            return df_target
        def remove_duplicate_columns(df):
            """
            Supprime les colonnes dupliquées dans un DataFrame en gardant la première occurrence.
            """
            if df is None or df.empty:
                return df
            df = df.loc[:, ~df.columns.duplicated()]
            return df

        # --- Valeur Difference ---
        df_inventaire = add_price_and_value(df_inventaire, df_article_euros, 'Ref_MERTO', 'ref', 'Inventaire_Final_Quantity', display_in_streamlit=False)
        df_reception = add_price_and_value(df_reception, df_article_euros, 'Ref_MERTO', 'ref', 'Qty_Reception', display_in_streamlit=False)
        df_sorties = add_price_and_value(df_sorties, df_article_euros, 'Ref_MERTO', 'ref', 'Qty/Article/Poids', display_in_streamlit=False)
        df_mvt_stock = add_price_and_value(df_mvt_stock, df_article_euros, 'Ref_MERTO', 'ref', 'Qty_Mouvement', display_in_streamlit=False)
        
        mapping_inventaire = df_inventaire[['MGB_6', 'Prix_Unitaire']].drop_duplicates()
        mapping_reception = df_reception[['MGB_6', 'Prix_Unitaire']].drop_duplicates()
        mapping_mvt = df_mvt_stock[['MGB_6', 'Prix_Unitaire']].drop_duplicates()
        mapping_global = pd.concat([mapping_inventaire, mapping_reception, mapping_mvt]).drop_duplicates(subset='MGB_6', keep='first')

        # fusionner pour ajouter Prix_Unitaire à df_ecart_stock_last**
        df_ecart_stock_last = df_ecart_stock_last.merge(mapping_global, on='MGB_6', how='left')

        df_ecart_stock_last['Valeur_Difference'] = df_ecart_stock_last['Prix_Unitaire'] * df_ecart_stock_last['Difference_MMS-WMS']
        df_ecart_stock_last['Valeur_Difference'] = pd.to_numeric(df_ecart_stock_last['Valeur_Difference'], errors='coerce').round(2)

        # --- Valeur AU_KG ---

        mapping_aukg_reception = df_reception[['MGB_6', 'Au_Kg']].drop_duplicates()
        mapping_aukg_mvt = df_mvt_stock[['MGB_6', 'Au_Kg']].drop_duplicates()
        mapping_aukg_sorties = df_sorties[['MGB_6', 'Au_Kg']].drop_duplicates()
        mapping_aukg_global = pd.concat([mapping_aukg_reception, mapping_aukg_mvt, mapping_aukg_sorties]).drop_duplicates(subset='MGB_6', keep='first')

        df_ecart_stock_last = df_ecart_stock_last.merge(mapping_aukg_global, on='MGB_6', how='left')

        # --- Réordonner colonnes finales ---
        nouvel_ordre = ["MGB_6", "Désignation", "MMS_Stock", "WMS_Stock", "Difference_MMS-WMS", 
                        'Au_Kg', "Deja_Present", 'Prix_Unitaire', 'Valeur_Difference', 
                        "Date_Dernier_Commentaire", "Commentaire"]
        
        df_ecart_stock_last = df_ecart_stock_last[[col for col in nouvel_ordre if col in df_ecart_stock_last.columns]]
        
        # --- Supprimer les colonnes dupliquées après preprocess ---
        df_mvt_stock = remove_duplicate_columns(df_mvt_stock)
        df_reception = remove_duplicate_columns(df_reception)
        df_sorties = remove_duplicate_columns(df_sorties)
        df_inventaire = remove_duplicate_columns(df_inventaire)
        df_ecart_stock_last = remove_duplicate_columns(df_ecart_stock_last)
        df_ecart_stock_prev = remove_duplicate_columns(df_ecart_stock_prev)
        df_article_euros = remove_duplicate_columns(df_article_euros)

        # ============================================================
        # Préserver les anciens commentaires avant d'écraser le parquet
        # ============================================================
        
        parquet_path = Path(r"https://github.com/IDLAurelienMartin/Data_IDL/blob/main/Cache/ecart_stock_last.parquet")

        if parquet_path.exists():
            try:
                df_old = pd.read_parquet(parquet_path)

                expected = {"MGB_6", "Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"}
                if expected.issubset(set(df_old.columns)):
                    # --- s'assurer qu'il n'y a pas de doublons côté ancien fichier (garder le dernier) ---
                    if df_old["MGB_6"].duplicated().any():
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

        def remove_full_duplicate_rows(df):
            """
            Supprime les lignes entièrement dupliquées dans un DataFrame.
            Garde la première occurrence.
            """
            if df is None or df.empty:
                return df
            return df.drop_duplicates(keep='first')
    
        df_ecart_stock_prev = remove_full_duplicate_rows(df_ecart_stock_prev)
        df_ecart_stock_last = remove_full_duplicate_rows(df_ecart_stock_last)
        df_reception = remove_full_duplicate_rows(df_reception)
        df_sorties = remove_full_duplicate_rows(df_sorties)
        df_inventaire = remove_full_duplicate_rows(df_inventaire)
        df_mvt_stock = remove_full_duplicate_rows(df_mvt_stock)
        df_article_euros = remove_full_duplicate_rows(df_article_euros)
        
        return df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock, df_etat_stock, df_excel_ean,
