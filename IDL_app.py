import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
import qrcode
from barcode.ean import EAN13, EAN8
from barcode.writer import ImageWriter
from pathlib import Path
import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import subprocess
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageDraw
from pdf2image import convert_from_path
import fitz
import numpy as np
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
import tempfile
import requests
import streamlit.components.v1 as components
import re
import math
# IDL_app.py
import sys

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

# Ajouter scripts/ au path **avant tout import**
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Maintenant les imports fonctionnent
try:
    from prepare_data import prepare_stock_data
    from preprocess_stock import load_data, preprocess_data
    from utils_stock import some_helper_function  # exemple
except ModuleNotFoundError as e:
    st.error(f"Erreur d'import : {e}")

# --- Initialisation des données ---
@st.cache_data(show_spinner="Initialisation des données…")
def init_data():
    prepare_stock_data()  # génère les Parquet dans le cache Streamlit
    return "Cache prêt"

init_data()
st.title("IDL App")


def tab_home():
    st.set_page_config(layout="wide")  # Doit être en premier
    st.title("Bibliothèque CID")

    # --- Configuration des services et dossiers ---
    base_cid = "https://github.com/IDLAurelienMartin/Data_IDL/tree/main/CID"
    Types = ["Infos Site", "Procedures"]
    info_types = {        
        "Générale": f"{base_cid}",
        "Fiches Reflexes": f"{base_cid} /FICHES REFLEXES",
        "Fiches Reflexes Nationales": f"{base_cid} /FICHES REFLEXES/Nationales"
    }
    services_procedure = {
        "Service Réception": f"{base_cid}/RECEPTION",
        "Service GDS": f"{base_cid}/GDS",
        "Service Preparation": f"{base_cid}/PREPARATION",
        "Service Réapprovisionnement": f"{base_cid}/REAPPRO",
    }

    cache_dir = Path(".streamlit/Cache/PDF")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # --- Interface Streamlit ---
    st.subheader("Visualisateur de Documents de Référence :")

    st.markdown("<h5>Choisir Type de Documents :</h5>", unsafe_allow_html=True)
    type_choix = st.selectbox("", Types, label_visibility="collapsed")

    col1, col2 = st.columns(2)

    with col1:
        # Sélecteur de service
        if type_choix == "Infos Site":
            st.markdown("<h5>Choisir type info :</h5>", unsafe_allow_html=True)
            service_selected = st.selectbox("", list(info_types.keys()), label_visibility="collapsed")
            service_path = info_types[service_selected]
        else:
            st.markdown("<h5>Choisir le Service :</h5>", unsafe_allow_html=True)
            service_selected = st.selectbox("", list(services_procedure.keys()), label_visibility="collapsed")
            service_path = services_procedure[service_selected]

    with col2:
        api_url = service_path.replace(
            "raw.githubusercontent.com",
            "api.github.com/repos/IDLAurelienMartin/Data_IDL/contents"
        )

        response = requests.get(api_url)

        if response.status_code != 200:
            st.warning("Impossible de charger les documents.")
            return

        pdf_files = [
            f["name"] for f in response.json()
            if f["name"].lower().endswith(".pdf")
        ]

        if not pdf_files:
            st.warning("Aucun PDF trouvé.")
            return

        pdf_selected = st.selectbox("Document", pdf_files)

    # ------------------ Téléchargement + affichage ------------------
    if st.button("Ouvrir le PDF"):
        pdf_url = f"{service_path}/{pdf_selected}"
        local_pdf = cache_dir / pdf_selected

        if not local_pdf.exists():
            r = requests.get(pdf_url)
            local_pdf.write_bytes(r.content)

        with open(local_pdf, "rb") as f:
            st.download_button(
                "Télécharger le PDF",
                f,
                file_name=pdf_selected,
                mime="application/pdf"
            )

        st.pdf(local_pdf)

def tab_QR_Codes():
    st.title("Etiquettes, QR Code, EAN")

    # --- Listes ---
    Liste_choix_Qr_code = ['','Etiquette Emplacement','QR Codes', 'EAN']
    Liste_allée = {
        "Ambiant": ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18'],
        "Frais": ['19','20','21','22','23','24','25','26','27','28','29'],
        "FL": ['30','31','32','33','34','35','36','37'],
        "Surgelé": ['38','39','40','41','42','43','44','45','46','47','48','49'],
        "Marée": ['50','51','52','53','54','55','56','57','58','59','60']
    }
    Liste_rangée = [str(i) for i in range(1, 41)]
    Liste_niveau = {
        "Ambiant": ['A1','A2','A3','A4'],
        "Frais": ['A1','A2','A3','A4'],
        "FL": ['A1','A2','A3','A4'],
        "Surgelé": ['A1','A2','A3','A4'],
        "Marée": ['A1','A2','A3','A4']
    }
    Liste_niveau_hauteur = {
        "Ambiant": ['B1','C1','D1'],
        "Frais": ['B1'],
        "FL": ['B1'],
        "Surgelé": ['B1','C1','D1']
    }
    Liste_emplacement = [str(i) for i in range(1, 13)]
    Liste_emplacement_hauteur = {
        "Ambiant": ['1','2','3'],
        "Frais": ['1','2','3', '4'],
        "FL": ['1','2','3', '4'],
        "Surgelé": ['1','2','3','4'],
    }
    # Choix du type de QR Code
    st.markdown("<h5>Choix :</h5>", unsafe_allow_html=True)
    option = st.selectbox('', options= Liste_choix_Qr_code,
                label_visibility="collapsed")
    
    if option == "Etiquette Emplacement":
        st.subheader("Etiquette Emplacement :")
        
        # --- Choix du format ---

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<h5>Choisir Format :</h5>", unsafe_allow_html=True)
            nb_qr_format = st.radio(
                label="",
                options=[ "Petit Format-Picking", "Petit Format-Stockage", "Grand Format"],
                label_visibility="collapsed"
            )
        with col2:
            st.markdown("<h5>Choisir Types :</h5>", unsafe_allow_html=True)
            nb_qr_serie = st.radio(
                label="",
                options=["Unités", "Série"],
                label_visibility="collapsed"
            )
                
        if nb_qr_serie == "Unités":
            if nb_qr_format == "Grand Format":
                qr_count = st.selectbox("Nombre de QR Codes :", range(1, 101))
                cols_per_row = 1
                font_size = 60
                frame_width = A4[0] - 20
                frame_height = 273
                spacing = 1
            elif nb_qr_format == "Petit Format-Picking":
                qr_count = st.selectbox("Nombre de QR Codes :", range(1, 101))
                cols_per_row = 2
                font_size = 30
                frame_width = (A4[0] - 130) / 2
                frame_height = 130
                spacing = 30
            else:
                qr_count = st.selectbox("Nombre de QR Codes :", range(1, 101))
                cols_per_row = 3
                font_size = 30
                frame_width = (A4[0] - 150) / 3
                frame_height = 220
                spacing = 20
        else :
            if nb_qr_format == "Grand Format":
                qr_count_serie = st.selectbox("Nombre de Série de QR Codes :", range(1, 11))
                qr_count = 101
                cols_per_row = 1
                font_size = 60
                frame_width = A4[0] - 20
                frame_height = 273
                spacing = 1
            elif nb_qr_format == "Petit Format-Picking":
                qr_count_serie = st.selectbox("Nombre de Série de QR Codes :", range(1, 11))
                qr_count = 101
                cols_per_row = 2
                font_size = 30
                frame_width = (A4[0] - 130) / 2
                frame_height = 130
                spacing = 30
            else:
                qr_count_serie = st.selectbox("Nombre de Série de QR Codes :", range(1, 11))
                qr_count = 101
                cols_per_row = 3
                font_size = 30
                frame_width = (A4[0] - 150) / 3
                frame_height = 220
                spacing = 20

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
                    if nb_qr_format == "Petit Format-Picking":
                        niveau = st.selectbox(f"Niveau", options=Liste_niveau[cellule], key=f"Niveau_{i}")
                    elif nb_qr_format == "Petit Format-Stockage":
                        niveau = st.selectbox(f"Niveau", options=Liste_niveau_hauteur[cellule], key=f"Niveau_{i}")
                    else:
                        niveau = st.selectbox(f"Niveau", options=Liste_niveau[cellule] + Liste_niveau_hauteur[cellule], key=f"Niveau_{i}")
                with col4:
                    if nb_qr_format == "Petit Format-Picking":
                        colonne = st.selectbox(f"Colonne", options=Liste_emplacement, key=f"Colonne_{i}")
                    elif nb_qr_format == "Petit Format-Stockage":
                        colonne = st.selectbox(f"Colonne", options=Liste_emplacement_hauteur[cellule], key=f"Colonne_{i}")
                    else:
                        colonne = st.selectbox(f"Colonne", options=Liste_emplacement + Liste_emplacement_hauteur[cellule], key=f"Colonne_{i}")  
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

                    if nb_qr_format == "Petit Format-Picking":
                        niveau_start = st.selectbox("Niveau début", options=Liste_niveau[cellule], key=f"Niveau_start_{i}")
                        niveau_end = st.selectbox("Niveau fin", options=Liste_niveau[cellule], key=f"Niveau_end_{i}")
                    elif nb_qr_format == "Petit Format-Stockage":
                        niveau_start = st.selectbox("Niveau début", options=Liste_niveau_hauteur[cellule], key=f"Niveau_start_{i}")
                        niveau_end = st.selectbox("Niveau fin", options=Liste_niveau_hauteur[cellule], key=f"Niveau_end_{i}")
                    else:
                        niveau_start = st.selectbox("Niveau début", options=Liste_niveau[cellule] + Liste_niveau_hauteur[cellule], key=f"Niveau_start_{i}")
                        niveau_end = st.selectbox("Niveau fin", options=Liste_niveau[cellule] + Liste_niveau_hauteur[cellule], key=f"Niveau_end_{i}")
                with col3:
                    st.markdown(f"**Choisi les Colonnes**")
                    if nb_qr_format == "Petit Format-Picking":
                        col_start = st.selectbox("Colonne début", options=Liste_emplacement, key=f"Colonne_start_{i}")
                        col_end = st.selectbox("Colonne fin", options=Liste_emplacement, key=f"Colonne_end_{i}")
                    elif nb_qr_format == "Petit Format-Stockage":
                        col_start = st.selectbox("Colonne début", options=Liste_emplacement_hauteur[cellule], key=f"Colonne_start_{i}")
                        col_end = st.selectbox("Colonne fin", options=Liste_emplacement_hauteur[cellule], key=f"Colonne_end_{i}")
                    else:
                        col_start = st.selectbox("Colonne début", options=Liste_emplacement + Liste_emplacement_hauteur[cellule], key=f"Colonne_start_{i}")
                        col_end = st.selectbox("Colonne fin", options=Liste_emplacement + Liste_emplacement_hauteur[cellule], key=f"Colonne_end_{i}")


                # Construire les plages
                if nb_qr_format == "Petit Format-Picking":
                    niveaux = Liste_niveau[cellule]
                    colonnes = Liste_emplacement
                elif nb_qr_format == "Petit Format-Stockage":
                    niveaux = Liste_niveau_hauteur[cellule]
                    colonnes = Liste_emplacement_hauteur[cellule]
                else:
                    niveaux = Liste_niveau[cellule] + Liste_niveau_hauteur[cellule]
                    colonnes = Liste_emplacement + Liste_emplacement_hauteur[cellule]

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

                combined = Image.new("RGB", (int(frame_width), int(frame_height)), text_bg_color)

                if nb_qr_format == "Petit Format-Stockage" :
                    qr_width = int(frame_width * 1)
                    qr_height = int(frame_height * 0.65)
                else :
                    qr_width = int(frame_width * 0.55)
                    qr_height = int(frame_height * 1)

                qr_offset = -20 if nb_qr_format == "Grand Format" else -10
                text_position = "bottom" if nb_qr_format == "Petit Format-Stockage" else "left"
                if text_position == "left":
                    text_x0 = max(qr_width + qr_offset, 0)
                    text_y0 = 0
                    text_x1 = frame_width
                    text_y1 = frame_height
                else:  # bottom
                    text_x0 = 0
                    text_y0 = int(frame_height * 0.65)
                    text_x1 = frame_width
                    text_y1 = frame_height
             
                draw = ImageDraw.Draw(combined)
                draw.rectangle([(text_x0, text_y0), (text_x1, text_y1)], fill=text_bg_color)

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=2
                )
                qr.add_data(contenu_qr)
                qr.make(fit=True)

                qr_img = qr.make_image(
                    fill_color="black",
                    back_color=text_bg_color
                ).convert("RGB")

                qr_img = qr_img.resize((qr_width, qr_height))

                # Position verticale selon format
                if nb_qr_format == "Petit Format-Stockage":
                    qr_y = 1  # légèrement en haut
                    qr_x = (frame_width - qr_width) // 2  # centre horizontalement
                else:
                    qr_y = (frame_height - qr_height) // 2  # centre verticalement
                    qr_x = 1  # légèrement à gauche


                combined.paste(qr_img, (int(qr_x), int(qr_y)))

                def fit_text_in_box(draw, text, font_path, box_width, box_height, max_font_size):
                    """
                    Retourne une police et les dimensions du texte qui rentrent dans la boîte,
                    sans dépasser max_font_size.
                    """
                    font_size = max_font_size
                    font = ImageFont.truetype(font_path, font_size)
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    # Réduire la taille tant que le texte dépasse la boîte
                    while (text_width > box_width or text_height > box_height) and font_size > 1:
                        font_size -= 1
                        font = ImageFont.truetype(font_path, font_size)
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]

                    return font, text_width, text_height


                # Calcul taille adaptative
                padding_h = int(0.05 * (text_x1 - text_x0)) 
                box_width = text_x1 - text_x0 - 2 * padding_h
                box_height = text_y1 - text_y0
                font, text_width, text_height = fit_text_in_box(draw, texte_affiche, "arialbd.ttf", box_width, box_height, max_font_size=font_size)

                if text_position == "left":
                    text_x = text_x0 + (text_x1 - text_x0 - text_width) // 2
                    text_y = (frame_height - text_height) // 2
                else:  # bottom
                    text_x = (frame_width - text_width) // 2
                    text_y = text_y0 + (text_y1 - text_y0 - text_height) // 2


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
    
    elif option == 'QR Codes':

        st.subheader("QR Codes")

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
                if len(EAN_input) == 13:
                    ean = EAN13(EAN_input, writer=ImageWriter())
                elif len(EAN_input) == 8:
                    ean = EAN8(EAN_input, writer=ImageWriter())
                else:
                    st.error("Le code EAN doit faire 8 ou 13 chiffres.")
                    st.stop()  # stoppe le reste du code si code invalide

                buffer = BytesIO()
                ean.write(buffer)
                buffer.seek(0)

            except Exception as e:
                # Ici on intercepte toute autre erreur
                st.error("Une erreur est survenue lors de la génération du code barre.")

            # Boutons pour téléchargement et effacer
            col1, col2 = st.columns(2)
            with col1:
                    st.image(buffer, caption=f"Code barre du EAN {EAN_input}", use_container_width=True)
                    st.download_button(
                    label="Télécharger le code barre",
                    data=buffer,
                    file_name=f"Code_barre_{EAN_input}.png",
                    mime="image/png"
                    )
            with col2:
                    if st.button("Effacer le code barre"):
                            st.experimental_rerun()

def Analyse_stock():   
    today = datetime.today().strftime("%d/%m/%Y")
    st.set_page_config(layout="wide")
    from scripts.utils_stock import update_emplacement, ajouter_totaux, color_rows

    # --- Charger les fichiers depuis le cache (OneDrive) ---
    onedrive_cache_dir = Path(r"\\spwfs-metbre\Partage\11_Public\Data_app\Cache")
    data_dir = onedrive_cache_dir

    if not data_dir.exists():
        st.error(f"Le dossier cache OneDrive est introuvable : {data_dir}")
        return


    try:
        df_article_euros = pd.read_parquet(data_dir / "article_euros.parquet")
        df_inventaire = pd.read_parquet(data_dir / "inventaire.parquet")
        df_mvt_stock = pd.read_parquet(data_dir / "mvt_stock.parquet")
        df_reception = pd.read_parquet(data_dir / "reception.parquet")
        df_sorties = pd.read_parquet(data_dir / "sorties.parquet")
        df_ecart_stock_prev = pd.read_parquet(data_dir / "ecart_stock_prev.parquet")
        df_ecart_stock_last = pd.read_parquet(data_dir / "ecart_stock_last.parquet")

    except Exception as e:
        st.error(f"Erreur lors du chargement du cache : {e}")
        return

    # 🔧 Harmoniser le format de la colonne MGB_6 dans tous les DataFrames
    for df in [df_article_euros, df_inventaire, df_mvt_stock, df_reception, df_sorties, df_ecart_stock_prev, df_ecart_stock_last]:
        if "MGB_6" in df.columns:
            df["MGB_6"] = df["MGB_6"].astype(str).str.strip().str.replace(" ", "")


    # --- Interface principale Streamlit ---
    st.title("Analyse Ecarts GEGC")

    # 🔧 Préparation légère ou ajustements (si nécessaires)
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
        "890060",'835296','388997','226976','226967','135656'
    ]

    
    # Afficher le tableau des écarts

    st.subheader("Tableau des écarts")

    # --- Colonnes pour les 5 premiers filtres ---
    cols = st.columns(5)

    # --- Options de filtrage ---
    options_1 = ["Toutes", "Positives", "Négatives", "Zéro"]
    options_2 = ["Tous", "Oui", "Non"]
    options_3 = ["Toutes","<1","1-5","5-10","10-15","15-20","20+"]
    options_4 = ["Toutes", "Positives", "Zéro"]
    options_5 = ["Toutes", "Positives", "Négatives"]

    filtres = {
        "WMS_Stock : IDL": {"col": cols[1], "options": options_4, "type": "numeric"},
        "MMS_Stock : Metro": {"col": cols[0], "options": options_1, "type": "numeric"},
        "Au_Kg": {"col": cols[2], "options": options_2, "type": "bool"},
        "Difference_MMS-WMS_Valeur": {"col": cols[3], "options": options_3, "type": "range", "df_col": "Difference_MMS-WMS"},
        "Difference_MMS-WMS_+/-": {"col": cols[4], "options": options_5, "type": "numeric", "df_col": "Difference_MMS-WMS"},
        }


    # --- Initialiser session_state pour chaque filtre ---
    for key, filt in filtres.items():
        state_key = f"filter_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = filt["options"][0]

    # --- Bouton Réinitialiser les 5 premiers filtres ---
    def reset_filters():
        for key in filtres.keys():
            st.session_state[f"filter_{key}"] = filtres[key]["options"][0]


    # --- Selectboxes pour les 5 premiers filtres (utiliser key pour forcer la lecture depuis session_state) ---
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
        columns={'Difference_MMS-WMS': 'Difference_précédente'}
    )
    df_affiche = df_affiche.merge(df_prev_diff, on='MGB_6', how='left')

    # Fonction de style pour mettre en orange si différence a changé
    def highlight_diff_change(row):
        if pd.notna(row['Difference_précédente']) and row['Difference_MMS-WMS'] != row['Difference_précédente']:
            return ['background-color: #FFA500'] * len(row)
        else:
            return [''] * len(row)
    col1, col2 = st.columns(2)
    col1.markdown(
        "<div style='background-color:#FFA500; padding:10px; border-radius:5px;'>"
        "Lignes Oranges => Différence_MMS-WMS changé depuis la dernière vérification."
        "</div>",
        unsafe_allow_html=True
    )

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

    # Colonnes à afficher pour chaque DataFrame
    cols_inventaire  = ["MGB", "Description","Ref_Metro","Initial_Quantity", "Inventaire_Final_Quantity", "Difference"]
    cols_mvt_stock   = ["Date", "Heure","MGB", "SSCC", "Code_Agent", "Type_Mouvement", "Code_Mouvement", "Info_Mouvement", "Qty_Mouvement","Synchro_MMS"]
    cols_reception   = ["Date", "Heure", "MGB","SSCC", "Date_Camion","N°_Camion","Code_Agent", "Qty_Reception"]
    cols_sorties     = ["Date", "Heure", "Date_de_livraison", "MGB", "Qty_Commandé" , "Qty_Total_Préparé", "N°_Commande"]

    # Filtrer et garder uniquement les colonnes définies
    stock_info      = df_ecart_stock_last[df_ecart_stock_last['MGB_6'] == mgb_selected]
    inventaire_info = df_inventaire[df_inventaire['MGB_6'] == mgb_selected][cols_inventaire]
    mvt_stock_info  = df_mvt_stock[df_mvt_stock['MGB_6'] == mgb_selected][cols_mvt_stock]
    reception_info  = df_reception[df_reception['MGB_6'] == mgb_selected][cols_reception]
    sorties_info    = df_sorties[df_sorties['MGB_6'] == mgb_selected][cols_sorties]

    mvt_stock_info = mvt_stock_info.drop_duplicates().reset_index(drop=True)
    reception_info = reception_info.drop_duplicates().reset_index(drop=True)    
    sorties_info = sorties_info.drop_duplicates("N°_Commande").reset_index(drop=True)

    # Calcul des totaux
    totaux_stock = ajouter_totaux(stock_info, ["MMS_Stock : Metro","WMS_Stock : IDL","Difference_MMS-WMS","Valeur_Difference"])
    totaux_inventaire = ajouter_totaux(inventaire_info, ["Inventaire_Final_Quantity"])
    totaux_mvt_stock = ajouter_totaux(mvt_stock_info, ["Qty_Mouvement"])
    totaux_reception = ajouter_totaux(reception_info, ["Qty_Reception"])
    totaux_sorties = ajouter_totaux(sorties_info, ["Qty_Total_Préparé"])

    # 🔧 CORRECTION UNIQUE : sécurisation des types
    inv_final = pd.to_numeric(totaux_inventaire.get('Inventaire_Final_Quantity', 0), errors='coerce') or 0
    qty_mvt   = pd.to_numeric(totaux_mvt_stock.get('Qty_Mouvement', 0), errors='coerce') or 0
    qty_rec   = pd.to_numeric(totaux_reception.get('Qty_Reception', 0), errors='coerce') or 0
    qty_sort  = pd.to_numeric(totaux_sorties.get('Qty_Total_Préparé', 0), errors='coerce') or 0

    stock_theorique = inv_final + qty_mvt + qty_rec - qty_sort

    # Affichage des métriques
    st.subheader(f"{mgb_selected} - {stock_info.iloc[0]['Désignation'] if not stock_info.empty else ''}")
    plus = "+"
    moins = "-"
    egal = "="
    col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1, 3, 1, 3, 2, 3])
    col1.metric("MMS Stock : Metro", totaux_stock.get("MMS_Stock : Metro", 0))
    col2.metric("", moins)
    col3.metric("WMS Stock : IDL", totaux_stock.get("WMS_Stock : IDL", 0))
    col4.metric("", egal)
    col5.metric("Difference MMS - WMS", totaux_stock.get("Difference_MMS-WMS", 0))
    col6.metric("", "Soit")
    col7.metric("Valeur Difference €", f"{totaux_stock.get('Valeur_Difference', 0):.2f} €")

    # separation :
    st.divider()

    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([3, 1, 3, 1, 3, 1, 3, 1, 3])
    col1.metric("Inventaire", inv_final)
    col2.metric("", plus)
    col3.metric("Mouvements", qty_mvt)
    col4.metric("", plus)
    col5.metric("Réceptions", qty_rec)
    col6.metric("", moins)
    col7.metric("Sorties", qty_sort)
    col8.metric("", egal)
    col9.metric("Stock théorique", round(stock_theorique, 2))

    # Affichage des tableaux détaillés
    st.subheader("Tableau Inventaire")
    st.dataframe(inventaire_info, use_container_width=True)

    st.subheader("Tableau des mouvements de stock")
    st.write(f"{mgb_selected} - {stock_info.iloc[0]['Désignation']}")
    st.write(f"Ref_Merto : {inventaire_info.iloc[0]['Ref_Metro']} - " f" Au_Kg : {'OUI' if stock_info.iloc[0]['Au_Kg'] else 'NON'}")
    col1, col2 = st.columns(2)
    col1.markdown(
        "<div style='background-color:#FF9999; padding:10px; border-radius:5px;'>"
        "Lignes Rouges => Sans Synchro."
        "</div>",
        unsafe_allow_html=True
    )
    col2.markdown(
        "<div style='background-color:#90EE90; padding:10px; border-radius:5px;'>"
        "Lignes Vertes => Avec Synchro."
        "</div>",
        unsafe_allow_html=True
    )
    st.dataframe(mvt_stock_info.style.apply(color_rows, axis=1), use_container_width=True)

    st.subheader("Tableau des réceptions")
    st.write(f"{mgb_selected} - {stock_info.iloc[0]['Désignation']}")
    st.write(f"Ref_Merto : {inventaire_info.iloc[0]['Ref_Metro']} - " f" Au_Kg : {'OUI' if stock_info.iloc[0]['Au_Kg'] else 'NON'}")
    st.dataframe(reception_info, use_container_width=True)

    st.subheader("Tableau des sorties")
    st.write(f"{mgb_selected} - {stock_info.iloc[0]['Désignation']}")
    st.write(f"Ref_Merto : {inventaire_info.iloc[0]['Ref_Metro']} - " f" Au_Kg : {'OUI' if stock_info.iloc[0]['Au_Kg'] else 'NON'}")
    st.dataframe(sorties_info, use_container_width=True)

    # separation :
    st.divider()

    # --- Lecture du chemin du dernier fichier parquet ---
    onedrive_cache_dir = Path(r"\\spwfs-metbre\Partage\11_Public\Data_app\Cache")
    file_last_txt = onedrive_cache_dir / "file_last.txt"


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

    # --------------------------
    # Génération du PDF
    # --------------------------
    if st.button("Générer le PDF du rapport"):
        df_for_pdf = st.session_state.df_comments.copy()
        df_for_pdf = st.session_state.df_comments[
            st.session_state.df_comments["Date_Dernier_Commentaire"].notna() &
            (st.session_state.df_comments["Date_Dernier_Commentaire"] != "")
        ]

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
        # Aujourd'hui
        today_dt = pd.Timestamp.today()

        # Liste des tranches [(min_jours, max_jours, label)]
        tranches = [
            (3, 6, ">3 à 6 jours"),
            (7, 10, ">6 à 10 jours"),
            (11, float("inf"), ">10 jours")
        ]

        retard_data = []

        for min_days, max_days, label in tranches:
            # Sélection non cumulative
            df_days = df_retard[
                ((today_dt - df_retard["Date_Dernier_Commentaire_dt"]).dt.days >= min_days) &
                ((today_dt - df_retard["Date_Dernier_Commentaire_dt"]).dt.days <= max_days)
            ]
            nb_met = len(df_days[df_days["Choix_traitement"] == "METRO"])
            nb_idl = len(df_days[df_days["Choix_traitement"] == "IDL"])
            retard_data.append((label, str(nb_met), str(nb_idl)))


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
            pdf.cell(col_widths[3], 6, str(row["MMS_Stock : Metro"]), border=1, fill=True)
            pdf.cell(col_widths[4], 6, str(row["WMS_Stock : IDL"]), border=1, fill=True)
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
    st.write("Générateur de Détrompeurs à partir d'un MGB.")

    # -------------------- Fichiers --------------------
    fichier_pdf_vierge = r"\\spwfs-metbre\Partage\11_Public\Data_app\Detrompeur\detrompeur_vierge.pdf"
    dossier_sortie = r"\\spwfs-metbre\Partage\11_Public\Data_app\Detrompeur\Detrompeur"
    file_excel_ean = r"\\spwfs-metbre\Partage\11_Public\Data_app\Detrompeur\Liste detrompeur + EAN.xlsx"       
    
    # -------------------- Charger df_ean de manière sûre --------------------
    global df_ean
    try:
        df_ean = pd.read_excel(file_excel_ean, dtype=str)
    except Exception:
        df_ean = pd.DataFrame(columns=["Description", "MGB", "CODE EAN"])

    # -------------------- Charger fichier état stock --------------------
    data_dir = Path(r"\\spwfs-metbre\Partage\11_Public\Data_app\Cache")
    if not data_dir.exists():
        st.error(f"Le dossier cache OneDrive est introuvable : {data_dir}")
        return

    try:
        df_etat_stock = pd.read_parquet(data_dir / "etat_stock.parquet")
    except Exception as e:
        st.error(f"Erreur lors du chargement du cache : {e}")
        return

    # ==================== Liste éditable des détrompeurs existants ====================
    st.subheader("Détrompeurs existants :")
    
    # Préserver les positions
    if 'Position' in df_etat_stock.columns:
        # Transformer Position en str et supprimer les NaN
        df_etat_stock['Position'] = df_etat_stock['Position'].astype(str).replace('nan', '')
        
        # Positions avec "A" d'abord, puis les autres
        def sort_positions(pos_list):
            # Supprimer doublons tout en gardant l'ordre
            pos_list = list(dict.fromkeys([p for p in pos_list if p]))
            
            # Détecter les emplacements : au moins chiffre-chiffre-lettre-chiffre
            pattern = re.compile(r'\d+-\d+-[A-Za-z]\d+-\d+')
            emplacements = [p for p in pos_list if pattern.match(p)]
            autres = [p for p in pos_list if not pattern.match(p)]
            
            # Dans les emplacements, mettre en premier ceux contenant "A"
            emplacements_a = [p for p in emplacements if 'A' in p]
            emplacements_autres = [p for p in emplacements if 'A' not in p]
            
            # Concaténer : emplacements avec A, autres emplacements, puis les autres positions
            sorted_list = emplacements_a + emplacements_autres + autres
            
            return ", ".join(sorted_list)
        
        # Grouper par MGB et concaténer toutes les positions
        positions_grouped = (df_etat_stock.groupby('MGB')['Position'].apply(lambda x: sort_positions(list(x))).reset_index(name='Positions'))
                    
        # Supprimer la colonne Position originale si nécessaire
        df_etat_stock = df_etat_stock.drop(columns=['Position'])

        # Faire le merge sur MGB
        df_etat_stock = df_etat_stock.merge(positions_grouped, on='MGB', how='left')

    else:
        df_etat_stock['Positions'] = ""

    # S'assurer que MGB est string
    df_etat_stock['MGB'] = df_etat_stock['MGB'].astype(str)
         
    # Initialisation session
    if "df_edit" not in st.session_state:
        st.session_state.df_edit = None
    if "pdf_detrompeurs" not in st.session_state:
        st.session_state.pdf_detrompeurs = None

    # Affichage / édition
    if st.button("Afficher / éditer la liste des détrompeurs"):

        if df_etat_stock is None or df_etat_stock.empty:
            st.error("État de stock non disponible.")
            st.stop()

        fichiers = [
            f for f in os.listdir(dossier_sortie)
            if f.lower().startswith("detrompeur_") and f.lower().endswith(".pdf")
        ]

        lignes = []
        for fichier in fichiers:
            mgb = fichier.replace("Detrompeur_", "").replace(".pdf", "")
            ligne_stock = df_etat_stock[df_etat_stock["MGB"] == mgb]

            lignes.append({
                "MGB": mgb,
                "Ref Metro": (
                    ligne_stock["Ref Metro"].iloc[0]
                    if not ligne_stock.empty and "Ref Metro" in df_etat_stock.columns
                    else ""
                ),
                "Désignation": (
                    ligne_stock["Désignation"].iloc[0]
                    if not ligne_stock.empty else ""
                ),
                "Positions": (
                    ligne_stock["Positions"].iloc[0]
                    if not ligne_stock.empty else ""
                ),
                "Cellule": (
                    ligne_stock["Cellule"].iloc[0]
                    if not ligne_stock.empty else ""
                )
            })

        df_detrompeurs = pd.DataFrame(lignes)

        # Extraire Allée pour trier
        df_detrompeurs['Allee'] = df_detrompeurs['Positions'].apply(lambda x: x.split('-')[0] if x else '')
        df_detrompeurs['Rangée'] = df_detrompeurs['Positions'].apply(lambda x: x.split('-')[1] if x and len(x.split('-')) > 1 else '')
        df_detrompeurs['Allee_num'] = df_detrompeurs['Allee'].str.extract(r'(\d+)').astype(float)
        df_detrompeurs['Rangée_num'] = df_detrompeurs['Rangée'].str.extract(r'(\d+)').astype(float) 
        
        # Trier par Cellule puis par Allée
        df_detrompeurs = df_detrompeurs.sort_values(
            by=['Allee_num','Rangée_num','Cellule'],
            na_position='last'
        )

        # ordre des colonnes
        cols = ['Cellule', 'Allee', 'MGB', 'Désignation', 'Ref Metro', 'Positions']
        df_detrompeurs = df_detrompeurs[cols]
        
        # Stocker dans session_state
        st.session_state.df_edit = df_detrompeurs.copy()
        st.dataframe(df_detrompeurs)

    # Génération PDF
    if st.session_state.df_edit is not None:
        if st.button("Générer le PDF des détrompeurs"):

            df_pdf = st.session_state.df_edit.fillna("").astype(str)
            if df_pdf.empty:
                st.error("Aucune donnée à exporter")
                st.stop()
             
            buffer = BytesIO()

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]

            # Fonction pour ajouter titre + numéro de page
            def add_page_number(canvas, doc):
                canvas.saveState()
                page_num_text = f"Page {doc.page}"
                canvas.setFont('Helvetica', 7)
                canvas.drawRightString(A4[1] - 1*cm, 0.75*cm, page_num_text)  # coordonnée pour paysage
                canvas.restoreState()

            pdf = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=1*cm,
                rightMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm
            )

            # Titre
            elements = [Paragraph("Liste des détrompeurs", title_style), Spacer(1, 0.5*cm)]
            
            # Ajouter une colonne Numéro à gauche
            df_pdf.insert(0, "N°", range(1, len(df_pdf)+1))

            data = [df_pdf.columns.tolist()] + df_pdf.values.tolist()
            page_width, _ = landscape(A4)
            usable_width = page_width - 2*cm  # marge gauche/droite

            # Calculer largeur de chaque colonne selon le texte le plus long
            font_name = "Helvetica"
            font_size = 7
            padding = 6  # points de marge à ajouter

            col_widths = []
            for col in df_pdf.columns:
                max_len = max(df_pdf[col].astype(str).map(len).max(), len(col))
                col_widths.append(stringWidth("M" * max_len, font_name, font_size) + padding)

            # Ajuster si la somme dépasse la largeur de la page
            total_width = sum(col_widths)
            if total_width > usable_width:
                scale = usable_width / total_width
                col_widths = [w * scale for w in col_widths]

            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            elements.append(table)

            pdf.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
            buffer.seek(0)

            st.session_state.pdf_detrompeurs = buffer.getvalue()
            st.success("PDF généré")

        # Téléchargement
        if st.session_state.pdf_detrompeurs:
            st.download_button(
                "Télécharger la liste des détrompeurs (PDF)",
                data=st.session_state.pdf_detrompeurs,
                file_name="liste_detrompeurs.pdf",
                mime="application/pdf"
            )


    # -------------------- Saisie MGB avec suggestions --------------------
    st.subheader("Créer un Détrompeur :")
    col1, col2 = st.columns(2)

    with col1:
        liste_mgb = df_etat_stock['MGB'].dropna().unique()
        st.markdown("<h5>Taper le MGB ici et appuyer sur Entrée</h5>", unsafe_allow_html=True)
        mgb_saisie = st.text_input("", label_visibility="collapsed")

        suggestions = [m for m in liste_mgb if mgb_saisie.upper() in str(m).upper()]
    with col2:
        if suggestions:
            st.markdown("<h5>Suggestions de MGB</h5>", unsafe_allow_html=True)
            mgb_input = st.selectbox("", options=suggestions, label_visibility="collapsed")
        else:
            mgb_input = mgb_saisie

    # -------------------- Lecture immédiate de la désignation --------------------
    if mgb_input:
        ligne_mgb = df_etat_stock[df_etat_stock["MGB"] == mgb_input]

        if not ligne_mgb.empty:
            designation_preview = ligne_mgb["Désignation"].values[0]
            st.info(f"🔎 Désignation trouvée : **{designation_preview}**")

    # -------------------- choix de la prise --------------------
    
    st.markdown("<h5>Type de prise :</h5>", unsafe_allow_html=True)
    type_prise = st.selectbox(
        "",
        ["COLIS", "PIECE", "POIDS"],
        index=0, 
        label_visibility="collapsed"
    )


    # -------------------- Aperçu PDF existant --------------------
    nom_fichier = f"Detrompeur_{mgb_input}.pdf"
    chemin_final = os.path.join(dossier_sortie, nom_fichier)

    if os.path.exists(chemin_final):
        st.warning("Un PDF pour ce MGB existe déjà :")

        pdf = fitz.open(chemin_final)
        page = pdf[0]
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        st.image(img_bytes, caption="Aperçu du PDF existant", use_container_width=True)

        modifier = st.radio("Voulez-vous le modifier ?", ["Non", "Oui"])

        if modifier == "Non":
            st.download_button(
                label="Télécharger le PDF existant",
                data=open(chemin_final, "rb").read(),
                file_name=nom_fichier,
                mime="application/pdf"
            )
            return  # pas de modification
        else:
            st.markdown("<h5>✅Charger la photo OK✅ (.jpeg) : </h5>", unsafe_allow_html=True)
            photo_ok = st.file_uploader("", type=['jpeg'], label_visibility="collapsed", key="photo_ok_uploader")
            st.markdown("<h5>❌Charger la photo KO❌ (.jpeg) : </h5>", unsafe_allow_html=True)
            photo_ko = st.file_uploader("", type=['jpeg'], label_visibility="collapsed", key="photo_ko_uploader")
    else:
        st.markdown("<h5>✅Charger la photo OK✅ (.jpeg) : </h5>", unsafe_allow_html=True)
        photo_ok = st.file_uploader("", type=['jpeg'], label_visibility="collapsed", key="photo_ok_uploader")
        st.markdown("<h5>❌Charger la photo KO❌ (.jpeg) : </h5>", unsafe_allow_html=True)
        photo_ko = st.file_uploader("", type=['jpeg'], label_visibility="collapsed")

    # -------------------- Récupération données MGB --------------------
    ligne = df_etat_stock[df_etat_stock['MGB'] == mgb_input]

    if ligne.empty:
        st.error("MGB non trouvé dans l'état stock.")
        return

    designation = ligne['Désignation'].values[0]
    ref_metro = str(ligne['Ref Metro'].values[0]).split('.')[0]
    ean = ligne['EAN'].values[0]

    # -------------------- EAN --------------------
    ean_existant = ""

    # Normaliser l’EAN s’il existe
    if pd.notna(ean):
        if isinstance(ean, (float, np.floating, int)):
            ean_existant = str(int(float(ean)))
        else:
            ean_existant = str(ean)

    # Cas 1 : EAN déjà présent → affichage info uniquement
    if ean_existant:
        st.info(f"L’EAN existant pour ce MGB : {ean_existant}")
        ean = ean_existant
        force_pdf = False

    # Cas 2 : aucun EAN → afficher input + checkbox
    else:
        ean = st.text_input("Ajouter l’EAN manuellement :")
        if not ean:
            force_pdf = st.checkbox("Forcer la création du PDF même sans EAN")
        else:
            force_pdf = False


    # -------------------- Bouton de création du PDF --------------------
    if st.button("Créer PDF"):
        if not ean and not force_pdf:
            st.error("Veuillez saisir un EAN ou cocher 'Forcer la création du PDF'.")
            return

        # --- Mise à jour Excel si EAN saisi ---
        if ean:
            if mgb_input in df_ean['MGB'].values:
                df_ean.loc[df_ean['MGB'] == mgb_input, 'CODE EAN'] = ean
            else:
                nouvelle_ligne = pd.DataFrame([{
                    "Désignation": designation,
                    "MGB": mgb_input,
                    "CODE EAN": ean
                }])
                df_ean = pd.concat([df_ean, nouvelle_ligne], ignore_index=True)

            df_ean.to_excel(file_excel_ean, index=False)
            st.success(f"EAN {ean} ajouté/modifié dans le fichier EAN.")

        # -------------------- Génération du PDF --------------------
        ean_final = ean if ean else ""
        st.success(f"PDF créé pour le MGB {mgb_input} avec l’EAN {ean_final}.")

        # --- Créer PDF temporaire avec texte et images ---
        buffer_txt = BytesIO()
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer_txt, pagesize=(page_width, page_height))

        # Texte
        x_start = 20
        y_start = page_height - 160
        max_width = page_width / 2 - 50
        max_lines = 3

        # Taille initiale de la police
        font_name = "Helvetica-Bold"
        font_size = 36
        min_font_size = 10

        words = designation.split()

        while font_size >= min_font_size:
            lines = []
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                if c.stringWidth(test_line, font_name, font_size) <= max_width:
                    line = test_line
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)

            if len(lines) <= max_lines:
                break  # OK, le texte tient
            font_size -= 2  # réduire la taille et réessayer

        # Affichage du texte
        text_obj = c.beginText()
        text_obj.setTextOrigin(x_start, y_start)
        text_obj.setFont(font_name, font_size)
        text_obj.setFillColor(colors.darkblue)
        for l in lines:
            text_obj.textLine(l)
        c.drawText(text_obj)

        # ref metro
        c.setFont("Helvetica-Bold", 38)
        c.setFillColor(colors.darkblue)    
        c.drawString(x_start + 220, y_start - 150, f"{ref_metro}")

        # Type de prise (COLIS / PIECE / POIDS)
        c.setFont("Helvetica-Bold", 38)
        c.setFillColor(colors.darkblue)
        c.drawString(x_start + 200, y_start - 210, f"{type_prise}")


        # --- Fonctions QR, EAN, croix rouge et redimensionnement ---
        def generate_qr(MGB):
            qr_img = qrcode.make(MGB).convert("RGB")
            qr_size = 100
            qr_img = qr_img.resize((qr_size, qr_size))
            return qr_img, qr_size, qr_size

        def generate_ean(ean_code: str):
            if not ean_code:
                return None, 0, 0
            if len(ean_code) == 13:
                ean = EAN13(ean_code, writer=ImageWriter())
            elif len(ean_code) == 8:
                ean = EAN8(ean_code, writer=ImageWriter())
            else:
                st.error("Le code EAN doit faire 8 ou 13 chiffres.")
                st.stop()
            buffer = BytesIO()
            ean.write(buffer)
            buffer.seek(0)
            ean_img = Image.open(buffer)
            ean_width, ean_height = 300, 150
            ean_img = ean_img.resize((ean_width, ean_height))
            return ean_img, ean_width, ean_height

        def ajouter_croix_rouge(image_stream):
            img = Image.open(image_stream).convert("RGBA")
            draw = ImageDraw.Draw(img)
            w, h = img.size
            thickness = max(25, w // 100)
            draw.line((0, 0, w, h), fill=(255, 0, 0, 255), width=thickness)
            draw.line((0, h, w, 0), fill=(255, 0, 0, 255), width=thickness)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer

        def get_image_size(file, max_width, max_height):
            if isinstance(file, Image.Image):
                img = file
            else:
                img = Image.open(file)
            if img.width > img.height:
                img = img.rotate(90, expand=True)
            target_ratio = 2 / 3
            w, h = img.size
            current_ratio = w / h
            if current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            elif current_ratio < target_ratio:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))
            ratio = min(max_width / img.width, max_height / img.height)
            return img, img.width * ratio, img.height * ratio

        quart_width = page_width * 0.25
        max_width_img = quart_width - 20
        max_height_img = page_height - 100
        decalage = 15

        # QR code
        qr_img, qr_w, qr_h = generate_qr(mgb_input)
        x_qr = page_width - qr_w - 10
        y_qr = page_height - qr_h - 10
        c.drawImage(ImageReader(qr_img), x_qr, y_qr, width=qr_w, height=qr_h)

        # EAN
        ean_img, ean_w, ean_h = generate_ean(ean)
        if ean_img:
            x_ean = 50
            y_ean = 50
            c.drawImage(ImageReader(ean_img), x_ean, y_ean, width=ean_w, height=ean_h)

        # Photos OK/KO
        if photo_ok:
            img, img_w, img_h = get_image_size(photo_ok, max_width_img, max_height_img)
            x_ok = page_width * 0.75 + (quart_width - img_w) / 2 - decalage
            y_ok = page_height / 2 - img_h / 2
            c.drawImage(ImageReader(img), x_ok, y_ok, width=img_w, height=img_h)

        if photo_ko:
            photo_ko_marked = ajouter_croix_rouge(photo_ko)
            img, img_w, img_h = get_image_size(photo_ko_marked, max_width_img, max_height_img)
            x_ko = page_width * 0.5 + (quart_width - img_w) / 2 - decalage
            y_ko = page_height / 2 - img_h / 2
            c.drawImage(ImageReader(img), x_ko, y_ko, width=img_w, height=img_h)

        c.save()
        buffer_txt.seek(0)

        # --- Fusionner avec PDF vierge ---
        reader_vierge = PdfReader(fichier_pdf_vierge)
        writer = PdfWriter()
        page_vierge = reader_vierge.pages[0]
        reader_txt = PdfReader(buffer_txt)
        page_txt = reader_txt.pages[0]
        page_vierge.merge_page(page_txt)
        writer.add_page(page_vierge)

        # --- Enregistrer PDF final ---
        nom_fichier = f"Detrompeur_{mgb_input}.pdf"
        chemin_final = f"{dossier_sortie}\\{nom_fichier}"
        with open(chemin_final, "wb") as f_out:
            writer.write(f_out)

        st.success(f"PDF généré avec succès et enregistré sous : {chemin_final}")
        st.download_button("Télécharger PDF", data=open(chemin_final, "rb").read(),
                        file_name=nom_fichier, mime="application/pdf")

def Inventaire():
    st.title("Inventaire")

    # -------------------- Charger fichier état stock --------------------
    # -------------------- Dossier Cache Streamlit --------------------
    # Tous les fichiers temporaires / Parquet seront ici
    data_dir = Path(".streamlit/Cache")
    data_dir.mkdir(parents=True, exist_ok=True)

    # -------------------- Inventaire versionné Git --------------------
    BASE_DIR = Path(__file__).resolve().parent.parent  # racine du projet
    Fond_inventaire = BASE_DIR / "data_app" / "Inventaire" / "Fond_inventaire.pdf"
    dossier_archive_inventaire = BASE_DIR / "data_app" / "Inventaire" / "Archive"
    dossier_archive_inventaire.mkdir(parents=True, exist_ok=True)

    # -------------------- Historique (cache) --------------------
    dossier_historique_inventaire = data_dir / "Historique"
    dossier_historique_inventaire.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        st.error(f"Le dossier cache OneDrive est introuvable : {data_dir}")
        return

    try:
        df_etat_stock = pd.read_parquet(data_dir / "etat_stock.parquet")
    except Exception as e:
        st.error(f"Erreur lors du chargement du cache : {e}")
        return

    df_etat_stock["Position"] = df_etat_stock["Position"].fillna("").astype(str)
    df_etat_stock['Allee'] = df_etat_stock["Position"].str.split("-").str[0]
   
    # remplir les lignes où Cellule est vide ou "Inconnu"
    Liste_allée = {
        "Ambiant": ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18'],
        "Frais": ['19','20','21','22','23','24','25','26','27','28','29'],
        "FL": ['30','31','32','33','34','35','36','37'],
        "Surgelé": ['38','39','40','41','42','43','44','45','46','47','48','49'],
        "Marée": ['50','51','52','53','54','55','56','57','58','59','60']
    }

    def determine_cellule(position):
        if not position:
            return "Inconnu"

        positions = [p.strip() for p in position.split(',')]
        for pos in positions:
            allee = pos.split('-')[0]
            for cellule, allees in Liste_allée.items():
                if allee in allees:
                    return cellule
        return "Inconnu"

    # 🔹 Masque : uniquement lignes à corriger
    mask = (
        df_etat_stock['Cellule'].isna() |
        (df_etat_stock['Cellule'] == '') |
        (df_etat_stock['Cellule'] == 'Inconnu')
    )

    df_etat_stock.loc[mask, 'Cellule'] = (
        df_etat_stock.loc[mask, 'Position']
        .apply(determine_cellule)
    )


    # Trier par Cellule puis par Allée
    # Fonction pour transformer la position en tuple sortable
    def position_to_tuple(pos):
        if not pos:
            return (0,0,'',0)
        parts = pos.split('-')
        if len(parts) != 4:
            return (0,0,'',0)  # fallback si format incorrect
        try:
            first = int(parts[0])
        except:
            first = 0
        try:
            second = int(parts[1])
        except:
            second = 0
        # segment 3 : lettre + chiffre
        m = re.match(r'([A-Za-z])(\d+)', parts[2])
        if m:
            lettre = m.group(1)
            chiffre = int(m.group(2))
            third = (lettre, chiffre)
        else:
            third = ('',0)
        try:
            fourth = int(parts[3])
        except:
            fourth = 0
        return (first, second, third, fourth)

    # Trier par Cellule puis par Position
    df_etat_stock = df_etat_stock.sort_values(
        by=['Cellule', 'Position'],
        key=lambda col: col.map(lambda x: position_to_tuple(x)) if col.name=='Position' else col
    )

    # Regex pour extraire la lettre de l'emplacement : XX-XX-LX-XX
    pattern = re.compile(r'\d+-\d+-([A-Za-z])\d+-\d+')

    # Extraire toutes les lettres d'une position
    def lettres_position(position):
        if not position:
            return set()
        lettres = set()
        for p in position.split(','):
            m = pattern.search(p.strip())
            if m:
                lettres.add(m.group(1).upper())
        return lettres

    # Ajouter une colonne temporaire avec les lettres pour chaque ligne
    df_etat_stock['Lettres'] = df_etat_stock['Position'].apply(lettres_position)

    # Fonction pour détecter s'il existe d'autres lettres différentes pour le même MGB
    def detect_autres(group):
        # Toutes les lettres du groupe
        lettres_group = list(group['Lettres'])
        autres_picking_a = []
        autres_stock = []

        for i, lettres_i in enumerate(lettres_group):
            # Lettres A dans la ligne
            has_a_i = 'A' in lettres_i
            # Lettres différentes de A
            other_i = {l for l in lettres_i if l != 'A'}

            # Comparer avec toutes les autres lignes du même MGB
            autres_lignes = lettres_group[:i] + lettres_group[i+1:]
            # Autre Picking_A ?
            autres_a = any('A' in l and l != lettres_i for l in autres_lignes)
            # Autre Stock ?
            autres_s = any(any(l != 'A' for l in lset) for lset in autres_lignes)

            autres_picking_a.append(autres_a)
            autres_stock.append(autres_s)

        group = group.copy()
        group['Autre_Picking'] = autres_picking_a
        group['Autre_Stock'] = autres_stock
            
        # S’assurer que ce sont bien des bools
        group['Autre_Picking'] = group['Autre_Picking'].astype(bool)
        group['Autre_Stock'] = group['Autre_Stock'].astype(bool)
        return group

    # Appliquer par MGB
    df_etat_stock = df_etat_stock.groupby('MGB', group_keys=False).apply(detect_autres)

    # Fonction pour extraire l'allée paire/impaire
    def pair_impair(position):
        if not position:
            return None
        parts = position.split('-')
        if len(parts) < 2:
            return None
        try:
            chiffre2 = int(parts[1])  # 2ᵉ segment
            return 'Pair' if chiffre2 % 2 == 0 else 'Impair'
        except:
            return None
    
    # Supprimer les valeurs non désirées
    df_etat_stock = df_etat_stock[
        (df_etat_stock['Cellule'] != "Inconnu") &
        (~df_etat_stock['Allee'].isin(["INSPECTION", "UNLOADING", "IN", "CROSS_DOCKING"]))&
        (df_etat_stock['Position'].str.strip() != "")
    ]

    # Créer colonne Paire/Impaire
    df_etat_stock['Pair_Impair'] = df_etat_stock['Position'].apply(pair_impair)

    
    # Extraire les options uniques
    cellules = sorted(df_etat_stock['Cellule'].dropna().unique())
    allees = sorted(df_etat_stock['Allee'].dropna().unique())
    gas = sorted(df_etat_stock['GA'].dropna().unique())
    sas = sorted(df_etat_stock['SA'].dropna().unique())
    paires = sorted(df_etat_stock['Pair_Impair'].dropna().unique())

    # --- Filtrage progressif des options ---
    # Copier le dataframe pour filtrage dynamique
    df_tmp = df_etat_stock.copy()
    
    liste_Intitulé = ["Alcool", "Boucherie", "Ambiant", "Frais", "FL", "Marée", "Surglé", "Autre"]
    Intitulé = st.selectbox("Choisir l'intitulé d'inventaire", liste_Intitulé)

    # --- 1. Filtre Cellule ---
   
    cellules = sorted(df_tmp['Cellule'].dropna().unique())
    cellule_sel = st.radio(
        "Cellule",
        options=[""] + cellules,
        index=0,
        horizontal=True,
        key="filtre_cellule"
    )
    if cellule_sel :
        df_tmp = df_tmp[df_tmp['Cellule'] == cellule_sel]
        
        # Créer 5 colonnes pour les filtres
        col1, col2, col3, col4, col5 = st.columns(5)
        # --- 2. Filtre Allée (apparait seulement après Cellule choisie) ---
        with col1:
            if not df_tmp.empty:
                allees = sorted(df_tmp['Allee'].dropna().unique())
                allee_sel = st.selectbox(
                    "Allée",
                    options=[""] + allees,
                    index=0,
                    key="filtre_allee"
                )
            if allee_sel :
                df_tmp = df_tmp[df_tmp['Allee'] == allee_sel]

        # --- 3. Filtre SA (multiple) ---
        with col2:
            if not df_tmp.empty:
                sas = sorted(df_tmp['SA'].dropna().unique())
                sa_sel = st.multiselect(
                    "SA",
                    options=sas,
                    key="filtre_sa"
                )

            if sa_sel:
                df_tmp = df_tmp[df_tmp['SA'].isin(sa_sel)]


        # --- 4. Filtre GA (multiple) ---
        with col3:
            if not df_tmp.empty:
                gas = sorted(df_tmp['GA'].dropna().unique())
                ga_sel = st.multiselect(
                    "GA",
                    options=gas,
                    key="filtre_ga"
                )

            if ga_sel:
                df_tmp = df_tmp[df_tmp['GA'].isin(ga_sel)]

        # --- 5. Filtre Picking / Hauteur ---
        with col4:
            if "Lettres" in df_tmp.columns and not df_tmp.empty:
                    # convertir les sets en chaînes pour pouvoir filtrer
                    df_tmp["Lettres"] = df_tmp["Lettres"].apply(
                        lambda x: ",".join(sorted(x)) if isinstance(x, set) else str(x).strip()
                    )

                    # selectbox Picking / Hauteur
                    picking_sel = st.selectbox(
                        "Picking / Hauteur",
                        options=["", "Picking", "Hauteur"],
                        key="filtre_picking_hauteur"
                    )

                    # filtrage
                    if picking_sel == "Picking":
                        df_tmp = df_tmp[df_tmp["Lettres"] == "A"]

                    elif picking_sel == "Hauteur":
                        df_tmp = df_tmp[df_tmp["Lettres"].isin(["B", "C", "D"])]

        
        # --- 6. Filtre Paire/Impaire ---
        paire_sel = None
        with col5:
            if not df_tmp.empty:
                paires = sorted(df_tmp['Pair_Impair'].dropna().unique())
                paire_sel = st.selectbox(
                    "Pair/Impair",
                    options=[""] + paires,
                    index=0,
                    key="filtre_pair_impair"
                )
            if paire_sel :
                df_tmp = df_tmp[df_tmp['Pair_Impair'] == paire_sel]

    st.subheader("Aperçu du DataFrame filtré")
    # Compter les emplacements uniques après filtrage
    if "Position" in df_tmp.columns and not df_tmp.empty:
        nb_emplacements = df_tmp["Position"].nunique()
        st.write(f"Nombre d'emplacements distincts : {nb_emplacements}")
    else:
        st.write("Aucun emplacement disponible après filtrage.")
    
    # vérifier que ces colonnes existent dans df_tmp
    cols_to_show = ["Position", "Désignation", "MGB", "DLC","Prix_Unitaire" ,"Autre_Picking", "Autre_Stock", "Qty_Stock"]
    cols_to_show = [c for c in cols_to_show if c in df_tmp.columns]
    df_tmp = df_tmp[cols_to_show]

    st.dataframe(df_tmp)

    # --------------------------
    # Génération PDF
    # --------------------------
    # ----------------------------------------------
    # --- recuperation filtre choisi pour le PDF ---
    # ----------------------------------------------
    def get_filters_for_pdf():
        l1 = []
        l2 = []
        l3 = []
        l4 = []

        if st.session_state.get("filtre_cellule"):
            l1.append(f"Cellule : {st.session_state['filtre_cellule']}")

        if st.session_state.get("filtre_allee"):
            l1.append(f"Allée : {st.session_state['filtre_allee']}")

        if st.session_state.get("filtre_sa"):
            l2.append(f"SA : {', '.join(st.session_state['filtre_sa'])}")

        if st.session_state.get("filtre_ga"):
            l3.append(f"GA : {', '.join(st.session_state['filtre_ga'])}")

        if st.session_state.get("filtre_picking_hauteur"):
            l4.append(f"Type emplacement : {st.session_state['filtre_picking_hauteur']}")

        if st.session_state.get("filtre_pair_impair"):
            l4.append(f"{st.session_state['filtre_pair_impair']}")

        return (" | ".join(l1),
                " | ".join(l2),
                " | ".join(l3),
                " | ".join(l4),
                )

    #-------------------------
    # --- Création Tableau ---
    # ------------------------

    # --- Préparer le DataFrame ---
    df_export = df_tmp.copy()
    df_export["Qty_Phys."] = "_____"
    df_export["Ecart"] = "______"

    # Dictionnaire de renommage : clé = nom actuel, valeur = nom à afficher
    renommage_colonnes = {
        "Autre_Picking": "Autre Pick.",
        "Prix_Unitaire": "Prix",
        "Autre_Stock": "Autre Stock",
        "Qty_Stock": "Qty WMS",
        "Qty_Phys.": "Qty Phys.",
        "Ecart": "Écart"
    }
    df_export = df_export.rename(columns=renommage_colonnes)

    # Conversion Prix en format "xx,xx €"
    df_export["Prix"] = df_export["Prix"].apply(
        lambda x: f"{float(x):.2f} €" if pd.notna(x) else ""
    )

    df_export["Qty WMS"] = df_export["Qty WMS"].round(2)                               
    
    # Sauvegarde du DataFrame exporté en parquet (avec colonnes booléennes)
    df_export["Autre Pick. B"] = df_export["Autre Pick."]
    df_export["Autre Stock B"] = df_export["Autre Stock"]

    styles = getSampleStyleSheet()
    style_checkbox = styles["Normal"]
    style_checkbox.fontSize = 12
    style_checkbox.alignment = 1  # centré
    for col in ["Autre Pick.", "Autre Stock"]:
        df_export[col] = df_export[col].apply(
            lambda x: Paragraph('<font color="green">&#10003;</font>', style_checkbox) if x else Paragraph("", style_checkbox)
        )

    # --- Paramètres page ---
    page_width, page_height = A4
    margin = 20
    row_height = 24
    y_offset = 200
    max_rows_per_page = int((page_height - y_offset*1.3) / row_height)

    def limit_to_two_lines(text, col_width, font="Helvetica", font_size=8):
        if not text:
            return ""

        avg_char_width = stringWidth("ABCDEFGHIJKLMNOPQRSTUVWXYZ", font, font_size) / 26
        max_chars_per_line = int(col_width / avg_char_width)
        max_chars_total = (max_chars_per_line + 6) * 2

        text = str(text).strip()
        if len(text) <= max_chars_total:
            return text

        return text[:max_chars_total - 3] + "..."

    # --- Fonction pour calculer la largeur des colonnes ---
    def get_col_widths(df, page_width, margin):
        col_widths = []
        fixed_total = 0
        for col in df.columns:
            if col in ["Autre Pick.", "Autre Stock"]:
                col_widths.append(35)
                fixed_total += 35
            elif col == "Position":
                col_widths.append(page_height/16) 
            elif col == "Désignation":
                col_widths.append(page_height/4.4) 
            else:
                max_len = stringWidth(str(col), "Helvetica", 8)
                for val in df[col]:
                    w = stringWidth(str(val), "Helvetica", 8)
                    if w > max_len:
                        max_len = w
                max_len += 6
                col_widths.append(max_len)
                fixed_total += max_len
        # largeur restante pour Désignation
        available_width = page_width - 2*margin - fixed_total
        col_widths = [available_width if w is None else w for w in col_widths]
        return col_widths

    def create_table_page(df_page, col_widths, page_num=1, total_pages=1, filters_lines=None):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        # --- Impression du titre et des filtres avec retour à la ligne ---
        styles = getSampleStyleSheet()
        style_title = styles["Heading2"]
        style_title.fontName = "Helvetica-Bold"

        # Titre principal
        c.setFont("Helvetica-Bold", 20)
        c.drawString(margin*10, page_height - margin*2, f"Inventaire {Intitulé} du {date_str}")

        # Nb emplacements
        c.setFont("Helvetica", 16)
        c.drawString(margin, page_height - y_offset*0.55, f"Nombre d'emplacements : {nb_emplacements}  -  Nombre de pages : {total_pages}")

        # Récupération des lignes de filtres
        # --- Récupération des filtres ---
        if filters_lines is not None:
            line1, line2, line3, line4 = filters_lines
        else:
            line1, line2, line3, line4 = get_filters_for_pdf()

        c.setFont("Helvetica", 12)
        y_filters = page_height - y_offset*0.60
        max_width = page_width - 2*margin

        def draw_wrapped_line(text, y):
            if not text:
                return y
            # Paragraph avec retour automatique
            p = Paragraph(text, styles["Normal"])
            w, h = p.wrap(max_width, 1000)
            p.drawOn(c, margin, y - h)
            return y - h - 2  # espace entre lignes

        y_filters = draw_wrapped_line(line1, y_filters)
        y_filters = draw_wrapped_line(line2, y_filters)
        y_filters = draw_wrapped_line(line3, y_filters)
        y_filters = draw_wrapped_line(line4, y_filters)

        # --- Préparation du DataFrame pour le tableau ---
        styleN = styles["Normal"]
        styleN.fontName = "Helvetica"
        styleN.fontSize = 8
        styleN.leading = 10
        styleN.alignment = 1
        styleN.wordWrap = 'CJK'

        df_page_copy = df_page.copy()
        designation_col_index = df_page.columns.get_loc("Désignation")
        designation_width = float(col_widths[designation_col_index])

        # Limiter Désignation à 2 lignes
        df_page_copy["Désignation"] = df_page_copy["Désignation"].apply(
            lambda x: Paragraph(limit_to_two_lines(x, designation_width), styleN)
        )

        # Titres sur 2 lignes
        headers = [Paragraph(col.replace(" ", "<br/>"), styleN) for col in df_page_copy.columns]
        data = [headers] + df_page_copy.values.tolist()

        num_rows = len(data)
        row_heights_list = [row_height] * num_rows

        table = Table(
            data,
            colWidths=col_widths,
            rowHeights=row_heights_list,
            repeatRows=1
        )

        # --- Styles ---
        table_style = TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ])

        # Indices des colonnes colorées
        col_autre = [df_page_copy.columns.get_loc("Autre Pick."),
                    df_page_copy.columns.get_loc("Autre Stock")]
        col_qty = [df_page_copy.columns.get_loc("Qty Phys."),
                df_page_copy.columns.get_loc("Écart")]

        # Couleurs lignes + colonnes
        for row in range(1, len(data)):
            # Lignes alternées gris très clair
            bg_shade = 0.50 if row % 2 == 0 else 1.0
            table_style.add('BACKGROUND', (0,row), (-1,row), colors.Color(bg_shade, bg_shade, bg_shade, alpha=0.1))

            # Colonnes jaune
            for ca in col_autre:
                color = colors.Color(1.0, 1.0, 0.85) if row % 2 == 0 else colors.Color(1.0, 1.0, 0.7)
                table_style.add('BACKGROUND', (ca,row), (ca,row), color)

            # Colonnes rouge
            for cq in col_qty:
                color = colors.Color(1.0, 0.8, 0.8) if row % 2 == 0 else colors.Color(1.0, 0.6, 0.6)
                table_style.add('BACKGROUND', (cq,row), (cq,row), color)

        table.setStyle(table_style)

        # --- Dessin du tableau en dessous des filtres ---
        table_y = page_height - y_offset
        table.wrapOn(c, page_width - 2*margin, table_y)
        table.drawOn(c, margin, table_y - row_height * num_rows)

        # --- Pagination en bas de page ---
        c.setFont("Helvetica", 10)
        pagination_text = f"Page {page_num} / {total_pages}"
        c.drawRightString(page_width - margin, 15, pagination_text)

        c.save()
        buffer.seek(0)
        return buffer
    
    # --- Paramètres PDF ---
    date_str = datetime.now().strftime("%d-%m-%Y")
    pdf_base_path = os.path.join(dossier_archive_inventaire, f"Inventaire_{Intitulé}_{date_str}.pdf")

    # --- Vérifier si le fichier existe ---
    if os.path.exists(pdf_base_path):
        st.warning(f"Le fichier {os.path.basename(pdf_base_path)} existe déjà !")
        
        option = st.radio(
            "Que voulez-vous faire ?",
            options=["Écraser le fichier existant", "Créer un nom alternatif"]
        )

        if option == "Créer un nom alternatif":
            base, ext = os.path.splitext(pdf_base_path)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            pdf_final_path = f"{base}_{i}{ext}"
            st.info(f"Un nouveau nom sera utilisé : {os.path.basename(pdf_final_path)}")

        elif option == "Écraser le fichier existant":
            pdf_final_path = pdf_base_path
            st.info("Le fichier existant sera écrasé")
    else:
        pdf_final_path = pdf_base_path
    
    if st.button("Générer le PDF de l'inventaire"):

        if df_tmp is None or df_tmp.empty:
            st.error("Aucune donnée à exporter")
            st.stop()
        
        # --- Fusion avec fond ---
        df_export_pdf = df_export.copy()

        df_export_pdf = df_export_pdf.drop(columns=["Autre Pick. B", "Autre Stock B"], errors="ignore")

        doc_fond = fitz.open(Fond_inventaire)
        doc_final = fitz.open()

        col_widths = get_col_widths(df_export_pdf, page_width, margin)

        total_pages = math.ceil(len(df_export_pdf)/max_rows_per_page)

        for i in range(0, len(df_export_pdf), max_rows_per_page):
            df_page = df_export_pdf.iloc[i:i+max_rows_per_page]
            page_num = i//max_rows_per_page + 1
            table_buffer = create_table_page(df_page, col_widths, page_num=page_num, total_pages=total_pages, filters_lines=None)
            tbl_pdf = fitz.open("pdf", table_buffer.getvalue())

            page_fond = doc_fond[0]
            new_page = doc_final.new_page(width=page_fond.rect.width, height=page_fond.rect.height)
            new_page.show_pdf_page(new_page.rect, doc_fond, 0)
            new_page.show_pdf_page(new_page.rect, tbl_pdf, 0)

            tbl_pdf.close()

        # Génération du PDF
        doc_final.save(pdf_final_path)
        doc_final.close()
        doc_fond.close()

        with open(pdf_final_path, "rb") as f:
            pdf_bytes = f.read()

        st.success(f"PDF inventaire généré : {pdf_final_path}")
        st.download_button(
            label="Télécharger le PDF",
            data=pdf_bytes,
            file_name=os.path.basename(pdf_final_path),
            mime="application/pdf"
        )
        # --- Historiser le DataFrame ---
        df_export_parquet = df_export.copy()

        df_export_parquet = df_export_parquet.drop(columns=["Autre Pick.", "Autre Stock"], errors="ignore")

        df_export_parquet.rename(columns={"Autre Pick. B": "Autre Pick.",
                                        "Autre Stock B": "Autre Stock"}, inplace=True)
        order_cols = [
            "Position", "Désignation", "MGB", "DLC", "Prix",
            "Autre Pick.", "Autre Stock", "Qty WMS", "Qty Phys.", "Écart"
        ]
        df_export_parquet = df_export_parquet[order_cols]

        # Récupération filtres et du nb_emplacements: 
        f_cellule, f_sa, f_ga, f_type = get_filters_for_pdf()

        # Colonnes filtres (mêmes valeurs sur toutes les lignes) :
        df_export_parquet["Filtre_Cellule"] = f_cellule
        df_export_parquet["Filtre_SA"] = f_sa
        df_export_parquet["Filtre_GA"] = f_ga
        df_export_parquet["Filtre_Type"] = f_type
        df_export_parquet["Nb_Emplacements"] = nb_emplacements

        # Maintenant on peut sauver
        # Nom du fichier identique au PDF mais dans le dossier historique
        file_name = Path(pdf_final_path).name  # récupère juste "Inventaire_XXX_01-01-2026.pdf"
        file_hist_path = Path(dossier_historique_inventaire) / file_name
        file_hist_path = file_hist_path.with_suffix(".parquet")
        df_export_parquet.to_parquet(file_hist_path, engine='pyarrow', index=False)

        st.info(f"Historique du DataFrame sauvegardé : {os.path.basename(file_hist_path)}")
    
    # separation :
    st.divider()

    st.header("Inventaire à traiter")

    # --- Liste les fichiers historiques ---
    hist_files = sorted([f for f in os.listdir(dossier_historique_inventaire) if f.lower().endswith(".parquet")])
    if not hist_files:
        st.info("Aucun inventaire en historique à traiter")
        st.stop()

    selected_file = st.selectbox("Sélectionner un inventaire à traiter", [""] + hist_files)
    if selected_file == "":
        st.info("Veuillez sélectionner un inventaire")
        st.stop()

    file_path = os.path.join(dossier_historique_inventaire, selected_file)
    df_hist = pd.read_parquet(file_path, engine='pyarrow')

    f_cellule = df_hist["Filtre_Cellule"].iloc[0]
    f_sa      = df_hist["Filtre_SA"].iloc[0]
    f_ga      = df_hist["Filtre_GA"].iloc[0]
    f_type    = df_hist["Filtre_Type"].iloc[0]
    nb_emplacements = df_hist["Nb_Emplacements"].iloc[0]    

    filters_line_1 = f_cellule
    filters_line_2 = f_sa
    filters_line_3 = f_ga
    filters_line_4 = f_type

    df_hist = df_hist.drop(
        columns=["Filtre_Cellule", "Filtre_SA", "Filtre_GA", "Filtre_Type", "Nb_Emplacements"],
        errors="ignore"
    )

    df_hist["Qty WMS"] = df_hist["Qty WMS"].round(2)
    
    st.subheader(f"Inventaire à traiter : {selected_file}")
    
    st.markdown("### Saisie des quantités physiques et écarts")

    # --- Initialisation session_state ---
    if "saisie_dict" not in st.session_state:
        st.session_state["saisie_dict"] = {}

    if "mgb_encours" not in st.session_state:
        st.session_state["mgb_encours"] = None

    # --- Sélecteur MGB ---
    mgb_input = st.text_input("Saisir un MGB existant :", key="mgb_input")
    if st.button("Valider MGB"):
        if mgb_input in df_hist["MGB"].tolist():
            st.session_state["mgb_encours"] = mgb_input
        else:
            st.error(f"MGB '{mgb_input}' non trouvé dans le fichier historique.")

    # --- Affichage des lignes du MGB sélectionné ---
    if st.session_state["mgb_encours"]:
        mgb = st.session_state["mgb_encours"]
        df_mgb = df_hist[df_hist["MGB"] == mgb].copy()
        designation = df_mgb.iloc[0]["Désignation"]

        st.markdown(f"### {mgb} - {designation}")

        # Créer un dictionnaire temporaire pour stocker les modifications locales
        saisie_temp = {}
        
        for idx, row in df_mgb.iterrows():
            page = int((idx + 1) // max_rows_per_page + 1)
            ligne = (idx + 1)-((page - 1) * max_rows_per_page)
            col1, col2, col3 = st.columns([20,10,10])
            with col1 :
                st.markdown(
                    f"""
                    <span style="font-size:14px;"> Page : {page} | ligne : {ligne} </span><br/>
                    <span style="font-size:20px;">
                        Emplacement : {row['Position']} | DLC : {row['DLC']} | Qty WMS : {row['Qty WMS']}
                    </span>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                # Récupérer Qty WMS et forcer en float
                try:
                    qty_wms = float(row["Qty WMS"])
                except (ValueError, TypeError):
                    qty_wms = 0.0

                # Valeur par défaut = saisie précédente ou Qty WMS
                val_defaut = st.session_state.get("saisie_dict", {}).get(idx, {}).get("Qty_Phys.", qty_wms)
                if val_defaut is None:
                    val_defaut = 0.0
                val_defaut = float(val_defaut)

                qty_phys = st.number_input(
                    f"Qty Phys. :",
                    value=val_defaut,
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"qty_{idx}"
                )

            with col3:
                try:
                    qty_wms = float(row["Qty WMS"])
                except (ValueError, TypeError):
                    qty_wms = 0.00
                val_defaut_ecart = qty_phys - qty_wms
                if val_defaut_ecart is None:
                    val_defaut_ecart = 0.00
                val_defaut_ecart = float(val_defaut_ecart)

                st.markdown(f"""
                    <span style="font-size:14px;"> Écart : </span><br/>
                    <span style="font-size:20px;"> {val_defaut_ecart:.2f} </span>
                """, unsafe_allow_html=True)

            saisie_temp[idx] = {
                "Qty Phys.": round(qty_phys, 2),
                "Écart": round(val_defaut_ecart, 2)
            }

    # --- Bouton valider pour ce MGB ---
        if st.button(f"Valider toutes les saisies pour {mgb}", key=f"valider_{mgb}"):
            # Enregistrer dans le dictionnaire global session_state
            st.session_state["saisie_dict"].update(saisie_temp)
            st.success(f"Toutes les lignes pour {mgb} ont été mises à jour.")
            st.session_state["mgb_encours"] = None  # réinitialiser pour saisir un autre MGB

    # --- Bouton pour valider toutes les saisies et générer le PDF final ---
    if st.button("Valider saisies et Archiver"):
        if not st.session_state["saisie_dict"]:
            st.warning("Aucune saisie à valider.")
            st.stop()

        # Mettre à jour df_hist avec toutes les saisies
        for idx, vals in st.session_state["saisie_dict"].items():
            df_hist.loc[idx, "Qty Phys."] = float(vals["Qty Phys."])
            df_hist.loc[idx, "Écart"] = float(vals["Écart"])

        # Colonnes numériques → convertir en str
        for col in ["Qty Phys.", "Écart"]:
            if col in df_hist.columns:
                df_hist[col] = df_hist[col].apply(lambda x: str(x) if pd.notna(x) else "")
        
        for col in ["Autre Pick.", "Autre Stock"]:
            df_hist[col] = df_hist[col].apply(
                lambda x: Paragraph('<font color="green">&#10003;</font>', style_checkbox) if x else Paragraph("", style_checkbox)
            )

        st.success("Toutes les saisies ont été intégrées dans le DataFrame.")

        # --- Génération PDF final ---
        file_name = Path(selected_file).name 
        file_name = Path(file_name)
        file_name = file_name.with_suffix(".pdf")
        pdf_final_path = os.path.join(dossier_archive_inventaire, file_name)

        doc_fond = fitz.open(Fond_inventaire)
        doc_final = fitz.open()
        col_widths = get_col_widths(df_hist, page_width, margin)
        total_pages = math.ceil(len(df_hist)/max_rows_per_page)

        for i in range(0, len(df_hist), max_rows_per_page):
            df_page = df_hist.iloc[i:i+max_rows_per_page]
            page_num = i//max_rows_per_page + 1
            pdf_buffer = create_table_page(df_page=df_page, col_widths=col_widths, page_num=page_num, total_pages=total_pages, filters_lines=(filters_line_1, filters_line_2, filters_line_3, filters_line_4))
            tbl_pdf = fitz.open("pdf", pdf_buffer.getvalue())

            # Nouvelle page basée sur le fond
            page_fond = doc_fond[0]
            new_page = doc_final.new_page(width=page_fond.rect.width, height=page_fond.rect.height)
            new_page.show_pdf_page(new_page.rect, doc_fond, 0)
            new_page.show_pdf_page(new_page.rect, tbl_pdf, 0)  # seulement le tableau

            tbl_pdf.close()

        doc_final.save(pdf_final_path)
        doc_final.close()
        doc_fond.close()

        # --- Télécharger le PDF ---
        with open(pdf_final_path, "rb") as f:
            pdf_bytes = f.read()

        st.success(f"PDF final généré : {os.path.basename(pdf_final_path)}")
        st.download_button(
            label="Télécharger le PDF",
            data=pdf_bytes,
            file_name=os.path.basename(pdf_final_path),
            mime="application/pdf"
        )

        # --- Nettoyage session_state ---
        st.session_state["saisie_dict"] = {}

        # --- Supprimer le CSV historique ---
        os.remove(file_path)
        st.info(f"Le fichier historique {selected_file} a été supprimé après validation")
        
def Retrait_DLC():
    st.title("Retrait DLC")
        
# Configuration des onglets
tabs = {
    "Bibliothèque CID": tab_home,
    "Etiquettes, QR Code, EAN": tab_QR_Codes,
    "Détrompeurs": tab_Detrompeurs,
    "GDS - Analyse Ecarts GEGC": Analyse_stock,
    "GDS - Inventaire" : Inventaire,
    "GDS - Retrait DLC" : Retrait_DLC,
}

def main():
    
    # Nouveau dossier de base : ton OneDrive
    git_dir = Path(r"https://github.com/IDLAurelienMartin/Data_IDL/blob/main/Images")

    # Chemins des images dans ton OneDrive
    IMAGE_PATH_1 = git_dir / "logo_IDL.jpg"
    IMAGE_PATH_2 = git_dir / "Logo_Metro.webp"
    # Vérification d’existence (pour éviter les erreurs Streamlit si un fichier manque)
    if IMAGE_PATH_1.exists():
        st.sidebar.image(str(IMAGE_PATH_1), use_container_width=True)
    else:
        st.sidebar.warning(f"Image non trouvée : {IMAGE_PATH_1}")

    st.sidebar.header("Navigation")
    selected_tab = st.sidebar.radio("", list(tabs.keys()))
    tabs[selected_tab]()

    if IMAGE_PATH_2.exists():
        st.sidebar.image(str(IMAGE_PATH_2), use_container_width=True)
    else:
        st.sidebar.warning(f"Image non trouvée : {IMAGE_PATH_2}")
   
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
