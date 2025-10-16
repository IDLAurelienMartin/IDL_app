import os
import json
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def get_drive_service():
    st.set_page_config(layout="wide")

    try:
        service_json = os.environ["GOOGLE_SERVICE_JSON"]
    except KeyError:
        st.error("La variable d'environnement GOOGLE_SERVICE_JSON n'est pas définie.")
        return None

    try:
        credentials_info = json.loads(service_json)
    except Exception as e:
        st.error(f"Impossible de parser GOOGLE_SERVICE_JSON : {e}")
        return None

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
