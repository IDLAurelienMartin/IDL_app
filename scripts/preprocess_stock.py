# scripts/preprocess_stock.py
import os
import glob
import pandas as pd
from pathlib import Path
import sys

def load_data():
    """
    Charge toutes les données Excel depuis les sous-dossiers Data/.
    Retourne les DataFrames bruts nécessaires au traitement.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    data_dir = BASE_DIR / "Data"

    dossier_mvt_stock = data_dir / "Mvt_Stock"
    dossier_reception = data_dir / "Historique_Réception"
    dossier_sorties = data_dir / "Historique_des_Sorties"
    dossier_ecart_stock = data_dir / "Ecart_Stock"

    def concat_excel_from_folder(folder):
        fichiers = glob.glob(str(folder / "*.xlsx"))
        if not fichiers:
            return pd.DataFrame()
        return pd.concat((pd.read_excel(f) for f in fichiers), ignore_index=True)

    # Chargement des données
    df_mvt_stock = concat_excel_from_folder(dossier_mvt_stock)
    df_reception = concat_excel_from_folder(dossier_reception)
    df_sorties = concat_excel_from_folder(dossier_sorties)

    # Récupération des deux derniers fichiers d’écart
    files = sorted(dossier_ecart_stock.glob("*.xlsx"), key=os.path.getmtime)
    if len(files) < 2:
        raise FileNotFoundError("Pas assez de fichiers dans Ecart_Stock pour comparaison.")
    file_prev, file_last = files[-2], files[-1]

    df_ecart_stock_prev = pd.read_excel(file_prev)
    df_ecart_stock_last = pd.read_excel(file_last)

    # Articles et inventaire
    file_article = data_dir / "Article_€.xlsx"
    file_inventaire = data_dir / "Inventory_21_09_2025.xlsx"

    df_article_euros = pd.read_excel(file_article) if file_article.exists() else pd.DataFrame()
    df_inventaire = pd.read_excel(file_inventaire) if file_inventaire.exists() else pd.DataFrame()
    
    # Chemin du fichier parquet (toujours fixe dans le cache)
    file_last_parquet = data_dir / "Cache" / "ecart_stock_last.parquet"

    # Écrit ce chemin dans file_last.txt
    file_last_txt = data_dir / "file_last.txt"
    with open(file_last_txt, "w", encoding="utf-8") as f:
        f.write(str(file_last_parquet).replace("\\", "/"))  # pour compatibilité Streamlit/Windows


    return (
        df_mvt_stock,
        df_reception,
        df_sorties,
        df_inventaire,
        df_ecart_stock_prev,
        df_ecart_stock_last,
        df_article_euros,
        file_last,
    )

def preprocess_data(df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock):  

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

        else:
            print("Aucun fichier inventaire trouvé ou vide.")

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
            "CCVM": "Conditionnement_Vente",
            "CCAF": "Conditionnement_Fournisseur",
            "stk_mvt_type": "Type_Mouvement",
            "stk_chg_desc": "Info_Mouvement",
            "cellule": "Cellule",
            'stk_sync_mms_ind':'Synchro_MMS',
            'MGB' : 'MGB_6',
            "art_mgb12": "MGB"
        })

        # Liste des colonnes dans l'ordre souhaité et suppression des doublons
        nouvel_ordre = ["Date", "Heure", "Code_Agent","MGB","MGB_6", "Désignation", "SV", "SA", "GA", "Ref_MERTO",
                        "Au_Kg", "SSCC", "Type_Mouvement","Code_Mouvement","Intituler_Mouvement", "Info_Mouvement",
                        'Synchro_MMS',"Cellule", "Conditionnement_Vente", "Conditionnement_Fournisseur",
                        'prefix_emplacement',"Emplacement","Qty_Mouvement"]
        nouvel_ordre = list(dict.fromkeys(nouvel_ordre))  # supprime les doublons
        df_mvt_stock = df_mvt_stock[nouvel_ordre]

        df_mvt_stock['Synchro_MMS'] = df_mvt_stock['Synchro_MMS'].replace({1: 'Oui', 0: 'Non'})
        df_mvt_stock['Type_Mouvement'] = df_mvt_stock['Type_Mouvement'].replace({
            'DELETE_STOCK': 'Modification_Stock',
            'EDIT_QUANTITY': 'Suppression_Stock',
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

        import re

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
                print("Info: La première ligne semble contenir l'entête réelle → on l'utilise comme header.")
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

            print("Colonnes après nettoyage :", list(df_article_euros.columns))

            # 5) Renommer la colonne prix (recherche fuzz : '€', 'unitaire', 'prix')
            euro_col = None
            for c in df_article_euros.columns:
                cl = str(c).lower()
                if '€' in c or 'unitaire' in cl or 'prix' in cl:
                    euro_col = c
                    break
            if euro_col:
                df_article_euros = df_article_euros.rename(columns={euro_col: "Prix_Unitaire"})
                print(f"-> Colonne prix détectée et renommée : '{euro_col}' -> 'Prix_Unitaire'")
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
                print(f"-> Colonne référence renommée : '{ref_col}' -> 'ref'")
            elif not ref_col:
                # tenter de détecter la colonne référence par type (entier)
                for c in df_article_euros.columns:
                    sample = df_article_euros[c].dropna().astype(str).head(5).tolist()
                    if all(re.fullmatch(r'\d+', s) for s in sample):
                        df_article_euros = df_article_euros.rename(columns={c: 'ref'})
                        ref_col = 'ref'
                        print(f"-> Colonne référence détectée automatiquement : '{c}' -> 'ref'")
                        break
                if not ref_col:
                    print("Colonne référence introuvable automatiquement. Vérifie le fichier Article_€.xlsx")

            # 7) Convertir Prix_Unitaire en float (retirer '€', remplacer virgule par point)
            if 'Prix_Unitaire' in df_article_euros.columns:
                s = df_article_euros['Prix_Unitaire'].astype(str)
                s = s.str.replace('€', '', regex=False)
                s = s.str.replace('\u00A0', '', regex=False)   # NBSP
                s = s.str.replace(' ', '', regex=False)
                s = s.str.replace(',', '.', regex=False)
                df_article_euros['Prix_Unitaire'] = pd.to_numeric(s, errors='coerce')
                print("-> Conversion 'Prix_Unitaire' en numérique effectuée.")
            else:
                print("'Prix_Unitaire' absent, conversion ignorée.")

            print("Aperçu articles (head):")
            print(df_article_euros.head(5))



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
        # 🧩 Préserver les anciens commentaires avant d'écraser le parquet
        # ============================================================
        BASE_DIR = Path(__file__).resolve().parent.parent
        data_dir = BASE_DIR / "Data" / "Cache"
        parquet_path = data_dir / "ecart_stock_last.parquet"

        if parquet_path.exists():
            try:
                df_old = pd.read_parquet(parquet_path)

                if {"MGB_6", "Commentaire", "Date_Dernier_Commentaire"}.issubset(df_old.columns):
                    print("Fusion des anciens commentaires avec les nouvelles données...")

                    # Fusion sur MGB_6
                    df_ecart_stock_last = df_ecart_stock_last.merge(
                        df_old[["MGB_6", "Commentaire", "Date_Dernier_Commentaire"]],
                        on="MGB_6",
                        how="left",
                        suffixes=("", "_old")
                    )

                    # Conserver les anciens commentaires si les nouveaux sont vides
                    df_ecart_stock_last["Commentaire"] = df_ecart_stock_last["Commentaire"].combine_first(
                        df_ecart_stock_last["Commentaire_old"]
                    )
                    df_ecart_stock_last["Date_Dernier_Commentaire"] = df_ecart_stock_last["Date_Dernier_Commentaire"].combine_first(
                        df_ecart_stock_last["Date_Dernier_Commentaire_old"]
                    )

                    # Supprimer les colonnes intermédiaires
                    df_ecart_stock_last.drop(columns=["Commentaire_old", "Date_Dernier_Commentaire_old"], inplace=True)

            except Exception as e:
                print(f"Impossible de restaurer les anciens commentaires : {e}")
        else:
            print("Aucun ancien parquet trouvé, création initiale du fichier.")


        return df_ecart_stock_prev, df_ecart_stock_last, df_reception, df_sorties, df_inventaire, df_article_euros, df_mvt_stock
