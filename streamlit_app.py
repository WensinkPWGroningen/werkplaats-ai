import base64
import re
import requests
import streamlit as st

# ============================================================
# WENSINK MERCEDES-BENZ WERKPLAATS ASSISTENT
# Herbouwde basis: RDW + Gemini + stapsgewijze vervolgdiagnose
# ============================================================

st.set_page_config(
    page_title="Wensink Mercedes Diagnose",
    page_icon="🚘",
    layout="wide",
)

# -------------------- CONFIGURATIE --------------------

RDW_VOERTUIG_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
RDW_BRANDSTOF_URL = "https://opendata.rdw.nl/resource/8ys7-d773.json"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_FOTOS = 3
MAX_FOTO_GROOTTE_MB = 8

# -------------------- HUISSTIJL --------------------

st.markdown(
    """
    <style>
      .stApp { background: #f4f6f9; }
      .main-title { color: #111827; font-size: 30px; font-weight: 800; }
      .subtitle { color: #64748b; margin-bottom: 20px; }
      .vehicle-card {
        background: white; padding: 18px 20px; border-radius: 12px;
        border: 1px solid #dce3ec; margin: 12px 0 20px 0;
      }
      div.stButton > button {
        min-height: 44px; border-radius: 8px; font-weight: 700;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- TOEGANGSCONTROLE --------------------

def controleer_toegang():
    if "ingelogd" not in st.session_state:
        st.session_state.ingelogd = False

    if st.session_state.ingelogd:
        return

    st.title("🔒 Wensink Diagnose Assistent")
    st.write("Voer de gezamenlijke toegangscode in.")

    ingevoerde_code = st.text_input("Toegangscode", type="password")
    if st.button("INLOGGEN", use_container_width=True):
        try:
            juiste_code = st.secrets["password"]["code"]
        except Exception:
            st.error(
                "De toegangscode is niet ingesteld. Voeg in Streamlit secrets "
                "de instelling [password] met code = \"...\" toe."
            )
            st.stop()

        if ingevoerde_code == juiste_code:
            st.session_state.ingelogd = True
            st.rerun()
        else:
            st.error("Onjuiste toegangscode.")

    st.stop()


controleer_toegang()

# -------------------- SESSION STATE --------------------

DEFAULTS = {
    "chat_history": [],
    "laatste_diagnose": "",
    "rdw_kenteken": "",
    "rdw_model": "",
    "rdw_jaar": "",
    "rdw_motor": "",
    "rdw_handelsbenaming": "",
    "rdw_voertuigsoort": "",
    "rdw_cilinderinhoud": "",
    "rdw_vermogen": "",
    "rdw_transmissie": "",
    "diagnose_fotos": [],
    "reset_melding": "",
    "laatste_kenteken_opgehaald": "",
}
