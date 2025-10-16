import os
import json
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from pathlib import Path
from googleapiclient.http import MediaFileUpload

# --------------------------
# Scopes Drive complets (lecture/écriture)
# --------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    st.set_page_config(layout="wide")

    service_json = os.environ.get("GOOGLE_SERVICE_JSON")
    
    if service_json:
        # Variable d'environnement présente (ex : Render)
        try:
            credentials_info = json.loads(service_json)
        except Exception as e:
            st.error(f"Impossible de parser GOOGLE_SERVICE_JSON : {e}")
            return None
    else:
        # Sinon on cherche un fichier local
        local_path = Path("IDL_DB/service_account.json")  # <-- adapte le chemin si nécessaire
        if not local_path.exists():
            st.error(
                "La variable d'environnement GOOGLE_SERVICE_JSON n'est pas définie "
                "et le fichier local n'existe pas."
            )
            return None
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                credentials_info = json.load(f)
        except Exception as e:
            st.error(f"Impossible de lire le fichier local service_account.json : {e}")
            return None

    try:
        creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=creds)
        return drive_service
    except Exception as e:
        st.error(f"Erreur lors de la création du service Google Drive : {e}")
        return None

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

