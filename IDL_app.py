from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import qrcode
from barcode.ean import EAN13
from barcode.writer import ImageWriter
from pathlib import Path
import glob
import os
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from fpdf import FPDF
import io
import subprocess
from datetime import datetime
import streamlit as st
from scripts.prepare_data import update_emplacement, ajouter_totaux, color_rows   

def tab_home():
    st.title("Accueil")
    st.write("Bienvenue dans l'application IDL_LaBrede.")
    
def tab_QR_Codes():
    st.title("QR Codes et Code Barre")

    # --- Listes ---
    Liste_choix_Qr_code = ['Vide','Emplacement', 'QR Code MGB','Autres QR Codes', 'EAN']
    Liste_allée = {
        "Ambiant": ['1','2','3','4','5','6','7','8','9','10','11','12'],
        "Frais": ['19','20','21','22','23','24','25','26'],
        "FL": ['30','31','32','33'],
        "Surgelé": ['38','39','40','41','42','43'],
        "Marée": ['50','51','52','53']
    }
    Liste_rangée = [str(i) for i in range(1, 41)]
    Liste_niveau = {
        "Ambiant": ['A1','A2','A3','A4','B1','C1','D1'],
        "Frais": ['A1','A2','A3','A4','B1'],
        "FL": ['A1','A2','A3','A4','B1'],
        "Surgelé": ['A1','A2','A3','A4','B1','C1','D1'],
        "Marée": ['A1','A2','A3','A4']
    }
    Liste_emplacement = [str(i) for i in range(1, 13)]

    # Choix du type de QR Code
    option = st.selectbox('Choix type de QR Code ou Code Barre :', options= Liste_choix_Qr_code)
    
    if option == "Emplacement":
        # --- Choix du format ---
        nb_qr_format = st.radio("Choisir le format :", ["Grand Format", "Petit Format"])
        nb_qr_serie = st.radio("Choisir types :", ["Unités", "Série"])
        if nb_qr_serie == "Unités":
            if nb_qr_format == "Grand Format":
                qr_count = st.selectbox("Nombre de QR Codes :", range(1, 101))
                cols_per_row = 1
                font_size = 38
                frame_width = A4[0] - 20
                frame_height = 273
                spacing = 1
            else:
                qr_count = st.selectbox("Nombre de QR Codes :", range(1, 101))
                cols_per_row = 2
                font_size = 12
                frame_width = (A4[0] - 130) / 2
                frame_height = 130
                spacing = 30
        else :
            if nb_qr_format == "Grand Format":
                qr_count_serie = st.selectbox("Nombre de Série de QR Codes :", range(1, 11))
                qr_count = 101
                cols_per_row = 1
                font_size = 38
                frame_width = A4[0] - 20
                frame_height = 273
                spacing = 1
            else:
                qr_count_serie = st.selectbox("Nombre de Série de QR Codes :", range(1, 11))
                qr_count = 101
                cols_per_row = 2
                font_size = 12
                frame_width = (A4[0] - 130) / 2
                frame_height = 130
                spacing = 30

        # --- Définir le chemin de la police ---
        FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"
        try:
            font = ImageFont.truetype(str(FONT_PATH), font_size)
        except Exception as e:
            st.error(f"Erreur police: {e}")
            font = ImageFont.load_default()

        # --- Sélection des QR Codes ---
        st.subheader("Choisir les QR Codes")
        qr_infos = []

        if nb_qr_serie == "Unités":
            for i in range(qr_count):
                st.markdown(f"**QR Code #{i+1}**")
                cellule = st.selectbox(f"Cellule", options=list(Liste_allée.keys()), key=f"Cellule_{i}")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    allée = st.selectbox(f"Allée", options=Liste_allée[cellule], key=f"Allée_{i}")
                with col2:
                    rangée = st.selectbox(f"Rangée", options=Liste_rangée, key=f"Rangée_{i}")
                with col3:
                    niveau = st.selectbox(f"Niveau", options=Liste_niveau[cellule], key=f"Niveau_{i}")
                with col4:
                    colonne = st.selectbox(f"Colonne", options=Liste_emplacement, key=f"Colonne_{i}")
                qr_infos.append({
                    "Cellule": cellule,
                    "Allée": allée,
                    "Rangée": rangée,
                    "Niveau": niveau,
                    "Colonne": colonne
                })
        
        else:
            for i in range(qr_count_serie):
                st.markdown(f"**Serie #{i+1}**")
                col1, col2, col3 = st.columns(3)
                # Sélections communes
                with col1:
                    cellule = st.selectbox("Cellule", options=list(Liste_allée.keys()), key=f"Cellule_{i}")
                with col2:
                    allée = st.selectbox("Allée", options=Liste_allée[cellule], key=f"Allée_{i}")
                with col3:
                    rangée = st.selectbox("Rangée", options=Liste_rangée, key=f"Rangée_{i}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Choisi les Niveaux**")
                    niveau_start = st.selectbox("Niveau début", options=Liste_niveau[cellule], key=f"Niveau_start_{i}")
                    niveau_end = st.selectbox("Niveau fin", options=Liste_niveau[cellule], key=f"Niveau_end_{i}")
                with col3:
                    st.markdown(f"**Choisi les Colonnes**")
                    col_start = st.selectbox("Colonne début", options=Liste_emplacement, key=f"Colonne_start_{i}")
                    col_end = st.selectbox("Colonne fin", options=Liste_emplacement, key=f"Colonne_end_{i}")

                # Construire les plages
                niveaux = Liste_niveau[cellule]
                colonnes = Liste_emplacement

                try:
                    start_idx_niv = niveaux.index(niveau_start)
                    end_idx_niv = niveaux.index(niveau_end)
                    start_idx_col = colonnes.index(col_start)
                    end_idx_col = colonnes.index(col_end)

                    niveaux_range = niveaux[min(start_idx_niv, end_idx_niv): max(start_idx_niv, end_idx_niv)+1]
                    colonnes_range = colonnes[min(start_idx_col, end_idx_col): max(start_idx_col, end_idx_col)+1]

                    total_etiquettes = len(niveaux_range) * len(colonnes_range)

                    if total_etiquettes > qr_count:
                        st.error(f"⚠️ Trop d’étiquettes ({total_etiquettes}), maximum autorisé : {qr_count}")
                    else:
                        for niv in niveaux_range:
                            for col in colonnes_range:
                                qr_infos.append({
                                    "Cellule": cellule,
                                    "Allée": allée,
                                    "Rangée": rangée,
                                    "Niveau": niv,
                                    "Colonne": col
                                })
                                

                except ValueError:
                    st.error("Erreur : les valeurs choisies ne sont pas dans les listes disponibles.")

        # --- Génération PDF ---
        if st.button("Générer le PDF A4"):
            pdf_buffer = BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            page_width, page_height = A4

            margin_top = 10 if nb_qr_format == "Grand Format" else 30
            margin_bottom = 10 if nb_qr_format == "Grand Format" else 30
            margin_left = 10 if nb_qr_format == "Grand Format" else 50

            usable_height = page_height - margin_top - margin_bottom
            rows_per_page = max(1, int((usable_height + spacing) // (frame_height + spacing)))
            items_per_page = rows_per_page * cols_per_row
            top_y = page_height - margin_top
            current_page = 0

            for idx, info in enumerate(qr_infos):
                page_index = idx // items_per_page
                if page_index > current_page:
                    c.showPage()
                    current_page = page_index

                idx_in_page = idx % items_per_page
                row = idx_in_page // cols_per_row
                col = idx_in_page % cols_per_row
                x = margin_left + col * (frame_width + spacing)
                y = top_y - (row * (frame_height + spacing)) - frame_height

                # Préfixe selon cellule
                prefix = ""
                if info["Cellule"] in ["Ambiant", "Frais", "FL"]:
                    prefix = "MEAT_SPECIAL_HANDLING-"
                elif info["Cellule"] == "Marée":
                    prefix = "FISH-"
                elif info["Cellule"] == "Surgelé":
                    prefix = "DEEP_FROZEN-"

                texte_affiche = f"{info['Allée']}-{info['Rangée']}-{info['Niveau']}-{info['Colonne']}"
                contenu_qr = prefix + texte_affiche

                # Couleur fond texte selon niveau
                if info["Niveau"] == "D1":
                    text_bg_color = "yellow"
                elif info["Niveau"] == "C1":
                    text_bg_color = "red"
                elif info["Niveau"] == "B1":
                    text_bg_color = "lightgreen"
                else:
                    text_bg_color = "white"

                combined = Image.new("RGB", (int(frame_width), int(frame_height)), "white")
                if nb_qr_format == "Grand Format" :
                    qr_width = int(frame_width * 0.55)
                    qr_height = int(frame_height * 1.15)
                else :
                    qr_width = int(frame_width * 0.62)
                    qr_height = int(frame_height * 1.15)
                qr_offset = -20 if nb_qr_format == "Grand Format" else -10
                text_x0 = max(qr_width + qr_offset, 0)
                text_x1 = frame_width

                draw = ImageDraw.Draw(combined)
                draw.rectangle([(text_x0, 0), (text_x1, frame_height)], fill=text_bg_color)

                qr_img = qrcode.make(contenu_qr).convert("RGB")
                qr_img = qr_img.resize((qr_width, qr_height))
                combined.paste(qr_img, (-20, -20) if nb_qr_format == "Grand Format" else (-10, -10))

                # Utiliser la police embarquée pour Render
                try:
                    font = ImageFont.truetype(str(FONT_PATH), font_size)
                except Exception as e:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), texte_affiche, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = text_x0 + (frame_width - text_x0 - text_width) // 2
                text_y = (frame_height - text_height) // 2
                draw.text((text_x, text_y), texte_affiche, fill="black", font=font)
                draw.rectangle([(0, 0), (int(frame_width)-1, int(frame_height)-1)], outline="black", width=2)

                img_byte_arr = BytesIO()
                combined.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                c.drawImage(ImageReader(img_byte_arr), float(x), float(y), width=float(frame_width), height=float(frame_height))

            c.save()
            pdf_buffer.seek(0)
            st.download_button(
                label="📥 Télécharger PDF",
                data=pdf_buffer,
                file_name="QR_Codes_A4.pdf",
                mime="application/pdf"
            )

    elif option == 'QR Code MGB':
        
        # Initialisation des états si pas encore définis
        if 'MGB' not in st.session_state:
            st.session_state['MGB'] = ""
        if 'confirm_11' not in st.session_state:
            st.session_state['confirm_11'] = False

        st.subheader("MGB :")
        
        st.session_state['MGB'] = st.text_input(
            "Entrer le numéro du MGB",
            value=st.session_state.get('MGB', ''),
            key="mgb_input"
        )


        def generate_qr(MGB):
            qr_img = qrcode.make(MGB).convert("RGB")
            qr_img = qr_img.resize((250, 250))
            st.image(qr_img, caption="QR Code du MGB", use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                buffer = BytesIO()
                qr_img.save(buffer, format="PNG")
                buffer.seek(0)
                st.download_button(
                    label="Télécharger le QR Code",
                    data=buffer,
                    file_name=f"QR_Code_{MGB}.png",
                    mime="image/png"
                )
            with col2:
                if st.button("Effacer le QR Code"):
                    st.session_state['MGB'] = ""
                    st.session_state['confirm_11'] = False

        # Bouton principal
        if st.button("Générer le QR Code"):
            MGB = st.session_state['MGB']
            if not MGB.isdigit():
                st.error("Le MGB doit être un nombre.")
            elif len(MGB) == 12:
                generate_qr(MGB)
            elif len(MGB) == 11:
                st.warning("Es-tu sûr que ton MGB n'a pas 12 chiffres ?")
                st.session_state['confirm_11'] = True
            else:
                st.error("Le MGB doit avoir 11 ou 12 chiffres.")

        # Si confirmation pour 11 chiffres
        if st.session_state['confirm_11']:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Oui, générer le QR Code"):
                    generate_qr(st.session_state['MGB'])
                    st.session_state['confirm_11'] = False
            with col2:
                if st.button("Non, corriger le MGB"):
                    st.info("Merci de remplir le champ correctement.")
                    st.session_state['confirm_11'] = False
    
    
    elif option == 'Autres QR Codes':

        st.title("Autres QR Codes")

        # Initialiser session_state
        if "MGB" not in st.session_state:
            st.session_state["MGB"] = ""

        user_input = st.text_input("Entrez le texte ou l'URL :", st.session_state["MGB"])

        # Bouton Générer
        if st.button("Générer le QR Code"):
            st.session_state["MGB"] = user_input  # on garde la valeur en mémoire

        # Affichage du QR Code si on a une valeur
        if st.session_state["MGB"]:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(st.session_state["MGB"])
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            
            buf = BytesIO()
            img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Votre QR Code")

            st.download_button(
                label="📥 Télécharger le QR Code",
                data=buf.getvalue(),
                file_name="qrcode.png",
                mime="image/png"
            )
            # Bouton Effacer
            if st.button("Effacer le QR Code"):
                st.session_state["MGB"] = ""
                st.rerun()




    elif option == 'EAN':
        st.subheader("EAN :")
        
        EAN_input = st.text_input("Entrez un code EAN")

        if st.button("Générer le Code Barre"): 
            try:
                # Cas valide → génération du code-barres
                ean = EAN13(EAN_input, writer=ImageWriter())

                buffer = BytesIO()
                ean.write(buffer)
                buffer.seek(0)

                st.image(buffer, caption=f"Code barre du EAN {EAN_input}", use_container_width=True)

            except Exception as e:
                # Ici on intercepte toute autre erreur
                st.error("Une erreur est survenue lors de la génération du code barre.")

            # Boutons pour téléchargement et effacer
            col1, col2 = st.columns(2)
            with col1:
                    st.download_button(
                    label="Télécharger le code barre",
                    data=buffer,
                    file_name=f"Code_barre_{EAN_input}.png",
                    mime="image/png"
                    )
            with col2:
                    if st.button("Effacer le code barre"):
                            st.experimental_rerun()


# --- Dossier cache local sur Render ---
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# --- URL GitHub pour les fichiers parquet initiaux ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/aumartin/idl_gd/main/data_parquet"

# --- Fonction pour charger parquet depuis cache ou GitHub ---
def load_parquet(file_name):
    local_path = CACHE_DIR / file_name
    if local_path.exists():
        return pd.read_parquet(local_path)
    url = f"{GITHUB_RAW_URL}/{file_name}"
    try:
        df = pd.read_parquet(url)
        df.to_parquet(local_path, index=False)  # sauvegarde dans cache
        return df
    except Exception as e:
        st.warning(f"Impossible de charger {file_name} depuis GitHub : {e}")
        return pd.DataFrame()

# --- Fonction pour sauvegarder parquet dans cache ---
def save_parquet(df, file_name):
    local_path = CACHE_DIR / file_name
    df.to_parquet(local_path, index=False)
    st.success(f"{file_name} sauvegardé dans le cache Render !")


def Analyse_stock():
    today = datetime.today().strftime("%d/%m/%Y")
    st.set_page_config(layout="wide")

    # --- Charger les fichiers ---
    df_article_euros = load_parquet("article_euros.parquet")
    df_inventaire    = load_parquet("inventaire.parquet")
    df_mvt_stock     = load_parquet("mvt_stock.parquet")
    df_reception     = load_parquet("reception.parquet")
    df_sorties       = load_parquet("sorties.parquet")
    df_ecart_stock_prev = load_parquet("ecart_stock_prev.parquet")
    df_ecart_stock_last = load_parquet("ecart_stock_last.parquet")

    # Harmoniser colonne MGB_6
    for df in [df_article_euros, df_inventaire, df_mvt_stock, df_reception, df_sorties, df_ecart_stock_prev, df_ecart_stock_last]:
        if "MGB_6" in df.columns:
            df["MGB_6"] = df["MGB_6"].astype(str).str.strip().str.replace(" ", "")

    st.title("Analyse des écarts de stock")

    if not df_mvt_stock.empty:
        df_mvt_stock['Emplacement'] = df_mvt_stock.apply(update_emplacement, axis=1)
        df_mvt_stock = df_mvt_stock.drop(columns=['prefix_emplacement'], errors='ignore')

    # --- Liste des MGB en consigne ---
    MGB_consigne = [
        "226796","890080","179986","885177","890050","226923","834397","890070",
        "886655","226725","226819","226681","897881","897885","897890","897698",
        "226658","226783","896634","226654","226814","226830","173907","897814",
        "226781","897704","886648","881810","226864","226780","633936","226932",
        "226995","226661","226690","180719","226993","226712","897082","135185",
        "226762","180717","226971","226704","872843","226875","226662","180716",
        "226820","892476","893404","226876","633937","226900","897083","881813",
        "135181","383779","226802","897816","180720","173902","226840","226889",
        "890060",'835296'
    ]

    # --- Filtrage et interface Streamlit ---
    st.subheader("Tableau des écarts")

    # Colonnes de filtre
    cols = st.columns(5)
    options_1 = ["Toutes", "Positives", "Négatives", "Zéro"]
    options_2 = ["Tous", "Oui", "Non"]
    options_3 = ["Toutes","<5","5-10","10-15","15-20","20+"]
    options_4 = ["Toutes", "Positives", "Zéro"]
    options_5 = ["Toutes", "Positives", "Négatives"]

    filtres = {
        "WMS_Stock": {"col": cols[1], "options": options_4, "type": "numeric"},
        "MMS_Stock": {"col": cols[0], "options": options_1, "type": "numeric"},
        "Au_Kg": {"col": cols[2], "options": options_2, "type": "bool"},
        "Difference_MMS-WMS_Valeur": {"col": cols[3], "options": options_3, "type": "range", "df_col": "Difference_MMS-WMS"},
        "Difference_MMS-WMS_+/-": {"col": cols[4], "options": options_5, "type": "numeric", "df_col": "Difference_MMS-WMS"},
    }

    # Initialiser session_state pour filtres
    for key, filt in filtres.items():
        state_key = f"filter_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = filt["options"][0]

    # Réinitialisation filtres
    def reset_filters():
        for key in filtres.keys():
            st.session_state[f"filter_{key}"] = filtres[key]["options"][0]

    for key, filt in filtres.items():
        state_key = f"filter_{key}"
        filt["value"] = filt["col"].selectbox(
            key.replace("_", " "),
            filt["options"],
            index=filt["options"].index(st.session_state[state_key]),
            key=state_key
        )
    cols[0].button("Réinitialiser les filtres", on_click=reset_filters)

    # --- Filtre Deja_Present ---
    deja_present_options = ["Tous", "Oui", "Non"]
    if "filter_Deja_Present" not in st.session_state:
        st.session_state["filter_Deja_Present"] = deja_present_options[0]
    filter_choice_6 = cols[0].selectbox(
        "Deja_Present",
        deja_present_options,
        index=deja_present_options.index(st.session_state["filter_Deja_Present"]),
        key="filter_Deja_Present"
    )

    # --- Appliquer filtres ---
    df_filtered = df_ecart_stock_last.copy()
    for key, filt in filtres.items():
        val = st.session_state[f"filter_{key}"]
        df_col = filt.get("df_col", key)
        if filt["type"] == "numeric":
            if val == "Positives":
                df_filtered = df_filtered[df_filtered[df_col] > 0]
            elif val == "Négatives":
                df_filtered = df_filtered[df_filtered[df_col] < 0]
            elif val == "Zéro":
                df_filtered = df_filtered[df_filtered[df_col] == 0]
        elif filt["type"] == "bool":
            if val == "Oui":
                df_filtered = df_filtered[df_filtered[df_col] == True]
            elif val == "Non":
                df_filtered = df_filtered[df_filtered[df_col] != True]
        elif filt["type"] == "range":
            ranges = {"<5": (0,5),"5-10": (5,10),"10-15":(10,15),"15-20":(15,20),"20+":(20,float("inf"))}
            if val in ranges:
                low, high = ranges[val]
                df_filtered = df_filtered[(df_filtered[df_col].abs()>=low)&(df_filtered[df_col].abs()<high)]

    # Filtre Deja_Present
    map_bool = {"Tous": None,"Oui": True,"Non": False}
    val_bool = map_bool[st.session_state["filter_Deja_Present"]]
    if val_bool is not None:
        df_filtered = df_filtered[df_filtered["Deja_Present"].astype(bool) == val_bool]

    # --- Affichage final ---
    df_affiche = df_filtered[~df_filtered["MGB_6"].astype(str).isin(MGB_consigne)].copy()
    df_affiche = df_affiche.reindex(df_affiche["Difference_MMS-WMS"].abs().sort_values(ascending=False).index)

    # Différence précédente
    df_prev_diff = df_ecart_stock_prev[['MGB_6','Difference_MMS-WMS']].rename(columns={'Difference_MMS-WMS':'Difference_prev'})
    df_affiche = df_affiche.merge(df_prev_diff, on='MGB_6', how='left')

    def highlight_diff_change(row):
        if pd.notna(row['Difference_prev']) and row['Difference_MMS-WMS'] != row['Difference_prev']:
            return ['background-color: #FFA500']*len(row)
        else:
            return ['']*len(row)

    st.dataframe(df_affiche.style.apply(highlight_diff_change, axis=1).format({
        '€_Unitaire': "{:.2f}",
        'Valeur_Difference': "{:.2f}"
    }))

    col1, col2 = st.columns(2)
    col1.subheader(f"Nombre de lignes (hors consignes): {len(df_affiche)}")
    total_value = df_affiche['Valeur_Difference'].sum()
    col2.subheader(f"Valeur total des écarts : {total_value:.2f} €")

    # --- Menu MGB ---
    col1, col2 = st.columns(2)
    mgb_list = df_affiche['MGB_6'].dropna().unique() if not df_affiche.empty else []
    mgb_selected = col1.selectbox("Choisir un MGB", mgb_list)

    # --- Filtrage DataFrames par MGB ---
    stock_info = df_ecart_stock_last[df_ecart_stock_last['MGB_6']==mgb_selected]
    inventaire_info = df_inventaire[df_inventaire['MGB_6']==mgb_selected]
    mvt_info = df_mvt_stock[df_mvt_stock['MGB_6']==mgb_selected]

    # --- Ajout commentaire ---
    st.subheader("Commentaires")
    comment_file = CACHE_DIR / f"{mgb_selected}_commentaires.parquet"
    if comment_file.exists():
        df_comments = pd.read_parquet(comment_file)
    else:
        df_comments = pd.DataFrame(columns=["MGB_6","Commentaire","Date"])
    
    new_comment = st.text_input("Ajouter un commentaire")
    if st.button("Enregistrer commentaire"):
        if new_comment.strip():
            df_comments = pd.concat([df_comments, pd.DataFrame({
                "MGB_6":[mgb_selected],
                "Commentaire":[new_comment],
                "Date":[today]
            })], ignore_index=True)
            save_parquet(df_comments, f"{mgb_selected}_commentaires.parquet")

    st.dataframe(df_comments[df_comments["MGB_6"]==mgb_selected])

    # --- Génération PDF ---
    if st.button("Exporter PDF"):
        pdf_file = CACHE_DIR / f"Stock_{mgb_selected}_{today.replace('/','-')}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0,10,f"Analyse Stock MGB {mgb_selected} - {today}", ln=True)
        for idx, row in stock_info.iterrows():
            pdf.cell(0,10,f"{row['MGB_6']} | MMS: {row['MMS_Stock']} | WMS: {row['WMS_Stock']} | Diff: {row['Difference_MMS-WMS']}", ln=True)
        pdf.output(str(pdf_file))
        st.success(f"PDF généré : {pdf_file}")

def tab_realisateurs():
    st.title("Réalisateurs")

# Configuration des onglets
tabs = {
    "Accueil": tab_home,
    "QR Codes et Code Barre": tab_QR_Codes,
    "Analyse Stock": Analyse_stock,
    "X3": tab_realisateurs
}

def main():
    
    # Nouveau dossier de base : ton OneDrive
    onedrive_dir = Path(r"https://github.com/IDLAurelienMartin/Data_IDL.git")

    # Chemins des images dans ton OneDrive
    IMAGE_PATH_1 = onedrive_dir / "Images" / "logo_IDL.jpg"
    IMAGE_PATH_2 = onedrive_dir / "Images" / "Logo_Metro.webp"

    # Vérification d’existence (pour éviter les erreurs Streamlit si un fichier manque)
    if IMAGE_PATH_1.exists():
        st.sidebar.image(str(IMAGE_PATH_1), use_container_width=True)
    else:
        st.sidebar.warning(f"⚠️ Image non trouvée : {IMAGE_PATH_1}")

    st.sidebar.header("Navigation")
    selected_tab = st.sidebar.radio("", list(tabs.keys()))
    tabs[selected_tab]()

    if IMAGE_PATH_2.exists():
        st.sidebar.image(str(IMAGE_PATH_2), use_container_width=True)
    else:
        st.sidebar.warning(f"⚠️ Image non trouvée : {IMAGE_PATH_2}")

     # --- Bouton actualiser ---
    if st.sidebar.button("Actualiser les données"):
        with st.spinner("Exécution du script run_all.py..."):
            script_path = Path(__file__).resolve().parent / "scripts" / "run_all.py"
            try:
                # Exécution du script
                result = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    st.sidebar.success("Actualisation terminée avec succès !")
                else:
                    st.sidebar.error(f"Erreur lors de l’exécution :\n{result.stderr}")
            except Exception as e:
                st.sidebar.error(f"Erreur : {e}")

    
    # Sidebar color
    st.markdown("""
    <style>
        [data-testid=stSidebar] {
            background-color : #D9DDFF;
            background-size: cover;
        }
    </style>
    """, unsafe_allow_html=True)

    # Background image
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"]{
            background-color : #D9DDFF ;
            background-size: cover;
        }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()



