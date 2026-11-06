import streamlit as st
import requests
import time
import re
import base64
import traceback

st.set_page_config(
    page_title="Wensink Mercedes Diagnose",
    page_icon="🚘",
    layout="wide"
)

# ============================================================
# BEVEILIGING WENSINK DIAGNOSE ASSISTENT
# ============================================================

def controleer_toegang():
    if "ingelogd" not in st.session_state:
        st.session_state["ingelogd"] = False

    if not st.session_state["ingelogd"]:
        st.markdown("<h1>🔒 Wensink Diagnose Assistent</h1>", unsafe_allow_html=True)
        st.write("Voer de gezamenlijke toegangscode in.")

        ingevoerde_code = st.text_input(
            "Toegangscode",
            type="password",
            key="toegangscode_invoer"
        )

        if st.button("INLOGGEN", use_container_width=True):
            juiste_code = st.secrets["password"]["code"]

            if ingevoerde_code == juiste_code:
                st.session_state["ingelogd"] = True
                st.rerun()
            else:
                st.error("Onjuiste toegangscode.")
        st.stop()

controleer_toegang()

# ============================================================
# INITIALISATIE SESSION STATE VARIABELEN
# ============================================================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "laatste_diagnose" not in st.session_state:
    st.session_state["laatste_diagnose"] = ""
if "rdw_kenteken" not in st.session_state:
    st.session_state["rdw_kenteken"] = ""

# ============================================================
# RESETFUNCTIES VOOR NIEUWE DIAGNOSE
# ============================================================

def reset_nieuw_voertuig():
    sleutels = [
        "rdw_model", "rdw_jaar", "rdw_motor", "rdw_handelsbenaming", "rdw_kenteken",
        "kenteken_invoer", "kilometerstand", "foutcode", "klacht", "extra_info", 
        "laatste_diagnose", "diagnose_chat_input"
    ]
    for sleutel in sleutels:
        st.session_state[sleutel] = ""
    st.session_state["chat_history"] = []
    st.session_state["reset_melding"] = "Nieuw voertuig: alle gegevens zijn gewist."

def reset_zelfde_voertuig():
    sleutels = [
        "kilometerstand", "foutcode", "klacht", "extra_info", "laatste_diagnose", "diagnose_chat_input"
    ]
    for sleutel in sleutels:
        st.session_state[sleutel] = ""
    st.session_state["chat_history"] = []
    st.session_state["reset_melding"] = "Nieuwe diagnose gestart voor hetzelfde voertuig."

# ============================================================
# WENSINK HUISSTIJL
# ============================================================

st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    .main-title { color: #111827; font-size: 30px; font-weight: 800; margin-top: 10px; }
    .subtitle { color: #64748b; font-size: 15px; margin-bottom: 25px; }
    .stButton button { background-color: #111827; color: white; border-radius: 8px; font-weight: bold; min-height: 45px; }
    .stButton button:hover { background-color: #374151; color: white; border-color: #374151; }
    .vehicle-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚘 Wensink Mercedes-Benz Werkplaats Assistent</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Voer de voertuiggegevens en klachten in voor een diepgaande technische diagnose.</p>", unsafe_allow_html=True)

# Resetknoppen bovenin tonen
col_reset1, col_reset2 = st.columns(2)
with col_reset1:
    if st.button("♻️ NIEUW VOERTUIG STARTEN", use_container_width=True):
        reset_nieuw_voertuig()
        st.rerun()
with col_reset2:
    if st.button("🔄 NIEUWE DIAGNOSE (ZELFDE AUTO)", use_container_width=True):
        reset_zelfde_voertuig()
        st.rerun()

if "reset_melding" in st.session_state and st.session_state["reset_melding"]:
    st.success(st.session_state["reset_melding"])
    st.session_state["reset_melding"] = ""

st.divider()

# ============================================================
# RDW API CONFIGURATIE & OPHALEN
# ============================================================

RDW_VOERTUIG_URL = "https://rdw.nl"
RDW_BRANDSTOF_URL = "https://rdw.nl"

def haal_rdw_data(kenteken):
    kenteken = re.sub(r"[^A-Z0-9]", "", kenteken.upper())
    if not kenteken:
        return None

    headers = {"Accept": "application/json", "User-Agent": "Wensink-Diagnose-Assistent/1.0"}

    try:
        response = requests.get(RDW_VOERTUIG_URL, params={"kenteken": kenteken, "$limit": 1}, headers=headers, timeout=15)
        response.raise_for_status()
        voertuigen = response.json()

        if not voertuigen:
            return None
        voertuig = voertuigen[0]

        merk = voertuig.get("merk", "").strip().upper()
        if merk not in ("MERCEDES-BENZ", "MERCEDES BENZ"):
            return "GEEN_MERCEDES"

        brandstof_response = requests.get(RDW_BRANDSTOF_URL, params={"kenteken": kenteken, "$limit": 10}, headers=headers, timeout=15)
        brandstof_response.raise_for_status()
        brandstof_data = brandstof_response.json()

        brandstoffen = [item.get("brandstof_omschrijving", "").upper() for item in brandstof_data]
        heeft_elektrisch = any("ELEKTR" in b for b in brandstoffen)
        heeft_benzine = any("BENZINE" in b for b in brandstoffen)
        heeft_diesel = any("DIESEL" in b for b in brandstoffen)

        if heeft_elektrisch and (heeft_benzine or heeft_diesel):
            brandstof = "Hybride"
        elif heeft_elektrisch:
            brandstof = "Elektrisch"
        elif heeft_benzine:
            brandstof = "Benzine"
        elif heeft_diesel:
            brandstof = "Diesel"
        elif brandstoffen:
            brandstof = brandstoffen[0].title()
        else:
            brandstof = "Onbekend"

        ruwe_model = voertuig.get("handelsbenaming", "Onbekend").strip().upper()
        model_regels = [
            ("SPRINTER", "Sprinter"), ("VITO", "Vito"), ("GLA", "GLA"), ("GLB", "GLB"),
            ("GLC", "GLC"), ("GLE", "GLE"), ("GLS", "GLS"), ("CLA", "CLA"), ("CLS", "CLS"),
            ("EQS", "EQS"), ("EQE", "EQE"), ("EQB", "EQB"), ("EQA", "EQA"), ("SLK", "SLK"),
            ("S-KLASSE", "S-Klasse"), ("E-KLASSE", "E-Klasse"), ("C-KLASSE", "C-Klasse"),
            ("A-KLASSE", "A-Klasse"), ("B-KLASSE", "B-Klasse")
        ]

        schoon_model = ruwe_model.title()
        for zoekterm, modelnaam in model_regels:
            if zoekterm in ruwe_model:
                schoon_model = modelnaam
                break

        datum = str(voertuig.get("datum_eerste_toelating", ""))
        bouwjaar = datum[:4] if len(datum) >= 4 else "Onbekend"

        return {
            "kenteken": kenteken,
            "merk": merk,
            "model": schoon_model,
            "handelsbenaming": ruwe_model,
            "jaar": bouwjaar,
            "motor": brandstof
        }
    except Exception:
        return None

# INVOERVELDEN DEEL 1
kenteken_invoer = st.text_input("Kenteken invoeren", key="kenteken_invoer")

if kenteken_invoer:
    with st.spinner("Voertuiggegevens ophalen bij de RDW..."):
        voertuig_data = haal_rdw_data(kenteken_invoer)
        if voertuig_data and voertuig_data != "GEEN_MERCEDES":
            st.session_state["rdw_kenteken"] = voertuig_data["kenteken"]
            st.session_state["rdw_model"] = voertuig_data["model"]
            st.session_state["rdw_jaar"] = voertuig_data["jaar"]
            st.session_state["rdw_motor"] = voertuig_data["motor"]
            st.session_state["rdw_handelsbenaming"] = voertuig_data["handelsbenaming"]
        elif voertuig_data == "GEEN_MERCEDES":
            st.error("Dit voertuig is geen Mercedes-Benz. De assistent ondersteunt alleen Mercedes-Benz.")
            st.session_state["rdw_kenteken"] = ""

if st.session_state.get("rdw_kenteken"):
    st.markdown(f"""
    <div class='vehicle-card'>
        <strong>🚗 Geregistreerd Voertuig:</strong> Mercedes-Benz {st.session_state['rdw_model']}<br>
        <small>Handelsbenaming: {st.session_state['rdw_handelsbenaming']} | Bouwjaar: {st.session_state['rdw_jaar']} | Aandrijving: {st.session_state['rdw_motor']}</small>
    </div>
    """, unsafe_allow_html=True)

# INVOERVELDEN DEEL 2: DIAGNOSEGEGEVENS MONTEUR
st.write("### 🛠️ Werkplaats Invoergegevens")
col1, col2 = st.columns(2)

with col1:
    kilometerstand = st.text_input("Kilometerstand (km)", key="kilometerstand")
    foutcode = st.text_input("Actieve storingscodes / DTC's (bijv. P0299, P0101)", key="foutcode")

with col2:
    klacht = st.text_area("Klachtomschrijving van de klant", key="klacht")
    extra_info = st.text_area("Extra parameters / Meetwaarden / Reeds uitgevoerde tests", key="extra_info")
# ============================================================
# DEEL 3: INITIALE DIAGNOSE GENEREREN (HOOFDKNOP)
# ============================================================

if st.session_state.get("rdw_kenteken"):
    if st.button("🔥 START MASTER TECHNICIAN ANALYSE", use_container_width=True):
        if not st.session_state.get("klacht") and not st.session_state.get("foutcode"):
            st.warning("Voer minimaal een klachtomschrijving of een storingscode in om de analyse te starten.")
        else:
            with st.spinner("De Wensink Diagnose Assistent raadpleegt fabrieksdocumentatie en analyseert meetwaarden..."):
                try:
                    api_key = st.secrets.get("GOOGLE_API_KEY", "")
                    if not api_key:
                        st.error("GOOGLE_API_KEY ontbreekt in Streamlit secrets.")
                        st.stop()

                    systeem_prompt = """Je bent de Mercedes-Benz Master Technician van de Wensink Diagnose Assistent.
Je voert een diepgaande technische diagnose uit voor Mercedes-Benz voertuigen. 
Geef concreet, professioneel en uitvoerbaar diagnoseadvies, verwijs naar relevante controles in XENTRY en maak helder onderscheid tussen vermoedens van defecten en bewezen defecten."""

                    gebruikers_prompt = f"""
Nieuwe diagnose-aanvraag voor Mercedes-Benz:
- Model: {st.session_state.get('rdw_model')}
- Handelsbenaming: {st.session_state.get('rdw_handelsbenaming')}
- Bouwjaar: {st.session_state.get('rdw_jaar')}
- Brandstof/Motorisering: {st.session_state.get('rdw_motor')}

Werkplaats parameters:
- Kilometerstand: {st.session_state.get('kilometerstand', 'Niet opgegeven')}
- Storingscode(s): {st.session_state.get('foutcode', 'Geen')}
- Klachtomschrijving: {st.session_state.get('klacht', 'Geen')}
- Extra informatie: {st.session_state.get('extra_info', 'Geen')}
"""

                    url = "https://googleapis.com"
                    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
                    payload = {
                        "contents": [{"role": "user", "parts": [{"text": gebruikers_prompt}]}],
                        "systemInstruction": {"parts": [{"text": systeem_prompt.strip()}]},
                        "generationConfig": {"temperature": 0.2}
                    }

                    response = requests.post(url, json=payload, headers=headers, timeout=90)
                    response.raise_for_status()
                    
                    eerste_antwoord = response.json()["candidates"][0]["content"]["parts"][0]["text"]

                    st.session_state["laatste_diagnose"] = eerste_antwoord
                    st.session_state["chat_history"] = [
                        {"role": "user", "parts": [{"text": gebruikers_prompt}]},
                        {"role": "model", "parts": [{"text": eerste_antwoord}]}
                    ]
                    st.rerun()

                except Exception as e:
                    st.error(f"Initieele diagnose genereren mislukt: {str(e)}")

# TOON DE GENERATED DIAGNOSE
if st.session_state.get("laatste_diagnose"):
    st.markdown("### 📋 Officiële Wensink Diagnose Rapportage")
    st.info(st.session_state["laatste_diagnose"])

# ============================================================
# DEEL 4: GEMINI VERVOLGCHAT LOGICA & UI
# ============================================================

def genereer_vervolgantwoord(chat_history, vraag):
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    
    systeem_prompt = """Je bent de Mercedes-Benz Master Technician van de Wensink Diagnose Assistent.
Houd rekening met de eerdere voertuiggegevens, klachten en storingen. Concentreer je op de nieuwe vraag en geef gerichte technische stappen."""

    inhoud = []
    for bericht in chat_history:
        rol = bericht.get("role")
        onderdelen = bericht.get("parts", [])
        geldige_onderdelen = []
        
        if isinstance(onderdelen, list):
            for o in onderdelen:
                if isinstance(o, dict) and o.get("text"):
                    geldige_onderdelen.append({"text": o["text"]})
        elif isinstance(onderdelen, dict) and onderdelen.get("text"):
            geldige_onderdelen.append({"text": onderdelen["text"]})
            
        if geldige_onderdelen:
            inhoud.append({"role": rol, "parts": geldige_onderdelen})

    inhoud.append({"role": "user", "parts": [{"text": vraag.strip()}]})

    url = "https://googleapis.com"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {
        "contents": inhoud,
        "systemInstruction": {"parts": [{"text": systeem_prompt.strip()}]},
        "generationConfig": {"temperature": 0.2}
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


# CHAT INTERFACE ONDERAAN HET SCHERM
if st.session_state.get("laatste_diagnose"):
    st.divider()
    st.subheader("💬 Verdieping en vervolgvragen")
    st.write("Stel aanvullende vragen over de meetwaarden of teststappen. De assistent behoudt de context.")

    # Laat eerdere turn-berichten live in de UI zien
    for bericht in st.session_state["chat_history"][2:]:
        rol_naam = "user" if bericht["role"] == "user" else "assistant"
        with st.chat_message(rol_naam):
            onderdelen = bericht.get("parts", [])
            if isinstance(onderdelen, list) and len(onderdelen) > 0:
                st.markdown(onderdelen[0].get("text", ""))
            elif isinstance(onderdelen, dict):
                st.markdown(onderdelen.get("text", ""))

    nieuwe_vraag = st.chat_input("Stel een vervolgvraag aan de Master Technician...", key="diagnose_chat_input")

    if nieuwe_vraag:
        with st.chat_message("user"):
            st.markdown(nieuwe_vraag)

        with st.chat_message("assistant"):
            with st.spinner("Analyseert aanvullende testgegevens..."):
                try:
                    antwoord_tekst = genereer_vervolgantwoord(st.session_state["chat_history"], nieuwe_vraag)
                    
                    st.session_state["chat_history"].extend([
                        {"role": "user", "parts": [{"text": nieuwe_vraag}]},
                        {"role": "model", "parts": [{"text": antwoord_tekst}]}
                    ])
                    st.markdown(antwoord_tekst)
                    st.rerun()
                except Exception as e:
                    st.error("Vervolgdiagnose mislukt: " + str(e))
