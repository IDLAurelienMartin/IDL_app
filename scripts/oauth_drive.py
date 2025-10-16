import os
import json
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
<<<<<<< HEAD
from pathlib import Path
from googleapiclient.http import MediaFileUpload

# --------------------------
# Scopes Drive complets (lecture/écriture)
# --------------------------
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    st.set_page_config(layout="wide")

    service_json = os.environ.get("GOOGLE_SERVICE_JSON")
    if not service_json:
=======

def get_drive_service():
    st.set_page_config(layout="wide")

    try:
        service_json = os.environ["GOOGLE_SERVICE_JSON"]
    except KeyError:
>>>>>>> c5fccbe (16/10  09h40)
        st.error("La variable d'environnement GOOGLE_SERVICE_JSON n'est pas définie.")
        return None

    try:
        credentials_info = json.loads(service_json)
    except Exception as e:
        st.error(f"Impossible de parser GOOGLE_SERVICE_JSON : {e}")
        return None

<<<<<<< HEAD
    creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

if __name__ == "__main__":
    drive_service = get_drive_service()
    if drive_service:
        results = drive_service.files().list(pageSize=10, fields="files(id, name)").execute()
        files = results.get('files', [])
        if not files:
            print("Aucun fichier trouvé.")
        else:
            print("Connexion Service Account réussie !")
            for f in files:
                print(f"{f['name']} ({f['id']})")
=======
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

if __name__ == "__main__":
    service = get_drive_service()
    # Test : lister les 10 premiers fichiers de ton My Drive
    if service:
            # Test : lister les 10 premiers fichiers de ton My Drive
            results = service.files().list(pageSize=10, fields="files(id, name)").execute()
            for f in results.get('files', []):
                print(f["name"], f["id"])
>>>>>>> c5fccbe (16/10  09h40)
