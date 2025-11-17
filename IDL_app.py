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
from git import Repo
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


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
# Render place les fichiers persistants dans le dossier /opt/render/project/src/render_cache
RENDER_CACHE_DIR = Path("/opt/render/project/src/render_cache")
LOCAL_CACHE_DIR = Path("Cache")
GIT_REPO_DIR = Path("/opt/render/project/src")  # ton repo local

# On crée aussi le dossier Cache pour éviter les erreurs
LOCAL_CACHE_DIR.mkdir(exist_ok=True)

def load_parquet_local(file_name):
    """
    Ordre de récupération :
    1) /opt/render/project/src/render_cache/
    2) Cache/
    3) Repo Git local (/opt/render/project/src/)
    """

    # 1) Chemin Render Cache
    render_path = RENDER_CACHE_DIR / file_name
    if render_path.exists():
        try:
            return pd.read_parquet(render_path)
        except Exception as e:
            st.warning(f"Erreur lecture Render cache → {e}")

    # 2) Chemin Cache Streamlit
    local_path = LOCAL_CACHE_DIR / file_name
    if local_path.exists():
        try:
            return pd.read_parquet(local_path)
        except Exception as e:
            st.warning(f"Erreur lecture Cache local → {e}")

    # 3) Fallback Git (repo cloné automatiquement par Render)
    git_path = GIT_REPO_DIR / file_name
    if git_path.exists():
        try:
            df = pd.read_parquet(git_path)

            # On sauvegarde en cache local pour les prochaines lectures
            LOCAL_CACHE_DIR.mkdir(exist_ok=True)
            df.to_parquet(local_path)

            return df
        except Exception as e:
            st.error(f"Erreur lecture fichier dans Git → {e}")

    # 4) Fichier absent partout
    st.error(f"Fichier introuvable : {file_name}")
    return pd.DataFrame()

def save_parquet_local(df, file_name):
    """
    Sauvegarde UNIQUE dans le dossier Cache/ interne.
    Render ne permet pas d'écrire dans render_cache (lecture seule).
    """
    local_path = LOCAL_CACHE_DIR / file_name
    df.to_parquet(local_path, index=False)
    st.success(f"{file_name} sauvegardé dans Cache/")

def git_commit_push(file_path: Path, message: str):
    """
    Commit et push automatique d'un fichier vers GitHub.
    """
    try:
        subprocess.run(["git", "-C", str(GIT_REPO_DIR), "add", str(file_path)], check=True)
        subprocess.run(["git", "-C", str(GIT_REPO_DIR), "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", str(GIT_REPO_DIR), "push"], check=True)
        st.success(f"{file_path.name} poussé sur Git avec succès !")
    except subprocess.CalledProcessError as e:
        st.error(f"Erreur Git : {e}")

def Analyse_stock():

    st.set_page_config(layout="wide")

    # --- Lire UNIQUEMENT depuis Render ---
    df_article_euros = load_parquet_local("article_euros.parquet")
    df_ecart_stock_prev = load_parquet_local("ecart_stock_prev.parquet")
    df_ecart_stock_last = load_parquet_local("ecart_stock_last.parquet")
    df_reception = load_parquet_local("reception.parquet")
    df_sorties = load_parquet_local("sorties.parquet")
    df_inventaire = load_parquet_local("inventaire.parquet")
    df_mvt_stock = load_parquet_local("mvt_stock.parquet")

    if df_article_euros.empty:
        st.stop()
   
    # Harmoniser le format de la colonne MGB_6 dans tous les DataFrames
    for df in [df_article_euros, df_inventaire, df_mvt_stock, df_reception, df_sorties, df_ecart_stock_prev, df_ecart_stock_last]:
        if "MGB_6" in df.columns:
            df["MGB_6"] = df["MGB_6"].astype(str).str.strip().str.replace(" ", "")

    # --- Interface principale Streamlit ---
    st.title("Analyse des écarts de stock")

    # Préparation légère ou ajustements (si nécessaires)
    if not df_mvt_stock.empty:
        df_mvt_stock['Emplacement'] = df_mvt_stock.apply(update_emplacement, axis=1)
        df_mvt_stock = df_mvt_stock.drop(columns=['prefix_emplacement'], errors='ignore')

    # --- Liste des MGB à traiter en "Consigne" (XX) ---
    MGB_consigne = [
        "226796", "890080", "179986", "885177", "890050", "226923", "834397", "890070",
        "886655", "226725", "226819", "226681", "897881", "897885", "897890", "897698",
        "226658", "226783", "896634", "226654", "226814", "226830", "173907", "897814",
        "226781", "897704", "886648", "881810", "226864", "226780", "633936", "226932",
        "226995", "226661", "226690", "180719", "226993", "226712", "897082", "135185",
        "226762", "180717", "226971", "226704", "872843", "226875", "226662", "180716",
        "226820", "892476", "893404", "226876", "633937", "226900", "897083", "881813",
        "135181", "383779", "226802", "897816", "180720", "173902", "226840", "226889",
        "890060",'835296'
    ]
    
    # Afficher le tableau des écarts
    st.subheader("Tableau des écarts")

    # --- Colonnes pour les 4 premiers filtres ---
    cols = st.columns(5)

    # --- Options de filtrage ---
    options_1 = ["Toutes", "Positives", "Négatives", "Zéro"]
    options_2 = ["Tous", "Oui", "Non"]
    options_3 = ["Toutes","<1","1-5","5-10","10-15","15-20","20+"]
    options_4 = ["Toutes", "Positives", "Zéro"]
    options_5 = ["Toutes", "Positives", "Négatives"]

    filtres = {
        "WMS_Stock": {"col": cols[1], "options": options_4, "type": "numeric"},
        "MMS_Stock": {"col": cols[0], "options": options_1, "type": "numeric"},
        "Au_Kg": {"col": cols[2], "options": options_2, "type": "bool"},
        "Difference_MMS-WMS_Valeur": {"col": cols[3], "options": options_3, "type": "range", "df_col": "Difference_MMS-WMS"},
        "Difference_MMS-WMS_+/-": {"col": cols[4], "options": options_5, "type": "numeric", "df_col": "Difference_MMS-WMS"},
        }


    # --- Initialiser session_state pour chaque filtre ---
    for key, filt in filtres.items():
        state_key = f"filter_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = filt["options"][0]

    # --- Bouton Réinitialiser les 4 premiers filtres ---
    def reset_filters():
        for key in filtres.keys():
            st.session_state[f"filter_{key}"] = filtres[key]["options"][0]

    
    # --- Selectboxes pour les 4 premiers filtres (utiliser key pour forcer la lecture depuis session_state) ---
    for key, filt in filtres.items():
        state_key = f"filter_{key}"
        filt["value"] = filt["col"].selectbox(
            key.replace("_", " "),
            filt["options"],
            index=filt["options"].index(st.session_state[state_key]),
            key=state_key  # clé obligatoire pour que la réinitialisation fonctionne
        )

    cols[0].button("Réinitialiser les filtres", on_click=reset_filters)

    # --- Filtre Deja_Present sous le bouton ---
    deja_present_options = ["Tous", "Oui", "Non"]
    if "filter_Deja_Present" not in st.session_state:
        st.session_state["filter_Deja_Present"] = deja_present_options[0]

    filter_choice_6 = cols[0].selectbox(
        "Deja_Present",
        deja_present_options,
        index=deja_present_options.index(st.session_state["filter_Deja_Present"]),
        key="filter_Deja_Present"
    )

    # --- Appliquer les filtres ---
    df_filtered = df_ecart_stock_last.copy()

    for key, filt in filtres.items():
        val = st.session_state[f"filter_{key}"]
        df_col = filt.get("df_col", key)  # si df_col n’existe pas, on garde key

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
                # Tout ce qui n'est pas True devient Non
                df_filtered = df_filtered[df_filtered[df_col] != True]

        elif filt["type"] == "range":
            ranges = {
                "<1": (0,1),
                "1-5": (1, 5),
                "5-10": (5, 10),
                "10-15": (10, 15),
                "15-20": (15, 20),
                "20+": (20, float("inf"))
            }
            if val in ranges:
                low, high = ranges[val]
                df_filtered = df_filtered[(df_filtered[df_col].abs() >= low) & (df_filtered[df_col].abs() < high)]

    # --- Filtre Deja_Present ---
    map_bool = {"Tous": None, "Oui": True, "Non": False}
    val_bool = map_bool[st.session_state["filter_Deja_Present"]]
    if val_bool is not None:
        df_filtered = df_filtered[df_filtered["Deja_Present"].astype(bool) == val_bool]

    # --- Affichage ---
    # On enlève les MGB présents dans la liste de consignes
    df_affiche = df_filtered[~df_filtered["MGB_6"].astype(str).isin(MGB_consigne)].copy()

    df_affiche = df_affiche.reindex(
        df_affiche["Difference_MMS-WMS"].abs().sort_values(ascending=False).index
    )

    # Préparer df_affiche avec la différence précédente
    df_prev_diff = df_ecart_stock_prev[['MGB_6', 'Difference_MMS-WMS']].rename(
        columns={'Difference_MMS-WMS': 'Difference_prev'}
    )
    df_affiche = df_affiche.merge(df_prev_diff, on='MGB_6', how='left')

    # Fonction de style pour mettre en orange si différence a changé
    def highlight_diff_change(row):
        if pd.notna(row['Difference_prev']) and row['Difference_MMS-WMS'] != row['Difference_prev']:
            return ['background-color: #FFA500'] * len(row)
        else:
            return [''] * len(row)

    # Affichage final avec formatage et coloration
    st.dataframe(
        df_affiche.style
        .apply(highlight_diff_change, axis=1)
        .format({
            '€_Unitaire': "{:.2f}",
            'Valeur_Difference': "{:.2f}"
        })
    )

    col1, col2 = st.columns(2)
    # compter le nombre de ligne :
    col1.subheader(f"Nombre de lignes (hors consignes): {len(df_affiche)}")

    # valeur total :
    total_value = df_affiche['Valeur_Difference'].sum()
    col2.subheader(f"Valeur total des écarts : {total_value:.2f} €")

    # separation :
    st.divider()

    # Menu déroulant MGB_6
    col1, col2 = st.columns(2)
    mgb_list = df_affiche['MGB_6'].dropna().unique() if not df_affiche.empty else []
    mgb_selected = col1.selectbox("Choisir un MGB", mgb_list)

    # Filtrer les DataFrames
    stock_info = df_ecart_stock_last[df_ecart_stock_last['MGB_6'] == mgb_selected]
    inventaire_info = df_inventaire[df_inventaire['MGB_6'] == mgb_selected]
    mvt_stock_info = df_mvt_stock[df_mvt_stock['MGB_6'] == mgb_selected]
    reception_info = df_reception[df_reception['MGB_6'] == mgb_selected]
    sorties_info = df_sorties[df_sorties['MGB_6'] == mgb_selected]

    # Calcul des totaux
    totaux_stock = ajouter_totaux(stock_info, ["MMS_Stock","WMS_Stock","Difference_MMS-WMS","Valeur_Difference"])
    totaux_inventaire = ajouter_totaux(inventaire_info, ["Inventaire_Final_Quantity"])
    totaux_mvt_stock = ajouter_totaux(mvt_stock_info, ["Qty_Mouvement"])
    totaux_reception = ajouter_totaux(reception_info, ["Qty_Reception"])
    totaux_sorties = ajouter_totaux(sorties_info, ["Qty/Article/Poids"])

    stock_theorique = (
        totaux_inventaire.get('Inventaire_Final_Quantity', 0)
        + totaux_mvt_stock.get('Qty_Mouvement', 0)
        + totaux_reception.get('Qty_Reception', 0)
        - totaux_sorties.get('Qty/Article/Poids', 0)
    )

    # Affichage des métriques
    st.subheader(f"Infos pour : {mgb_selected} - {stock_info.iloc[0]['Désignation'] if not stock_info.empty else ''}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("MMS Stock", totaux_stock.get("MMS_Stock", 0))
    col2.metric("WMS Stock", totaux_stock.get("WMS_Stock", 0))
    col4.metric("Difference MMS-WMS", totaux_stock.get("Difference_MMS-WMS", 0))
    col5.metric("Valeur Difference €", totaux_stock.get("Valeur_Difference", 0),"€")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Inventaire", totaux_inventaire.get("Inventaire_Final_Quantity", 0))
    col2.metric("Mouvements", totaux_mvt_stock.get("Qty_Mouvement", 0))
    col3.metric("Réceptions", totaux_reception.get("Qty_Reception", 0))
    col4.metric("Sorties", totaux_sorties.get("Qty/Article/Poids", 0))
    col5.metric("Stock théorique", round(stock_theorique, 2))

    # Affichage des tableaux détaillés
    st.subheader("Tableau Inventaire")
    st.dataframe(inventaire_info, use_container_width=True)

    st.subheader("Tableau des mouvements de stock")
    st.dataframe(mvt_stock_info.style.apply(color_rows, axis=1), use_container_width=True)

    st.subheader("Tableau des réceptions")
    st.dataframe(reception_info, use_container_width=True)

    st.subheader("Tableau des sorties")
    st.dataframe(sorties_info, use_container_width=True)

    # separation :
    st.divider()


    # --- Lecture du chemin du dernier fichier parquet ---
    render_cache_dir = Path("/opt/render/project/src/render_cache")
    file_last_txt = render_cache_dir / "file_last.txt"

    # --- Debug : afficher le contenu des dossiers ---
    cache_dir = Path("/opt/render/project/src/render_cache")
    st.write("Fichiers dans render_cache :", list(cache_dir.glob("*")))

    tmp_dir = Path("/tmp")
    st.write("Fichiers dans /tmp :", list(tmp_dir.glob("*")))

    file_last = None
    if file_last_txt.exists():
        with open(file_last_txt, "r", encoding="utf-8") as f:
            file_last = f.read().strip()

    if not file_last:
        st.warning("Aucun fichier d'écart stock récent trouvé (file_last non défini).")
        st.stop()

    # --- Chargement du dernier parquet ---
    parquet_path = Path(file_last).with_suffix(".parquet")
    if not parquet_path.exists():
        st.warning(f"Fichier parquet introuvable : {parquet_path}")
        st.stop()

    # --- Initialisation de la session Streamlit ---
    if "df_comments" not in st.session_state:
        df_existing = pd.read_parquet(parquet_path)

        # S'assurer qu'on a bien la colonne MGB_6
        if "MGB_6" not in df_existing.columns:
            if "Article number (MGB)" in df_existing.columns:
                df_existing["MGB_6"] = df_existing["Article number (MGB)"].astype(str)
                df_existing = df_existing.drop(columns=["Article number (MGB)"])
            else:
                df_existing["MGB_6"] = ""

        # Ajouter les colonnes de commentaire si elles n'existent pas
        for col in ["Commentaire", "Date_Dernier_Commentaire"]:
            if col not in df_existing.columns:
                df_existing[col] = ""

        st.session_state.df_comments = df_existing.copy()

           
        # --- Injection automatique des MGB de consigne dans df_comments ---

    # Copie du DataFrame de commentaires existant
    df_comments = st.session_state.df_comments.copy()
    df_comments["MGB_6"] = df_comments["MGB_6"].astype(str)


    # On garde uniquement les MGB de consigne présents dans df_affiche
    df_consigne = df_ecart_stock_last[df_ecart_stock_last["MGB_6"].isin(MGB_consigne)].copy()

    # Colonnes nécessaires
    for col in ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"]:
        if col not in df_consigne.columns:
            df_consigne[col] = ""

    # Définir les valeurs de consigne
    today = datetime.today().strftime("%d-%m-%Y")
    df_consigne["Commentaire"] = "Consigne"
    df_consigne["Date_Dernier_Commentaire"] = today
    df_consigne["Choix_traitement"] = "XX"

    # --- Appliquer ou ajouter les lignes correspondantes ---
    for _, row in df_consigne.iterrows():
        mgb = row["MGB_6"]

        # Si le MGB existe déjà dans df_comments → mise à jour
        if mgb in df_comments["MGB_6"].values:
            df_comments.loc[df_comments["MGB_6"] == mgb, 
                ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"]] = [
                    "Consigne", today, "XX"
                ]
        # Sinon → ajout d'une nouvelle ligne
        else:
            df_comments = pd.concat([df_comments, pd.DataFrame([row])], ignore_index=True)

    # Sauvegarde et mise à jour de la session
    st.session_state.df_comments = df_comments
    df_comments.to_parquet(parquet_path, index=False)

    # --- Zone d’ajout/modification de commentaire ---
    mgb_text = f"{mgb_selected} - {stock_info.iloc[0]['Désignation'] if not stock_info.empty else ''}"

    st.markdown(f"""
    <h1 style='font-size:2.5em'>
    Ajouter un commentaire à la ligne :<br>{mgb_text}
    </h1>
    """, unsafe_allow_html=True)

    df_temp_last = st.session_state.df_comments

    # --- Initialisation sécurisée de df_comments ---
    if "df_comments" not in st.session_state:
        st.session_state.df_comments = pd.DataFrame(columns=[
            "MGB_6", "Commentaire", "Date_Dernier_Commentaire", "Choix_traitement", "IDL_auto"
        ])

    # --- Attribution automatique IDL pour les quantités < 1 (valeur absolue) ---
    df_auto_idl = df_ecart_stock_last[df_ecart_stock_last["Difference_MMS-WMS"].abs() < 1].copy()
    today_str = datetime.today().strftime("%d-%m-%Y")

    for _, row in df_auto_idl.iterrows():
        mgb = str(row["MGB_6"])
        if mgb in st.session_state.df_comments["MGB_6"].values:
            st.session_state.df_comments.loc[
                st.session_state.df_comments["MGB_6"] == mgb,
                ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement", "IDL_auto"]
            ] = ["Régul à faire quantité inferieur à 1", today_str, "IDL", True]
        else:
            new_row = {
                "MGB_6": mgb,
                "Commentaire": "Régul à faire quantité inferieur à 1",
                "Date_Dernier_Commentaire": today_str,
                "Choix_traitement": "IDL",
                "IDL_auto": True
            }
            st.session_state.df_comments = pd.concat(
                [st.session_state.df_comments, pd.DataFrame([new_row])], ignore_index=True
            )

    # Pour les autres lignes, s'assurer que IDL_auto existe
    if "IDL_auto" not in st.session_state.df_comments.columns:
        st.session_state.df_comments["IDL_auto"] = False


    if mgb_selected not in df_temp_last["MGB_6"].values:
        st.warning(f"MGB {mgb_selected} non trouvé dans le fichier parquet.")
        st.stop()

    index = df_temp_last.index[df_temp_last["MGB_6"] == mgb_selected][0]
    commentaire_existant = df_temp_last.at[index, "Commentaire"]
    
    # Si la colonne n’existe pas encore, on la crée
    if "Choix_traitement" not in df_temp_last.columns:
        df_temp_last["Choix_traitement"] = ""
    
    choix_existant = df_temp_last.at[index, "Choix_traitement"]

    # --- Réinitialisation automatique du champ texte quand on change de MGB ---
    if "last_mgb" not in st.session_state:
        st.session_state.last_mgb = mgb_selected

    if mgb_selected != st.session_state.last_mgb:
        st.session_state[f"commentaire_{mgb_selected}"] = ""  # reset texte
        st.session_state[f"choix_{mgb_selected}"] = None      # reset choix
        st.session_state.last_mgb = mgb_selected

    # --- Zone d’édition du commentaire ---

    if pd.isna(commentaire_existant) or commentaire_existant == "":
        commentaire = st.text_area("Écrire votre commentaire :")
        choix_source = st.radio(
            "Sélectionner le chargé du traitement (obligatoire) :",
            options=["METRO", "IDL"],
            index=None,
            key=f"choix_{mgb_selected}",
        )
        if st.button("Ajouter le commentaire"):
            if not choix_source:
                st.error("Vous devez sélectionner METRO ou IDL avant de valider.")
                st.stop()
            today = datetime.today().strftime("%d-%m-%Y")
            df_temp_last.at[index, "Commentaire"] = commentaire
            df_temp_last.at[index, "Date_Dernier_Commentaire"] = today
            df_temp_last.at[index, "Choix_traitement"] = choix_source
            st.session_state.df_comments = df_temp_last
            df_temp_last.to_parquet(parquet_path, index=False)
            git_commit_push(parquet_path, f"MAJ commentaires pour MGB {mgb_selected}")
            st.success(f"Commentaire ajouté pour {mgb_selected} ({today}) !")
    else:
        st.write(f"Commentaire actuel : {commentaire_existant}")
        st.write(f"Suivi actuel : {choix_existant if choix_existant else 'Non défini'}")
        modifier = st.radio("Voulez-vous changer ce commentaire ?", ("Non", "Oui"))
        if modifier == "Oui":
            commentaire = st.text_area("Écrire votre nouveau commentaire :", commentaire_existant)
            choix_source = st.radio(
            "Sélectionner le chargé du traitement (obligatoire) :",
                options=["METRO", "IDL"],
                index=["METRO", "IDL"].index(choix_existant) if choix_existant in ["METRO", "IDL"] else None,
                key=f"choix_{mgb_selected}",
            )
            if st.button("Mettre à jour le commentaire"):
                if not choix_source:
                    st.error("Vous devez sélectionner METRO ou IDL avant de valider.")
                    st.stop()
                today = datetime.today().strftime("%d-%m-%Y")
                df_temp_last.at[index, "Commentaire"] = commentaire
                df_temp_last.at[index, "Date_Dernier_Commentaire"] = today
                df_temp_last.at[index, "Choix_traitement"] = choix_source
                st.session_state.df_comments = df_temp_last
                df_temp_last.to_parquet(parquet_path, index=False)
                git_commit_push(parquet_path, f"MAJ commentaires pour MGB {mgb_selected}")
                st.success(f"Commentaire mis à jour pour {mgb_selected} ({today}) !")

   # --------------------------
    # Classe PDF personnalisée
    # --------------------------
    class PDF(FPDF):
        def __init__(self, headers, col_widths):
            super().__init__(orientation="L", unit="mm", format="A4")
            self.headers = headers
            self.col_widths = col_widths
            self.first_page = True

        def header(self):
            if self.first_page:
                return
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, f"Rapport Ecart {datetime.today().strftime('%d/%m/%Y')}", ln=True, align="C")
            self.ln(5)
            self.set_font("Arial", "B", 10)
            for i, col in enumerate(self.headers):
                self.cell(self.col_widths[i], 10, col, border=1, align="C")
            self.ln()

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    # -------------------------
    # ----Génération du PDF----
    # -------------------------
    
    if st.button("Générer le PDF du rapport"):
        df_for_pdf = st.session_state.df_comments.copy()
        df_for_pdf = st.session_state.df_comments[
            st.session_state.df_comments["Date_Dernier_Commentaire"].notna() &
            (st.session_state.df_comments["Date_Dernier_Commentaire"] != "")
        ].fillna("")

        # Fusion avec df_sorties pour ajouter la colonne 'Cellule'
        if 'df_sorties' in locals():
            # S’assurer qu’il y a une seule ligne par MGB_6
            df_cellules = (
                df_sorties[['MGB_6', 'Cellule']]
                .dropna(subset=['MGB_6'])
                .drop_duplicates(subset=['MGB_6'], keep='first')
            )

            df_for_pdf = df_for_pdf.merge(
                df_cellules,
                on='MGB_6',
                how='left'
            )
        else:
            st.warning("df_sorties non trouvé, la colonne 'Cellule' ne sera pas ajoutée.")
            df_for_pdf["Cellule"] = ""
        
            # Convertir la date en format réel pour tri
        df_for_pdf["Date_Dernier_Commentaire_dt"] = pd.to_datetime(
            df_for_pdf["Date_Dernier_Commentaire"], format="%d-%m-%Y", errors="coerce"
        )

        # Ordonner les lignes :
        df_idl_auto = df_for_pdf[df_for_pdf.get("IDL_auto", False) == True]
        df_idl_normales = df_for_pdf[(df_for_pdf["Choix_traitement"] == "IDL") & (df_for_pdf.get("IDL_auto", False) != True)]
        # 1️ METRO par date croissante
        # 2️ IDL par date croissante
        df_for_pdf = pd.concat([
            df_for_pdf[df_for_pdf["Choix_traitement"] == "METRO"],
            df_idl_normales,
            df_idl_auto,  
            df_for_pdf[df_for_pdf["Choix_traitement"] == ""],
            df_for_pdf[df_for_pdf["Choix_traitement"] == "XX"]
        ])

        col_widths = [15, 70, 15, 15, 15, 15, 20, 15, 105]
        headers = ["MGB_6", "Désignation","Cellule","MMS","WMS", "Diff", "Date", "Suivi", "Commentaire"]

        pdf = PDF(headers, col_widths)
        pdf.set_auto_page_break(auto=True, margin=20)

        # --- Préparation des données pour la synthèse ---

        # Exclure les MGB de consignes
        df_for_pdf_no_consigne = df_for_pdf[~df_for_pdf["MGB_6"].astype(str).isin(MGB_consigne)].copy()

        # Total (hors consignes)
        total_lignes = len(df_temp_last)-len(df_consigne)
        
        # Lignes METRO
        df_metro = df_for_pdf_no_consigne[df_for_pdf_no_consigne["Choix_traitement"] == "METRO"]
        nb_metro = len(df_metro)

        # Lignes IDL
        df_idl = df_for_pdf_no_consigne[df_for_pdf_no_consigne["Choix_traitement"] == "IDL"]
        nb_idl = len(df_idl)

        # Lignes non traitées (non présentes dans df_for_pdf car pas de commentaire)      
        nb_non = total_lignes-(nb_metro+nb_idl)

        # --- 1ere page = Page de synthèse ---
        x_offset = 50
        x_offset_1 = 40
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Tableau de synthèse", ln=True, align="C")
        pdf.ln(6)

        pdf.set_font("Arial", "", 10)

        pdf.ln(6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(x_offset_1)
        pdf.cell(0, 8, "Synthèse des Ecarts", ln=True)
        pdf.set_font("Arial", "", 10)

        synthese_data = [            
            ("Lignes METRO", str(nb_metro)),
            ("Lignes IDL", str(nb_idl)),
            ("Lignes en attente d'affectations", str(nb_non)),
            ("Total écarts (hors consignes)", str(total_lignes)),
        ]

        col_widths_syn = [90, 40]
        pdf.set_fill_color(220, 220, 220)
        pdf.set_x(x_offset)
        pdf.cell(col_widths_syn[0], 8, "Catégorie", border=1, align="C", fill=True)
        pdf.cell(col_widths_syn[1], 8, "Nombre", border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        
        for row in synthese_data:
            pdf.set_x(x_offset)
            pdf.cell(col_widths_syn[0], 8, row[0], border=1)
            pdf.cell(col_widths_syn[1], 8, row[1], border=1, align="C")
            pdf.ln()

        pdf.set_font("Arial", "I", 9)
        pdf.set_x(x_offset)
        pdf.cell(0, 6, "Les lignes non affectées ne figurent pas dans le rapport détaillé.", ln=True)

        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(x_offset_1)
        pdf.cell(0, 8, "Synthèse des lignes traitées", ln=True)
        pdf.set_font("Arial", "", 10)

        # --- Tableau : lignes traitées par type ---
        # Les lignes traitées = présentes dans df_ecart_stock_prev mais plus dans df_ecart_stock_last

        mgb_prev = set(df_ecart_stock_prev["MGB_6"].astype(str))
        mgb_last = set(df_ecart_stock_last["MGB_6"].astype(str))
        mgb_traite = mgb_prev - mgb_last

        nb_total_traite = len(mgb_traite)

        synthese_traite = [
            ("Total lignes traitées", str(nb_total_traite))
        ]

        # Affichage du tableau
        col_widths_syn2 = [90, 40]
        pdf.set_fill_color(220, 220, 220)
        pdf.set_x(x_offset)
        pdf.cell(col_widths_syn2[0], 8, "Catégorie", border=1, align="C", fill=True)
        pdf.cell(col_widths_syn2[1], 8, "Nombre", border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for row in synthese_traite:
            pdf.set_x(x_offset)
            pdf.cell(col_widths_syn2[0], 8, row[0], border=1)
            pdf.cell(col_widths_syn2[1], 8, row[1], border=1, align="C")
            pdf.ln()

        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(x_offset_1)
        pdf.cell(0, 8, "Synthèse des retards de traitement", ln=True)
        pdf.set_font("Arial", "", 10)

        # --- Tableau : lignes affectées depuis plus de 3, 6 et 10 jours ---
        today_dt = datetime.today()

        df_retard = df_for_pdf[
            (~df_for_pdf["MGB_6"].isin(MGB_consigne)) &
            (df_for_pdf["Date_Dernier_Commentaire_dt"].notna())
        ]

        # Retards >3, >6, >10 jours séparés par type METRO/IDL
        retard_data = []
        for days in [3, 6, 10]:
            df_days = df_retard[(today_dt - df_retard["Date_Dernier_Commentaire_dt"]).dt.days > days]
            nb_met = len(df_days[df_days["Choix_traitement"] == "METRO"])
            nb_idl = len(df_days[df_days["Choix_traitement"] == "IDL"])
            retard_data.append((f"> {days} jours", str(nb_met), str(nb_idl)))

        # Affichage du tableau
        col_widths_retard = [90, 40, 40]  # Délai | METRO | IDL

        # En-tête
        pdf.set_fill_color(220, 220, 220)
        pdf.set_x(x_offset)
        pdf.cell(col_widths_retard[0], 8, "Délai depuis dernier commentaire", border=1, align="C", fill=True)
        pdf.cell(col_widths_retard[1], 8, "METRO", border=1, align="C", fill=True)
        pdf.cell(col_widths_retard[2], 8, "IDL", border=1, align="C", fill=True)
        pdf.ln()

        # Contenu
        pdf.set_font("Arial", "", 9)
        for row in retard_data:
            pdf.set_x(x_offset)
            pdf.cell(col_widths_retard[0], 8, row[0], border=1)
            pdf.cell(col_widths_retard[1], 8, row[1], border=1, align="C")
            pdf.cell(col_widths_retard[2], 8, row[2], border=1, align="C")
            pdf.ln()

        pdf.first_page = False  # Les pages suivantes auront les en-têtes

        # Nouvelle page pour le détail complet
        pdf.add_page()
        pdf.set_font("Arial", "", 9)

        for _, row in df_for_pdf.iterrows():
            choix = row.get("Choix_traitement", "")
            if row.get("IDL_auto", False):
                pdf.set_fill_color(216, 191, 216)  # Violet clair pour IDL auto
            elif choix == "METRO":
                pdf.set_fill_color(255, 255, 153)  # Jaune clair
            elif choix == "IDL":
                pdf.set_fill_color(173, 216, 230)  # Bleu clair
            elif choix == "XX":
                pdf.set_fill_color(255, 200, 200)  # Rouge clair (consignes)
            else:
                pdf.set_fill_color(255, 255, 255)  # Blanc

            # ligne du tableau
            pdf.cell(col_widths[0], 6, str(row["MGB_6"]), border=1, align="C", fill=True)
            pdf.cell(col_widths[1], 6, str(row["Désignation"]), border=1, fill=True)
            pdf.cell(col_widths[2], 6, str(row.get("Cellule", "")), border=1, align="C", fill=True)
            pdf.cell(col_widths[3], 6, str(row["MMS_Stock"]), border=1, fill=True)
            pdf.cell(col_widths[4], 6, str(row["WMS_Stock"]), border=1, fill=True)
            pdf.cell(col_widths[5], 6, str(round(row.get("Difference_MMS-WMS", 0), 2)), border=1, align="C", fill=True)
            pdf.cell(col_widths[6], 6, str(row["Date_Dernier_Commentaire"]), border=1, align="C", fill=True)
            pdf.cell(col_widths[7], 6, str(choix), border=1, align="C", fill=True)
            
            x_before = pdf.get_x()
            y_before = pdf.get_y()
            pdf.multi_cell(col_widths[8], 6, str(row["Commentaire"]), border=1, fill=True)
            y_after = pdf.get_y()
            pdf.set_xy(x_before + col_widths[8], y_before)
            pdf.ln(max(6, y_after - y_before))

        pdf_bytes = pdf.output(dest="S").encode("latin-1")

        st.download_button(
            label="Télécharger le PDF",
            data=pdf_bytes,
            file_name=f"rapport_ecart_{datetime.today().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf"
        )

        st.success("PDF généré et parquet mis à jour avec les commentaires !")

def tab_Detrompeurs():
    st.title("Détrompeurs")

# Configuration des onglets
tabs = {
    "Accueil": tab_home,
    "QR Codes et Code Barre": tab_QR_Codes,
    "Analyse Stock": Analyse_stock,
    "Détrompeurs": tab_Detrompeurs
}

def main():
    st.sidebar.image("https://raw.githubusercontent.com/IDLAurelienMartin/Data_IDL/main/Images/logo_IDL.jpg")

    st.sidebar.header("Navigation")
    selected_tab = st.sidebar.radio("", list(tabs.keys()))
    tabs[selected_tab]()

    st.sidebar.image("https://raw.githubusercontent.com/IDLAurelienMartin/Data_IDL/main/Images/Logo_Metro.webp")

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



