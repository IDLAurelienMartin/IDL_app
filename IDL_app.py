from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader
import qrcode
from barcode.ean import EAN13, EAN8
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
from git import Repo
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import requests
import fitz
from PyPDF2 import PdfReader, PdfWriter
import sys
from scripts.prepare_data import update_emplacement, ajouter_totaux, color_rows 
import numpy as np
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import base64

# --- Dossier cache local sur Render ---
# Render place les fichiers persistants dans le dossier /opt/render/project/src/render_cache
RENDER_CACHE_DIR = Path("/opt/render/project/src/render_cache")
LOCAL_CACHE_DIR = Path("Cache")
GIT_REPO_DIR = Path("/opt/render/project/src")  # ton repo local

# On crée aussi le dossier Cache pour éviter les erreurs
LOCAL_CACHE_DIR.mkdir(exist_ok=True)
RENDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# --- Dossiers ---
RENDER_CACHE_DIR = Path("/opt/render/project/src/render_cache")  # lecture seule
LOCAL_CACHE_DIR = Path("Cache")  # tentative locale
LOCAL_CACHE_DIR.mkdir(exist_ok=True)

# --- GitHub RAW pour Data_IDL ---
GITHUB_OWNER = "IDLAurelienMartin"
GITHUB_REPO = "Data_IDL"
GITHUB_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/Cache/"

# --- Chargement police compatible Render ---

FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"

def load_font(font_size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), font_size)
    except Exception as e:
        st.error(f"Erreur chargement police : {e}")
        return ImageFont.load_default()

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

                font = load_font(font_size)

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

def load_parquet(file_name):
    """
    Charge un parquet en suivant cet ordre :
    1) Render cache
    2) Local cache interne (Cache/)
    3) GitHub RAW (Data_IDL)
    """
    # 1) Render cache
    render_path = RENDER_CACHE_DIR / file_name
    if render_path.exists():
        return pd.read_parquet(render_path)
    
    # 2) Local cache
    local_path = LOCAL_CACHE_DIR / file_name
    if local_path.exists():
        return pd.read_parquet(local_path)
    
    # 3) GitHub RAW fallback
    github_url = RAW_BASE + file_name
    try:
        r = requests.get(github_url)
        r.raise_for_status()
        df = pd.read_parquet(BytesIO(r.content))
        return df
    except Exception as e:
        st.error(f"Impossible de charger {file_name} depuis GitHub : {e}")
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

    # ---------- utilitaire cache wrapper ----------
    @st.cache_data(ttl=300)
    def cached_parquet_load(name):
        # wrapper autour de ton load_parquet existant (doit exister dans le scope global)
        return load_parquet(name)

    # ---------- charger fichiers (mis en cache) ----------
    df_article_euros = cached_parquet_load("article_euros.parquet")
    df_ecart_stock_prev = cached_parquet_load("ecart_stock_prev.parquet")
    df_ecart_stock_last = cached_parquet_load("ecart_stock_last.parquet")
    df_reception = cached_parquet_load("reception.parquet")
    df_sorties = cached_parquet_load("sorties.parquet")
    df_inventaire = cached_parquet_load("inventaire.parquet")
    df_mvt_stock = cached_parquet_load("mvt_stock.parquet")

    # vérification minimale
    if df_article_euros.empty or df_ecart_stock_last.empty:
        st.warning("Fichiers indispensables manquants (article_euros ou ecart_stock_last).")
        st.stop()

    # ---------- harmonisation MGB_6 (vectorisée) ----------
    all_dfs = [
        df_article_euros, df_inventaire, df_mvt_stock, df_reception,
        df_sorties, df_ecart_stock_prev, df_ecart_stock_last
    ]
    for df in all_dfs:
        if "MGB_6" in df.columns:
            df["MGB_6"] = df["MGB_6"].astype(str).str.replace(" ", "", regex=False).str.strip()

    st.title("Analyse des écarts de stock")

    # ---------- Prétraiter df_mvt_stock une seule fois ----------
    if not df_mvt_stock.empty:
        if "df_mvt_stock_processed" not in st.session_state:
            # use apply once then cache in session state
            try:
                df_mvt_stock_proc = df_mvt_stock.copy()
                df_mvt_stock_proc["Emplacement"] = df_mvt_stock_proc.apply(update_emplacement, axis=1)
                df_mvt_stock_proc = df_mvt_stock_proc.drop(columns=["prefix_emplacement"], errors="ignore")
                st.session_state.df_mvt_stock_processed = df_mvt_stock_proc
            except Exception:
                st.session_state.df_mvt_stock_processed = df_mvt_stock.copy()
        df_mvt_stock = st.session_state.df_mvt_stock_processed

    # ---------- Liste consignes (unchanged) ----------
    MGB_consigne = {
        "226796","890080","179986","885177","890050","226923","834397","890070",
        "886655","226725","226819","226681","897881","897885","897890","897698",
        "226658","226783","896634","226654","226814","226830","173907","897814",
        "226781","897704","886648","881810","226864","226780","633936","226932",
        "226995","226661","226690","180719","226993","226712","897082","135185",
        "226762","180717","226971","226704","872843","226875","226662","180716",
        "226820","892476","893404","226876","633937","226900","897083","881813",
        "135181","383779","226802","897816","180720","173902","226840","226889",
        "890060","835296"
    }

    # ---------- UI : filtres (identiques mais gérés via masque combiné) ----------
    st.subheader("Tableau des écarts")
    cols = st.columns(5)

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

    # init session state for filters
    for key, filt in filtres.items():
        sk = f"filter_{key}"
        if sk not in st.session_state:
            st.session_state[sk] = filt["options"][0]

    def reset_filters():
        for k in filtres.keys():
            st.session_state[f"filter_{k}"] = filtres[k]["options"][0]

    for key, filt in filtres.items():
        sk = f"filter_{key}"
        filt["value"] = filt["col"].selectbox(
            key.replace("_", " "),
            filt["options"],
            index=filt["options"].index(st.session_state[sk]),
            key=sk
        )
    cols[0].button("Réinitialiser les filtres", on_click=reset_filters)

    # Deja_Present selectbox
    deja_present_options = ["Tous", "Oui", "Non"]
    if "filter_Deja_Present" not in st.session_state:
        st.session_state["filter_Deja_Present"] = deja_present_options[0]

    filter_choice_6 = cols[0].selectbox(
        "Deja_Present",
        deja_present_options,
        index=deja_present_options.index(st.session_state["filter_Deja_Present"]),
        key="filter_Deja_Present"
    )

    # ---------- construire masque combiné (une passe) ----------
    df_src = df_ecart_stock_last
    mask = pd.Series(True, index=df_src.index)

    for key, filt in filtres.items():
        val = st.session_state[f"filter_{key}"]
        df_col = filt.get("df_col", key)
        if filt["type"] == "numeric":
            if val == "Positives":
                mask &= df_src[df_col] > 0
            elif val == "Négatives":
                mask &= df_src[df_col] < 0
            elif val == "Zéro":
                mask &= df_src[df_col] == 0
        elif filt["type"] == "bool":
            if val == "Oui":
                mask &= df_src[df_col] == True
            elif val == "Non":
                mask &= df_src[df_col] != True
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
                mask &= (df_src[df_col].abs() >= low) & (df_src[df_col].abs() < high)

    map_bool = {"Tous": None, "Oui": True, "Non": False}
    vb = map_bool[st.session_state["filter_Deja_Present"]]
    if vb is not None:
        mask &= df_src["Deja_Present"].astype(bool) == vb

    df_filtered = df_src[mask].copy()

    # ---------- enlever les consignes ----------
    df_affiche = df_filtered[~df_filtered["MGB_6"].astype(str).isin(MGB_consigne)].copy()

    # ---------- tri des tableaux : par date puis heure ----------
    date_col = "Date" if "Date" in df_affiche.columns else None
    heure_col = "Heure" if "Heure" in df_affiche.columns else None

    if date_col:
        # Conversion au format datetime si nécessaire
        df_affiche[date_col] = pd.to_datetime(df_affiche[date_col], errors="coerce")
        
        if heure_col:
            # Si heure dispo, on combine date + heure pour trier correctement
            df_affiche[heure_col] = pd.to_datetime(df_affiche[heure_col], errors="coerce").dt.time
            df_affiche = df_affiche.sort_values(
                by=[date_col, heure_col],
                ascending=[False, False]  # du plus récent au plus ancien
            )
        else:
            # Sinon, on trie juste par date
            df_affiche = df_affiche.sort_values(by=date_col, ascending=False)
    else:
        # fallback previous behavior
        df_affiche = df_affiche.reindex(
            df_affiche["Difference_MMS-WMS"].abs().sort_values(ascending=False).index
        )


    # ---------- merger difference précédente (batch) ----------
    if not df_ecart_stock_prev.empty:
        df_prev_diff = df_ecart_stock_prev[["MGB_6", "Difference_MMS-WMS"]].rename(columns={"Difference_MMS-WMS":"Difference_prev"})
        # merge left
        df_affiche = df_affiche.merge(df_prev_diff, on="MGB_6", how="left")
    else:
        df_affiche["Difference_prev"] = np.nan

    # ---------- style function (kept) ----------
    def highlight_diff_change(row):
        if pd.notna(row.get("Difference_prev")) and row.get("Difference_MMS-WMS") != row.get("Difference_prev"):
            return ['background-color: #FFA500'] * len(row)
        else:
            return [''] * len(row)

    # ---------- affichage principal ----------
    st.dataframe(
        df_affiche.style
            .apply(highlight_diff_change, axis=1)
            .format({'€_Unitaire': "{:.2f}", 'Valeur_Difference': "{:.2f}"})
    )

    col1, col2 = st.columns(2)
    col1.subheader(f"Nombre de lignes (hors consignes): {len(df_affiche)}")
    total_value = df_affiche['Valeur_Difference'].sum() if "Valeur_Difference" in df_affiche.columns else 0
    col2.subheader(f"Valeur total des écarts : {total_value:.2f} €")

    st.divider()

    # ---------- sélection MGB pour détails ----------
    col1, col2 = st.columns(2)
    mgb_list = df_affiche['MGB_6'].dropna().unique() if not df_affiche.empty else []
    if len(mgb_list) == 0:
        st.info("Aucune ligne à afficher après filtrage.")
        st.stop()

    mgb_selected = col1.selectbox("Choisir un MGB", mgb_list)

    # filtre détaillé (très rapide car index selection)
    stock_info = df_ecart_stock_last[df_ecart_stock_last['MGB_6'] == mgb_selected].copy()
    inventaire_info = df_inventaire[df_inventaire['MGB_6'] == mgb_selected].copy()
    mvt_stock_info = df_mvt_stock[df_mvt_stock['MGB_6'] == mgb_selected].copy()
    reception_info = df_reception[df_reception['MGB_6'] == mgb_selected].copy()
    sorties_info = df_sorties[df_sorties['MGB_6'] == mgb_selected].copy()

    # tri des tableaux détaillés par Date_Heure si existant
    def sort_if_date(df_):
        for c in ["Date", "Heure"]:
            if c in df_.columns:
                df_[c] = pd.to_datetime(df_[c], errors="coerce")
                return df_.sort_values(by=[c], ascending=True)
        return df_
    inventaire_info = sort_if_date(inventaire_info)
    mvt_stock_info = sort_if_date(mvt_stock_info)
    reception_info = sort_if_date(reception_info)
    sorties_info = sort_if_date(sorties_info)

    # ---------- métriques (utilitaire ajouter_totaux réutilisé) ----------
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

    st.subheader(f"Infos pour : {mgb_selected} - {stock_info.iloc[0]['Désignation'] if not stock_info.empty else ''}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("MMS Stock", totaux_stock.get("MMS_Stock", 0))
    c2.metric("WMS Stock", totaux_stock.get("WMS_Stock", 0))
    c4.metric("Difference MMS-WMS", totaux_stock.get("Difference_MMS-WMS", 0))
    c5.metric("Valeur Difference €", totaux_stock.get("Valeur_Difference", 0),"€")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Inventaire", totaux_inventaire.get("Inventaire_Final_Quantity", 0))
    c2.metric("Mouvements", totaux_mvt_stock.get("Qty_Mouvement", 0))
    c3.metric("Réceptions", totaux_reception.get("Qty_Reception", 0))
    c4.metric("Sorties", totaux_sorties.get("Qty/Article/Poids", 0))
    c5.metric("Stock théorique", round(stock_theorique, 2))

    # affichages tableaux détaillés
    st.subheader("Tableau Inventaire")
    st.dataframe(inventaire_info, use_container_width=True)

    st.subheader("Tableau des mouvements de stock")
    # color_rows est réutilisé mais on évite apply coûteux en l'appliquant sur la subset (déjà petit)
    st.dataframe(mvt_stock_info.style.apply(color_rows, axis=1) if not mvt_stock_info.empty else mvt_stock_info, use_container_width=True)

    st.subheader("Tableau des réceptions")
    st.dataframe(reception_info, use_container_width=True)

    st.subheader("Tableau des sorties")
    st.dataframe(sorties_info, use_container_width=True)

    st.divider()

    # ---------- lecture automatique file_last / parquet_path (identique logique) ----------
    file_last_txt = RENDER_CACHE_DIR / "file_last.txt"
    file_last = None
    try:
        if file_last_txt.exists():
            file_last = file_last_txt.read_text(encoding="utf-8").strip()
        elif (LOCAL_CACHE_DIR / "file_last.txt").exists():
            file_last = (LOCAL_CACHE_DIR / "file_last.txt").read_text(encoding="utf-8").strip()
        else:
            r = requests.get(RAW_BASE + "file_last.txt")
            r.raise_for_status()
            file_last = r.text.strip()
    except Exception as e:
        st.warning(f"Aucun fichier d'écart stock récent trouvé (file_last non défini).\n{e}")
        st.stop()

    file_last_name = Path(file_last).name
    parquet_path = None
    if (RENDER_CACHE_DIR / file_last_name).exists():
        parquet_path = RENDER_CACHE_DIR / file_last_name
    elif (LOCAL_CACHE_DIR / file_last_name).exists():
        parquet_path = LOCAL_CACHE_DIR / file_last_name
    else:
        try:
            github_parquet_url = RAW_BASE + file_last_name
            r = requests.get(github_parquet_url)
            r.raise_for_status()
            parquet_path = RENDER_CACHE_DIR / file_last_name
            parquet_path.write_bytes(r.content)
        except Exception as e:
            st.error(f"Impossible de récupérer le fichier parquet depuis GitHub : {file_last_name}\n{e}")
            st.stop()

    # ---------- lecture du parquet (df base pour commentaires) ----------
    try:
        df_base = pd.read_parquet(parquet_path)
    except Exception as e:
        st.error(f"Erreur lors du chargement du parquet : {parquet_path}\n{e}")
        st.stop()

    # initialisation session df_comments (stockage local en session)
    if "df_comments" not in st.session_state:
        df_existing = df_base.copy()
        if "MGB_6" not in df_existing.columns:
            if "Article number (MGB)" in df_existing.columns:
                df_existing["MGB_6"] = df_existing["Article number (MGB)"].astype(str)
                df_existing = df_existing.drop(columns=["Article number (MGB)"])
            else:
                df_existing["MGB_6"] = ""
        for col in ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement", "IDL_auto"]:
            if col not in df_existing.columns:
                df_existing[col] = "" if col != "IDL_auto" else False
        st.session_state.df_comments = df_existing.copy()

    # use local ref
    df_comments = st.session_state.df_comments

    # ---------- injections consignes en batch (update + append) ----------
    df_consigne = df_ecart_stock_last[df_ecart_stock_last["MGB_6"].isin(MGB_consigne)].copy()
    # ensure cols
    for col in ["Commentaire", "Date_Dernier_Commentaire", "Choix_traitement"]:
        if col not in df_consigne.columns:
            df_consigne[col] = ""
    today = datetime.today().strftime("%d-%m-%Y")
    df_consigne["Commentaire"] = "Consigne"
    df_consigne["Date_Dernier_Commentaire"] = today
    df_consigne["Choix_traitement"] = "XX"

    # prepare indexes for fast update
    df_comments = df_comments.set_index("MGB_6")
    df_consigne_upd = df_consigne.set_index("MGB_6")[["Commentaire","Date_Dernier_Commentaire","Choix_traitement"]]

    # update existing rows
    common_idx = df_comments.index.intersection(df_consigne_upd.index)
    if not common_idx.empty:
        df_comments.update(df_consigne_upd.loc[common_idx])

    # append missing rows
    new_idx = df_consigne_upd.index.difference(df_comments.index)
    if not new_idx.empty:
        rows_to_add = df_consigne_upd.loc[new_idx].copy()
        rows_to_add["IDL_auto"] = False
        df_comments = pd.concat([df_comments, rows_to_add], axis=0)

    df_comments = df_comments.reset_index()

    # ---------- Attribution automatique IDL (batch) ----------
    df_auto_idl = df_ecart_stock_last[df_ecart_stock_last["Difference_MMS-WMS"].abs() < 1].copy()
    auto_mgbs = df_auto_idl["MGB_6"].astype(str).unique().tolist()
    if len(auto_mgbs) > 0:
        # ensure index
        df_comments = df_comments.set_index("MGB_6")
        for mgb in auto_mgbs:
            if mgb in df_comments.index:
                df_comments.at[mgb, "Commentaire"] = "Régul à faire quantité inferieur à 1"
                df_comments.at[mgb, "Date_Dernier_Commentaire"] = today
                df_comments.at[mgb, "Choix_traitement"] = "IDL"
                df_comments.at[mgb, "IDL_auto"] = True
            else:
                df_comments.loc[mgb] = {
                    "Commentaire": "Régul à faire quantité inferieur à 1",
                    "Date_Dernier_Commentaire": today,
                    "Choix_traitement": "IDL",
                    "IDL_auto": True
                }
        df_comments = df_comments.reset_index()

    # save back to session (do not write file yet)
    st.session_state.df_comments = df_comments.copy()

    # ---------- zone d'édition commentaire (interaction) ----------
    df_temp_last = st.session_state.df_comments
    if mgb_selected not in df_temp_last["MGB_6"].astype(str).values:
        st.warning(f"MGB {mgb_selected} non trouvé dans le fichier de commentaires.")
        # don't stop; allow adding new comment manually
        add_new = True
    else:
        add_new = False

    if not add_new:
        idx = df_temp_last.index[df_temp_last["MGB_6"].astype(str) == str(mgb_selected)][0]
        commentaire_existant = df_temp_last.at[idx, "Commentaire"]
        choix_existant = df_temp_last.at[idx, "Choix_traitement"] if "Choix_traitement" in df_temp_last.columns else ""

    # reset input state on change
    if "last_mgb" not in st.session_state:
        st.session_state.last_mgb = mgb_selected
    if mgb_selected != st.session_state.last_mgb:
        st.session_state[f"commentaire_{mgb_selected}"] = ""
        st.session_state[f"choix_{mgb_selected}"] = None
        st.session_state.last_mgb = mgb_selected

    st.markdown(f"<h1 style='font-size:1.6em'>Ajouter un commentaire : {mgb_selected}</h1>", unsafe_allow_html=True)

    if add_new or pd.isna(commentaire_existant) or commentaire_existant == "":
        commentaire = st.text_area("Écrire votre commentaire :", key=f"txt_{mgb_selected}")
        choix_source = st.radio(
            "Sélectionner le chargé du traitement (obligatoire) :",
            options=["METRO", "IDL"],
            key=f"choix_{mgb_selected}"
        )
        if st.button("Ajouter le commentaire", key=f"add_{mgb_selected}"):
            if not choix_source:
                st.error("Vous devez sélectionner METRO ou IDL avant de valider.")
            else:
                today = datetime.today().strftime("%d-%m-%Y")
                # update session df_comments by index
                if mgb_selected in st.session_state.df_comments["MGB_6"].astype(str).values:
                    ridx = st.session_state.df_comments.index[st.session_state.df_comments["MGB_6"].astype(str) == str(mgb_selected)][0]
                    st.session_state.df_comments.at[ridx, "Commentaire"] = commentaire
                    st.session_state.df_comments.at[ridx, "Date_Dernier_Commentaire"] = today
                    st.session_state.df_comments.at[ridx, "Choix_traitement"] = choix_source
                else:
                    new_row = {"MGB_6": str(mgb_selected), "Commentaire": commentaire, "Date_Dernier_Commentaire": today, "Choix_traitement": choix_source, "IDL_auto": False}
                    st.session_state.df_comments = pd.concat([st.session_state.df_comments, pd.DataFrame([new_row])], ignore_index=True)
                # write once, then git push
                st.session_state.df_comments.to_parquet(parquet_path, index=False)
                git_commit_push(parquet_path, f"MAJ commentaires pour MGB {mgb_selected}")
                st.success(f"Commentaire ajouté pour {mgb_selected} ({today}) !")
                # refresh local copies
                st.experimental_rerun()
    else:
        st.write(f"Commentaire actuel : {commentaire_existant}")
        st.write(f"Suivi actuel : {choix_existant if choix_existant else 'Non défini'}")
        modifier = st.radio("Voulez-vous changer ce commentaire ?", ("Non", "Oui"), key=f"modif_{mgb_selected}")
        if modifier == "Oui":
            commentaire = st.text_area("Écrire votre nouveau commentaire :", commentaire_existant, key=f"edit_{mgb_selected}")
            choix_source = st.radio(
                "Sélectionner le chargé du traitement (obligatoire) :",
                options=["METRO", "IDL"],
                index=["METRO", "IDL"].index(choix_existant) if choix_existant in ["METRO", "IDL"] else 0,
                key=f"choix_edit_{mgb_selected}"
            )
            if st.button("Mettre à jour le commentaire", key=f"update_{mgb_selected}"):
                today = datetime.today().strftime("%d-%m-%Y")
                ridx = st.session_state.df_comments.index[st.session_state.df_comments["MGB_6"].astype(str) == str(mgb_selected)][0]
                st.session_state.df_comments.at[ridx, "Commentaire"] = commentaire
                st.session_state.df_comments.at[ridx, "Date_Dernier_Commentaire"] = today
                st.session_state.df_comments.at[ridx, "Choix_traitement"] = choix_source
                st.session_state.df_comments.to_parquet(parquet_path, index=False)
                git_commit_push(parquet_path, f"MAJ commentaires pour MGB {mgb_selected}")
                st.success(f"Commentaire mis à jour pour {mgb_selected} ({today}) !")
                st.experimental_rerun()

    # ---------- Génération du PDF trié par Suivi puis Date ----------
    if st.button("Générer le PDF du rapport"):
        df_for_pdf = st.session_state.df_comments.copy()
        df_for_pdf = df_for_pdf[df_for_pdf["Date_Dernier_Commentaire"].notna() & (df_for_pdf["Date_Dernier_Commentaire"] != "")].fillna("")

        # ajouter colonne 'Cellule' via df_sorties (une ligne par MGB_6)
        if not df_sorties.empty:
            df_cellules = df_sorties[['MGB_6', 'Cellule']].dropna(subset=['MGB_6']).drop_duplicates(subset=['MGB_6'], keep='first')
            df_for_pdf = df_for_pdf.merge(df_cellules, on='MGB_6', how='left')
        else:
            df_for_pdf["Cellule"] = ""

        # date convert
        df_for_pdf["Date_Dernier_Commentaire_dt"] = pd.to_datetime(df_for_pdf["Date_Dernier_Commentaire"], format="%d-%m-%Y", errors="coerce")

        # create Suivi_sort with IDL_auto handled
        def suivi_val(row):
            if row.get("IDL_auto", False):
                return "IDL_auto"
            val = row.get("Choix_traitement", "")
            return val if pd.notna(val) else ""

        df_for_pdf["Suivi_sort"] = df_for_pdf.apply(suivi_val, axis=1)

        suivi_order = ["METRO", "IDL", "IDL_auto", "", "XX"]
        df_for_pdf["Suivi_sort"] = pd.Categorical(df_for_pdf["Suivi_sort"], categories=suivi_order, ordered=True)

        # sort by suivi then date (ascending)
        df_for_pdf = df_for_pdf.sort_values(by=["Suivi_sort", "Date_Dernier_Commentaire_dt"], ascending=[True, True])

        # exclude consignes for detailed part
        df_for_pdf_no_consigne = df_for_pdf[~df_for_pdf["MGB_6"].astype(str).isin(MGB_consigne)].copy()

        # precompute color mapping
        def color_code(row):
            if row.get("IDL_auto", False): return (216,191,216)
            if row.get("Choix_traitement") == "METRO": return (255,255,153)
            if row.get("Choix_traitement") == "IDL": return (173,216,230)
            if row.get("Choix_traitement") == "XX": return (255,200,200)
            return (255,255,255)
        df_for_pdf["Color_fill"] = df_for_pdf.apply(color_code, axis=1)

        # PDF class as before but lighter loop since precomputed fields exist
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

        # build pdf
        col_widths = [15, 70, 15, 15, 15, 15, 20, 15, 105]
        headers = ["MGB_6", "Désignation","Cellule","MMS","WMS", "Diff", "Date", "Suivi", "Commentaire"]
        pdf = PDF(headers, col_widths)
        pdf.set_auto_page_break(auto=True, margin=20)

        # synthese page (same content)
        total_lignes = len(st.session_state.df_comments) - len(df_consigne)
        df_metro = df_for_pdf_no_consigne[df_for_pdf_no_consigne["Choix_traitement"] == "METRO"]
        df_idl = df_for_pdf_no_consigne[df_for_pdf_no_consigne["Choix_traitement"] == "IDL"]
        nb_metro, nb_idl = len(df_metro), len(df_idl)
        nb_non = total_lignes - (nb_metro + nb_idl)

        x_offset = 50; x_offset_1 = 40
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

        synthese_data = [("Lignes METRO", str(nb_metro)), ("Lignes IDL", str(nb_idl)), ("Lignes en attente d'affectations", str(nb_non)), ("Total écarts (hors consignes)", str(total_lignes))]

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

        # retards table
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(x_offset_1)
        pdf.cell(0, 8, "Synthèse des retards de traitement", ln=True)
        pdf.set_font("Arial", "", 10)
        today_dt = datetime.today()
        df_retard = df_for_pdf[(~df_for_pdf["MGB_6"].isin(MGB_consigne)) & (df_for_pdf["Date_Dernier_Commentaire_dt"].notna())]
        retard_data = []
        for days in [3,6,10]:
            df_days = df_retard[(today_dt - df_retard["Date_Dernier_Commentaire_dt"]).dt.days > days]
            nb_met = len(df_days[df_days["Choix_traitement"] == "METRO"])
            nb_idl_ = len(df_days[df_days["Choix_traitement"] == "IDL"])
            retard_data.append((f"> {days} jours", str(nb_met), str(nb_idl_)))

        col_widths_retard = [90, 40, 40]
        pdf.set_fill_color(220, 220, 220)
        pdf.set_x(x_offset)
        pdf.cell(col_widths_retard[0], 8, "Délai depuis dernier commentaire", border=1, align="C", fill=True)
        pdf.cell(col_widths_retard[1], 8, "METRO", border=1, align="C", fill=True)
        pdf.cell(col_widths_retard[2], 8, "IDL", border=1, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for row in retard_data:
            pdf.set_x(x_offset)
            pdf.cell(col_widths_retard[0], 8, row[0], border=1)
            pdf.cell(col_widths_retard[1], 8, row[1], border=1, align="C")
            pdf.cell(col_widths_retard[2], 8, row[2], border=1, align="C")
            pdf.ln()

        pdf.first_page = False
        pdf.add_page()
        pdf.set_font("Arial", "", 9)

        # boucle détaillée (précomputation réduit le coût)
        for _, row in df_for_pdf.iterrows():
            pdf.set_fill_color(*row["Color_fill"])
            pdf.cell(col_widths[0], 6, str(row["MGB_6"]), border=1, align="C", fill=True)
            pdf.cell(col_widths[1], 6, str(row.get("Désignation", "")), border=1, fill=True)
            pdf.cell(col_widths[2], 6, str(row.get("Cellule", "")), border=1, align="C", fill=True)
            pdf.cell(col_widths[3], 6, str(row.get("MMS_Stock", "")), border=1, fill=True)
            pdf.cell(col_widths[4], 6, str(row.get("WMS_Stock", "")), border=1, fill=True)
            pdf.cell(col_widths[5], 6, str(round(row.get("Difference_MMS-WMS", 0), 2)), border=1, align="C", fill=True)
            pdf.cell(col_widths[6], 6, str(row.get("Date_Dernier_Commentaire", "")), border=1, align="C", fill=True)
            pdf.cell(col_widths[7], 6, str(row.get("Choix_traitement", "")), border=1, align="C", fill=True)
            x_before = pdf.get_x(); y_before = pdf.get_y()
            pdf.multi_cell(col_widths[8], 6, str(row.get("Commentaire", "")), border=1, fill=True)
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

        # write parquet with comments after PDF generation (one save)
        st.session_state.df_comments.to_parquet(parquet_path, index=False)
        git_commit_push(parquet_path, f"MAJ commentaires / export PDF {datetime.today().strftime('%Y-%m-%d')}")

        st.success("PDF généré et commentaires sauvegardés.")


def tab_Detrompeurs():
    st.title("Détrompeurs")
    st.write("Générateur de PDF de détrompeurs à partir d'un MGB.")

        # -------------------- Fichiers sources GitHub --------------------
    fichier_pdf_vierge_url = "https://github.com/IDLAurelienMartin/Data_IDL/raw/main/Detrompeur/detrompeur_vierge.pdf"
    file_excel_ean_url = "https://github.com/IDLAurelienMartin/Data_IDL/raw/main/Detrompeur/Liste%20detrompeur%20%2B%20EAN.xlsx"
    file_excel_stock_url = "https://github.com/IDLAurelienMartin/Data_IDL/raw/main/Etat_Stock.xlsm"

    # Dossier sortie Render
    dossier_sortie = Path("Detrompeur_output")
    dossier_sortie.mkdir(exist_ok=True)

    # -------------------- Télécharger PDF vierge --------------------
    fichier_pdf_vierge = dossier_sortie / "detrompeur_vierge.pdf"
    r = requests.get(fichier_pdf_vierge_url)
    r.raise_for_status()
    with open(fichier_pdf_vierge, "wb") as f:
        f.write(r.content)

    # -------------------- Télécharger Excel EAN --------------------
    file_excel_ean = dossier_sortie / "Liste_detrompeur_EAN.xlsx"
    r = requests.get(file_excel_ean_url)
    r.raise_for_status()
    with open(file_excel_ean, "wb") as f:
        f.write(r.content)

    # -------------------- Télécharger Excel Etat Stock --------------------
    file_excel_stock = dossier_sortie / "Etat_Stock.xlsm"
    r = requests.get(file_excel_stock_url)
    r.raise_for_status()
    with open(file_excel_stock, "wb") as f:
        f.write(r.content)

    # -------------------- Charger DataFrames --------------------
    try:
        df_ean = pd.read_excel(file_excel_ean, dtype=str)
    except Exception:
        df_ean = pd.DataFrame(columns=["Description", "MGB", "CODE EAN"])

    try:
        df_etat_stock = pd.read_excel(file_excel_stock, sheet_name="Stock", dtype=str)
    except Exception:
        st.error("Erreur lors du chargement du fichier Etat_Stock.xlsm")
        return

    # -------------------- Saisie MGB --------------------
    liste_mgb = df_etat_stock['MGB'].dropna().unique()
    mgb_saisie = st.text_input("Taper le MGB ici et appuyer sur Entrée pour voir les suggestions")
    suggestions = [m for m in liste_mgb if mgb_saisie.upper() in str(m).upper()]
    mgb_input = st.selectbox("Suggestions de MGB", options=suggestions) if suggestions else mgb_saisie

    if mgb_input:
        ligne_mgb = df_etat_stock[df_etat_stock["MGB"] == mgb_input]
        if not ligne_mgb.empty:
            designation_preview = ligne_mgb["Description"].values[0]
            st.info(f"🔎 Désignation trouvée : **{designation_preview}**")

    # -------------------- Choix type de prise --------------------
    type_prise = st.selectbox("Type de prise", ["COLIS", "PIECE", "POIDS"], index=0)

    # -------------------- Aperçu PDF existant --------------------
    nom_fichier = f"Detrompeur_{mgb_input}.pdf"
    chemin_final = dossier_sortie / nom_fichier

    if chemin_final.exists():
        st.warning("Un PDF pour ce MGB existe déjà :")
        import fitz
        pdf = fitz.open(str(chemin_final))
        pix = pdf[0].get_pixmap()
        st.image(pix.tobytes("png"), caption="Aperçu du PDF existant", use_container_width=True)

        modifier = st.radio("Voulez-vous le modifier ?", ["Non", "Oui"])
        if modifier == "Non":
            st.download_button("Télécharger le PDF existant",
                               data=open(chemin_final, "rb").read(),
                               file_name=nom_fichier, mime="application/pdf")
            return

    # -------------------- Uploader photos --------------------
    photo_ok = st.file_uploader("✅Charger la photo OK✅ (.jpeg)", type=['jpeg'])
    photo_ko = st.file_uploader("❌Charger la photo KO❌ (.jpeg)", type=['jpeg'])

    # -------------------- Récupération données MGB --------------------
    ligne = df_etat_stock[df_etat_stock['MGB'] == mgb_input]
    if ligne.empty:
        st.error("MGB non trouvé dans l'état stock.")
        return
    designation = ligne['Description'].values[0]
    ref_metro = str(ligne['Ref Metro'].values[0]).split('.')[0]
    ean = ligne['EAN'].values[0]

    if pd.notna(ean):
        ean = str(int(float(ean))) if isinstance(ean, (float, int)) else str(ean)
        st.info(f"L’EAN existant pour ce MGB : {ean}")
    else:
        st.warning("Pas d’EAN existant pour ce MGB.")
        ean = st.text_input("Ajouter un EAN manuellement :", value="")

    force_pdf = st.checkbox("Forcer la création du PDF même sans EAN")

    # -------------------- Création PDF --------------------
    if st.button("Créer PDF"):
        if not ean and not force_pdf:
            st.error("Veuillez saisir un EAN ou cocher 'Forcer la création du PDF'.")
            return

        # --- Mise à jour Excel si EAN saisi ---
        if ean:
            if mgb_input in df_ean['MGB'].values:
                df_ean.loc[df_ean['MGB'] == mgb_input, 'CODE EAN'] = ean
            else:
                df_ean = pd.concat([df_ean, pd.DataFrame([{"Description": designation, "MGB": mgb_input, "CODE EAN": ean}])], ignore_index=True)
            df_ean.to_excel(file_excel_ean, index=False)
            st.success(f"EAN {ean} ajouté/modifié dans le fichier EAN.")

        # --- Génération PDF ---
        buffer_txt = BytesIO()
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer_txt, pagesize=(page_width, page_height))

        # --- Police intégrée ---
        font_path = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"
        font_size = 36
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", str(font_path)))
            font_name = "DejaVu"
        except Exception:
            font_name = "Helvetica-Bold"

        # --- Texte Designation ---
        x_start, y_start = 20, page_height - 160
        max_width, max_lines = page_width/2 - 50, 3
        words = designation.split()
        while font_size >= 10:
            lines, line = [], ""
            for word in words:
                test_line = f"{line} {word}".strip()
                if c.stringWidth(test_line, font_name, font_size) <= max_width:
                    line = test_line
                else:
                    lines.append(line)
                    line = word
            if line: lines.append(line)
            if len(lines) <= max_lines: break
            font_size -= 2

        text_obj = c.beginText()
        text_obj.setTextOrigin(x_start, y_start)
        text_obj.setFont(font_name, font_size)
        text_obj.setFillColor(colors.darkblue)
        for l in lines: text_obj.textLine(l)
        c.drawText(text_obj)

        # --- Ref Metro et Type Prise ---
        c.setFont(font_name, 38)
        c.drawString(x_start + 220, y_start - 150, f"{ref_metro}")
        c.drawString(x_start + 200, y_start - 210, f"{type_prise}")

        # --- QR code ---
        qr_img = qrcode.make(mgb_input).convert("RGB")
        qr_img = qr_img.resize((100,100))
        c.drawImage(ImageReader(qr_img), page_width-110, page_height-110, width=100, height=100)

        # --- EAN ---
        if ean:
            ean_img = EAN13(ean, writer=ImageWriter()) if len(ean)==13 else EAN8(ean, writer=ImageWriter())
            buf_ean = BytesIO()
            ean_img.write(buf_ean)
            buf_ean.seek(0)
            img = Image.open(buf_ean).resize((300,150))
            c.drawImage(ImageReader(img), 50, 50, width=300, height=150)

        # --- Photos OK / KO ---
        def ajouter_croix_rouge(file):
            img = Image.open(file).convert("RGBA")
            draw = ImageDraw.Draw(img)
            w, h = img.size
            thick = max(5, w//100)
            draw.line((0,0,w,h), fill=(255,0,0,255), width=thick)
            draw.line((0,h,w,0), fill=(255,0,0,255), width=thick)
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf

        def get_image_size(file, max_w, max_h):
            img = Image.open(file) if not isinstance(file, Image.Image) else file
            ratio = min(max_w/img.width, max_h/img.height)
            return img, img.width*ratio, img.height*ratio

        quart_width, max_w_img, max_h_img, decalage = page_width*0.25, page_width*0.25-20, page_height-100, 15
        if photo_ok:
            img, iw, ih = get_image_size(photo_ok, max_w_img, max_h_img)
            c.drawImage(ImageReader(img), page_width*0.75 + (quart_width-iw)/2 - decalage, page_height/2-ih/2, width=iw, height=ih)
        if photo_ko:
            img, iw, ih = get_image_size(photo_ko, max_w_img, max_h_img)
            img_marked = ajouter_croix_rouge(img)
            c.drawImage(ImageReader(img_marked), page_width*0.5 + (quart_width-iw)/2 - decalage, page_height/2-ih/2, width=iw, height=ih)

        c.save()
        buffer_txt.seek(0)

        # --- Fusion PDF vierge ---
        reader_vierge = PdfReader(fichier_pdf_vierge)
        writer = PdfWriter()
        page_vierge = reader_vierge.pages[0]
        reader_txt = PdfReader(buffer_txt)
        page_txt = reader_txt.pages[0]
        page_vierge.merge_page(page_txt)
        writer.add_page(page_vierge)

        # --- Enregistrer PDF localement ---
        with open(chemin_final, "wb") as f_out:
            writer.write(f_out)
        st.success(f"PDF généré localement : {chemin_final}")
        st.download_button("Télécharger PDF", data=open(chemin_final,"rb").read(),
                           file_name=nom_fichier, mime="application/pdf")

        # --- Push GitHub ---
        def push_to_github(file_path, repo_path, commit_message="Ajout detrompeur"):
            with open(file_path,"rb") as f:
                content_b64 = base64.b64encode(f.read()).decode()
            repo_owner = "IDLAurelienMartin"
            repo_name = "Data_IDL"
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{repo_path}"
            headers = {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}"}
            r = requests.get(url, headers=headers)
            sha = r.json().get("sha") if r.status_code==200 else None
            data = {"message": commit_message, "content": content_b64}
            if sha: data["sha"]=sha
            r = requests.put(url, json=data, headers=headers)
            if r.status_code in [200,201]:
                st.success(f"PDF envoyé dans GitHub : {repo_path}")
            else:
                st.error(f"Erreur GitHub : {r.status_code} {r.text}")

        repo_path = f"Detrompeur/Detrompeur/{nom_fichier}"
        push_to_github(str(chemin_final), repo_path)

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



