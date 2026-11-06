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
        st.markdown(
            "<h1>🔒 Wensink Diagnose Assistent</h1>",
            unsafe_allow_html=True
        )

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
        "kilometerstand", "foutcode", "klacht", "extra_info", "laatste_diagnose", "diagnose_chat_input"
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
    .main-title { color: #111827; font-size: 30px; font-weight: 800; }
    .subtitle { color: #64748b; font-size: 15px; margin-bottom: 25px; }
    .stButton button { background-color: #111827; color: white; border-radius: 8px; font-weight: bold; min-height: 45px; }
    .stButton button:hover { background-color: #374151; color: white; border-color: #374151; }
    .vehicle-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# RDW API INSTELLINGEN
# ============================================================

RDW_VOERTUIG_URL = "https://rdw.nl"
RDW_BRANDSTOF_URL = "https://rdw.nl"

# ============================================================
# RDW VOERTUIGGEGEVENS OPHALEN
# ============================================================

def haal_rdw_data(kenteken):
    kenteken = re.sub(r"[^A-Z0-9]", "", kenteken.upper())
    if not kenteken:
        return None

    headers = {
        "Accept": "application/json",
        "User-Agent": "Wensink-Diagnose-Assistent/1.0"
    }

    try:
        # VOERTUIGGEGEVENS
        response = requests.get(RDW_VOERTUIG_URL, params={"kenteken": kenteken, "$limit": 1}, headers=headers, timeout=15)
        response.raise_for_status()
        voertuigen = response.json()

        if not voertuigen:
            return None
        voertuig = voertuigen[0]

        # MERK CONTROLEREN
        merk = voertuig.get("merk", "").strip().upper()
        if merk not in ("MERCEDES-BENZ", "MERCEDES BENZ"):
            return "GEEN_MERCEDES"

        # BRANSTOFGEGEVENS
        brandstof_response = requests.get(RDW_BRANDSTOF_URL, params={"kenteken": kenteken, "$limit": 10}, headers=headers, timeout=15)
        brandstof_response.raise_for_status()
        brandstof_data = brandstof_response.json()

        brandstoffen = [item.get("brandstof_omschrijving", "").upper() for item in brandstof_data]

        # BRANDSTOF HERKENNEN
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

        # MERCEDES MODEL HERKENNING
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

        # BOUWJAAR
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

    except requests.exceptions.Timeout:
        st.error("De RDW reageert niet op tijd.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error("RDW HTTP-fout: " + " - " + str(e))
        return None
    except requests.exceptions.RequestException as e:
        st.error("RDW verbindingsfout: " + str(e))
        return None
    except Exception as e:
        st.error(f"Onverwachte RDW-fout: {str(e)}")
        return None

# ============================================================
# DEEL 4A: GEMINI VERVOLGCHAT LOGICA
# ============================================================

def genereer_vervolgantwoord(chat_history, vraag):
    if not vraag or not vraag.strip():
        raise ValueError("Je hebt geen vervolgvraag ingevoerd.")
    if not isinstance(chat_history, list) or not chat_history:
        raise ValueError("Er is geen diagnosegeschiedenis beschikbaar. Genereer eerst een diagnose.")

    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY ontbreekt in Streamlit secrets.")

    systeem_prompt = """
Je bent de Mercedes-Benz Master Technician van de Wensink Diagnose Assistent.
Je voert een doorlopende technische diagnose uit voor Mercedes-Benz voertuigen.

BELANGRIJK:
1. Gebruik alle eerdere voertuiggegevens.
2. Houd rekening met de oorspronkelijke klacht.
3. Onthoud alle eerdere storingscodes.
4. Gebruik de oorspronkelijke diagnose als uitgangspunt.
5. Verwerk nieuwe meetwaarden en testresultaten.
6. Pas conclusies aan wanneer nieuwe informatie daar aanleiding toe geeft.
7. Stel gerichte vervolgvragen wanneer informatie ontbreekt.
8. Geef praktische vervolgstappen voor de monteur.

ANTWOORDSTIJL:
- Schrijf professioneel technisch Nederlands.
- Geef concrete en uitvoerbare diagnoseadviezen.
- Concentreer je op de nieuwe vraag en de volgende diagnosestap.
"""

    inhoud = []
    for bericht in chat_history:
        if isinstance(bericht, dict):
            rol = bericht.get("role")
            onderdelen = bericht.get("parts", [])
            geldige_onderdelen = []
            
            # Controleer of parts een lijst is (zoals het hoort)
            if isinstance(onderdelen, list):
                for onderdeel in onderdelen:
                    if isinstance(onderdeel, dict) and onderdeel.get("text"):
                        geldige_onderdelen.append({"text": onderdeel["text"]})
            # Als parts per ongeluk een dict is, vang het hier veilig op
            elif isinstance(onderdelen, dict) and onderdelen.get("text"):
                geldige_onderdelen.append({"text": onderdelen["text"]})
            
            if geldige_onderdelen:
                inhoud.append({"role": rol, "parts": geldige_onderdelen})

    inhoud.append({"role": "user", "parts": [{"text": vraag.strip()}]})

    url = "https://googleapis.com"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": inhoud,
        "systemInstruction": {"parts": [{"text": systeem_prompt.strip()}]},
        "generationConfig": {"temperature": 0.2}
    }

    for poging in range(1, 4):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code in (429, 500, 502, 503, 504) and poging < 3:
                time.sleep(2 * poging)
                continue
            
            response.raise_for_status()
            resultaat = response.json()
            
            kandidaten = resultaat.get("candidates", [])
            if kandidaten:
                kandidaat = kandidaten[0]
                inhoud_antwoord = kandidaat.get("content", {})
                onderdelen_antwoord = inhoud_antwoord.get("parts", [])
                antwoord = "\n".join(o.get("text", "") for o in onderdelen_antwoord if o.get("text")).strip()
                if antwoord:
                    return antwoord
            raise ValueError("Gemini heeft geen bruikbaar tekstantwoord teruggegeven.")
            
        except requests.exceptions.RequestException as e:
            if poging == 3:
                raise RuntimeError(f"Verbindingsfout bij Gemini: {str(e)}")
            time.sleep(2 * poging)

    raise RuntimeError("De vervolgdiagnose kon niet worden gegenereerd na 3 pogingen.")

# ============================================================
# DEEL 4B: CHATINTERFACE UI
# ============================================================

st.markdown("<h1 class='main-title'>🚘 Wensink Mercedes-Benz Werkplaats Assistent</h1>", unsafe_allow_html=True)

# Test-omgeving simulatie met de VOLLEDIG CORRECTE lijst-structuur voor de parts
if not st.session_state["laatste_diagnose"] or not st.session_state["chat_history"]:
    st.session_state["laatste_diagnose"] = "Basisdiagnose gegenereerd."
    st.session_state["rdw_kenteken"] = "KXP17K"
    st.session_state["chat_history"] = [
        {"role": "user", "parts": [{"text": "Diagnose opstarten"}]},
        {"role": "model", "parts": [{"text": "Systeem startklaar. Welke klacht wilt u onderzoeken?"}]}
    ]

if st.session_state.get("laatste_diagnose"):
    st.divider()
    st.subheader("Verdieping en vervolgvragen")
    st.write("Stel aanvullende vragen over deze diagnose. Gemini onthoudt de eerdere voertuiggegevens, klacht en diagnose.")

    # Toon geschiedenis vanaf de vervolgturns (index 2+)
    for bericht in st.session_state["chat_history"][2:]:
        rol_naam = "user" if bericht["role"] == "user" else "assistant"
        with st.chat_message(rol_naam):
            # GEFIXT: Haal de tekst veilig op uit de lijst-structuur [0]["text"]
            onderdelen = bericht.get("parts", [])
            if isinstance(onderdelen, list) and len(onderdelen) > 0:
                st.markdown(onderdelen[0].get("text", ""))
            elif isinstance(onderdelen, dict):
                st.markdown(onderdelen.get("text", ""))

    nieuwe_vraag = st.chat_input("Stel een vervolgvraag over deze Mercedes...", key="diagnose_chat_input")

    if nieuwe_vraag:
        with st.chat_message("user"):
            st.markdown(nieuwe_vraag)

        with st.chat_message("assistant"):
            with st.spinner("Gemini analyseert de vervolggegevens..."):
                try:
                    antwoord_tekst = genereer_vervolgantwoord(st.session_state["chat_history"], nieuwe_vraag)
                    
                    # Sla beide nieuwe berichten correct op als lijst in parts
                    st.session_state["chat_history"].extend([
                        {"role": "user", "parts": [{"text": nieuwe_vraag}]},
                        {"role": "model", "parts": [{"text": antwoord_tekst}]}
                    ])
                    st.markdown(antwoord_tekst)
                    st.rerun()
                except Exception as e:
                    st.error("Vervolgdiagnose mislukt: " + str(e))
                    st.code(traceback.format_exc(), language="python")
