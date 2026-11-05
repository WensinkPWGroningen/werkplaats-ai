
import streamlit as st
import requests
import time
import re

# ============================================================
# WENSINK MERCEDES-BENZ DIAGNOSE ASSISTENT
# DEEL 1: INSTELLINGEN EN RDW-KOPPELING
# ============================================================

st.set_page_config(
    page_title="Wensink Mercedes Diagnose",
    page_icon="🚘",
    layout="wide"
)

# ============================================================
# WENSINK HUISSTIJL
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #f4f6f9;
    }

    .main-title {
        color: #111827;
        font-size: 30px;
        font-weight: 800;
    }

    .subtitle {
        color: #64748b;
        font-size: 15px;
        margin-bottom: 25px;
    }

    .stButton button {
        background-color: #111827;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        min-height: 45px;
    }

    .stButton button:hover {
        background-color: #374151;
        color: white;
        border-color: #374151;
    }

    .vehicle-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# RDW API INSTELLINGEN
# ============================================================

RDW_VOERTUIG_URL = (
    "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
)

RDW_BRANDSTOF_URL = (
    "https://opendata.rdw.nl/resource/8ys7-d773.json"
)


# ============================================================
# RDW VOERTUIGGEGEVENS OPHALEN
# ============================================================

def haal_rdw_data(kenteken):

    kenteken = re.sub(
        r"[^A-Z0-9]",
        "",
        kenteken.upper()
    )

    if not kenteken:
        return None

    headers = {
        "Accept": "application/json",
        "User-Agent": "Wensink-Diagnose-Assistent/1.0"
    }

    try:

        # VOERTUIGGEGEVENS

        response = requests.get(
            RDW_VOERTUIG_URL,
            params={
                "kenteken": kenteken,
                "$limit": 1
            },
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        voertuigen = response.json()

        if not voertuigen:
            return None

        voertuig = voertuigen[0]

        # MERK CONTROLEREN

        merk = voertuig.get(
            "merk", ""
        ).strip().upper()

        if merk not in (
            "MERCEDES-BENZ",
            "MERCEDES BENZ"
        ):
            return "GEEN_MERCEDES"

        # BRANSTOFGEGEVENS

        brandstof_response = requests.get(
            RDW_BRANDSTOF_URL,
            params={
                "kenteken": kenteken,
                "$limit": 10
            },
            headers=headers,
            timeout=15
        )

        brandstof_response.raise_for_status()

        brandstof_data = brandstof_response.json()

        brandstoffen = [
            item.get(
                "brandstof_omschrijving", ""
            ).upper()
            for item in brandstof_data
        ]

        # BRANDSTOF HERKENNEN

        heeft_elektrisch = any(
            "ELEKTR" in b for b in brandstoffen
        )

        heeft_benzine = any(
            "BENZINE" in b for b in brandstoffen
        )

        heeft_diesel = any(
            "DIESEL" in b for b in brandstoffen
        )

        if heeft_elektrisch and (
            heeft_benzine or heeft_diesel
        ):
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

        ruwe_model = voertuig.get(
            "handelsbenaming", "Onbekend"
        ).strip().upper()

        model_regels = [
            ("SPRINTER", "Sprinter"),
            ("VITO", "Vito"),
            ("GLA", "GLA"),
            ("GLB", "GLB"),
            ("GLC", "GLC"),
            ("GLE", "GLE"),
            ("GLS", "GLS"),
            ("CLA", "CLA"),
            ("CLS", "CLS"),
            ("EQS", "EQS"),
            ("EQE", "EQE"),
            ("EQB", "EQB"),
            ("EQA", "EQA"),
            ("SLK", "SLK"),
            ("S-KLASSE", "S-Klasse"),
            ("E-KLASSE", "E-Klasse"),
            ("C-KLASSE", "C-Klasse"),
            ("A-KLASSE", "A-Klasse"),
            ("B-KLASSE", "B-Klasse")
        ]

        schoon_model = ruwe_model.title()

        for zoekterm, modelnaam in model_regels:

            if zoekterm in ruwe_model:
                schoon_model = modelnaam
                break

        # BOUWJAAR

        datum = str(
            voertuig.get(
                "datum_eerste_toelating", ""
            )
        )

        bouwjaar = (
            datum[:4]
            if len(datum) >= 4
            else "Onbekend"
        )

        # RESULTAAT TERUGGEVEN

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

        st.error("RDW HTTP-fout: " + str(e))
        return None

    except requests.exceptions.RequestException as e:

        st.error("RDW verbindingsfout: " + str(e))
        return None

    except Exception as e:

        st.error("Onverwachte RDW-fout: " + str(e))
        return None


# ============================================================
# EINDE DEEL 1
# PLAK DEEL 2 HIERONDER
# ============================================================

# ============================================================
# DEEL 2: GOOGLE GEMINI AI DIAGNOSE-ENGINE
# ============================================================

def genereer_diagnose(
    model,
    bouwjaar,
    handelsbenaming,
    motorisering,
    kilometerstand,
    foutcode,
    klacht
):

    # GOOGLE API-SLEUTEL OPHALEN

    api_key = st.secrets.get(
        "GOOGLE_API_KEY", ""
    )

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY ontbreekt in Streamlit secrets."
        )

    # ========================================================
    # SYSTEEMPROMPT
    # ========================================================

    systeem_prompt = """
Je bent een zeer ervaren Mercedes-Benz Master Technician
met specialistische kennis van Mercedes-Benz voertuigen.

Je hebt kennis van:

- Mercedes-Benz benzinemotoren
- Mercedes-Benz dieselmotoren
- Plug-in hybride systemen
- Volledig elektrische EQ-modellen
- Automatische transmissies
- 7G-Tronic en 9G-Tronic
- OM-motoren
- M-motoren
- Mercedes-Benz motormanagement
- AdBlue en SCR-systemen
- DPF en EGR-systemen
- Turbo- en injectiesystemen
- 12V en 48V elektrische systemen
- CAN-bus en LIN-bus
- SAM-modules
- ESP en ABS
- Airconditioning
- XENTRY diagnose

Je bent gespecialiseerd in technische diagnose
voor een professionele Mercedes-Benz werkplaats.

BELANGRIJKE DIAGNOSEREGELS:

1. Geef geen onderdelen vrij voor vervanging zonder
   eerst een diagnose-onderbouwing te geven.

2. Maak onderscheid tussen:
   - Mogelijke oorzaak
   - Waarschijnlijke oorzaak
   - Bevestigd defect

3. Geef altijd een logische diagnosevolgorde.

4. Vermeld welke meetwaarden relevant zijn.

5. Verzin geen fabriekswaarden, toleranties,
   onderdeelnummers of technische specificaties.

6. Wanneer exacte technische gegevens ontbreken,
   verwijs dan naar de juiste Mercedes-Benz
   werkplaatsdocumentatie of XENTRY.

7. Houd rekening met het bouwjaar en de motorisering.

8. Geef aan wanneer een VIN of motorcode noodzakelijk is.

9. Geef praktische teststappen die een monteur
   daadwerkelijk kan uitvoeren.

10. Geef veiligheidswaarschuwingen wanneer werkzaamheden
    aan hoogvoltage- of brandstofsystemen aan de orde zijn.

11. Maak duidelijk wanneer een reparatie eerst door
    aanvullende metingen moet worden bevestigd.

12. Gebruik professioneel en technisch Nederlands.

# VASTE STRUCTUUR VAN HET ANTWOORD

## 1. Voertuigidentificatie
Vat de voertuiggegevens samen.

## 2. Klachtanalyse
Analyseer de klacht en mogelijke oorzaken.

## 3. Top 3 meest waarschijnlijke oorzaken
Geef drie mogelijke oorzaken met technische onderbouwing.

## 4. Diagnose stappenplan
Geef een logisch stappenplan voor de monteur.

Beschrijf per stap:
- Wat controleren?
- Hoe controleren?
- Welke meetwaarden zijn relevant?
- Wat betekent de uitkomst?

## 5. Storingscode-analyse
Analyseer de opgegeven DTC-codes.
Leg uit wat ze betekenen en welke systemen erbij betrokken zijn.

## 6. Bekende aandachtspunten
Geef relevante aandachtspunten voor dit Mercedes-model
en deze motorisering.
Maak duidelijk wanneer informatie niet bevestigd is.

## 7. Mogelijk defecte onderdelen
Geef een lijst met mogelijke onderdelen.
Vermeld waarom deze verdacht zijn en hoe ze getest worden.

## 8. Eindadvies
Geef aan welke controle de monteur als eerste moet uitvoeren.

## 9. Diagnoseconclusie
Geef een korte samenvatting met:
- Meest waarschijnlijke oorzaak
- Benodigde vervolgtest
- Mate van zekerheid

Let op:
Een diagnose is pas definitief wanneer de relevante
testresultaten het defect bevestigen.
"""

    # ========================================================
    # GEBRUIKERSPROMPT
    # ========================================================

    gebruikers_prompt = f"""
# MERCEDES-BENZ VOERTUIGGEGEVENS

Merk: Mercedes-Benz

Model: {model}

Bouwjaar: {bouwjaar}

Handelsbenaming: {handelsbenaming}

Motor / Brandstof: {motorisering}

Kilometerstand: {kilometerstand}

# STORINGSGEGEVENS

Storingscode(s): {foutcode if foutcode else "Niet opgegeven"}

# KLACHTOMSCHRIJVING

{klacht}

# OPDRACHT

Analyseer bovenstaande gegevens als een ervaren
Mercedes-Benz Master Technician.

Geef een technisch onderbouwd diagnoseadvies
met een praktisch stappenplan voor de werkplaats.

Houd rekening met het specifieke voertuig,
de motorisering, het bouwjaar en de klacht.

Verzin geen meetwaarden of technische specificaties.
Geef duidelijk aan welke gegevens nog ontbreken.
"""

    # ========================================================
    # GEMINI API INSTELLINGEN
    # ========================================================

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.8-flash:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    payload = {

        "contents": [
            {
                "parts": [
                    {
                        "text": gebruikers_prompt
                    }
                ]
            }
        ],

        "systemInstruction": {
            "parts": [
                {
                    "text": systeem_prompt
                }
            ]
        },

        "generationConfig": {
            "temperature": 0.2
        }
    }

    # ========================================================
    # API AANROEP MET HERHALING BIJ TIJDELIJKE FOUTEN
    # ========================================================

    for poging in range(1, 4):

        try:

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=90
            )

            # TIJDELIJKE GOOGLE API-PROBLEMEN

            if response.status_code in (
                429, 500, 502, 503, 504
            ):

                if poging < 3:
                    time.sleep(2 * poging)
                    continue

            # ANDERE HTTP-FOUTEN

            response.raise_for_status()

            # JSON RESULTAAT VERWERKEN

            resultaat = response.json()

            kandidaten = resultaat.get(
                "candidates", []
            )

            if not kandidaten:

                raise ValueError(
                    "Gemini heeft geen diagnoseantwoord teruggegeven."
                )

            inhoud = kandidaten[0].get(
                "content", {}
            )

            onderdelen = inhoud.get(
                "parts", []
            )

            antwoord = "\n".join(
                onderdeel.get("text", "")
                for onderdeel in onderdelen
                if onderdeel.get("text")
            )

            if not antwoord:

                raise ValueError(
                    "Het AI-antwoord bevat geen tekst."
                )

            return antwoord

        except requests.exceptions.HTTPError:

            if poging == 3:
                raise

            time.sleep(2 * poging)

        except requests.exceptions.RequestException:

            if poging == 3:
                raise

            time.sleep(2 * poging)

    raise RuntimeError(
        "Diagnose kon niet worden gegenereerd."
    )


# ============================================================
# EINDE DEEL 2
# PLAK DEEL 3 HIERONDER
# ============================================================

# ============================================================
# DEEL 3: WENSINK STREAMLIT INTERFACE
# ============================================================

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    'Wensink Diagnose Assistent'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Mercedes-Benz voertuigidentificatie en technische diagnose'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ============================================================
# SECTIE 1: KENTEKEN OPZOEKEN
# ============================================================

st.subheader("1. Voertuig identificeren")

col1, col2 = st.columns([3, 1])

with col1:

    kenteken_invoer = st.text_input(
        "Kenteken",
        placeholder="Bijvoorbeeld GG-123-X"
    )

with col2:

    st.write("")
    st.write("")

    ophalen = st.button(
        "RDW OPHALEN",
        use_container_width=True
    )


# ============================================================
# RDW OPHALEN EN SESSION STATE BIJWERKEN
# ============================================================

if ophalen:

    if not kenteken_invoer.strip():

        st.warning(
            "Vul eerst een kenteken in."
        )

    else:

        with st.spinner(
            "Voertuiggegevens ophalen bij RDW..."
        ):

            data = haal_rdw_data(
                kenteken_invoer
            )

        if data == "GEEN_MERCEDES":

            st.error(
                "Dit voertuig is geen Mercedes-Benz. "
                "Deze applicatie is uitsluitend bedoeld "
                "voor Mercedes-Benz."
            )

        elif data:

            st.session_state["rdw_model"] = data["model"]

            st.session_state["rdw_jaar"] = data["jaar"]

            st.session_state["rdw_motor"] = data["motor"]

            st.session_state["rdw_handelsbenaming"] = (
                data["handelsbenaming"]
            )

            st.session_state["rdw_kenteken"] = (
                data["kenteken"]
            )

            st.success(
                "Mercedes-Benz voertuig succesvol opgehaald!"
            )

            st.rerun()

        else:

            st.warning(
                "Geen voertuiggegevens gevonden. "
                "Controleer het kenteken of vul de gegevens handmatig in."
            )


# ============================================================
# SECTIE 2: VOERTUIGGEGEVENS TONEN
# ============================================================

if st.session_state.get("rdw_model"):

    st.markdown(
        '<div class="vehicle-card">',
        unsafe_allow_html=True
    )

    st.success(
        "Voertuiggegevens beschikbaar"
    )

    v1, v2, v3 = st.columns(3)

    with v1:

        st.metric(
            "Model",
            st.session_state.get(
                "rdw_model", "-"
            )
        )

    with v2:

        st.metric(
            "Bouwjaar",
            st.session_state.get(
                "rdw_jaar", "-"
            )
        )

    with v3:

        st.metric(
            "Brandstof",
            st.session_state.get(
                "rdw_motor", "-"
            )
        )

    st.caption(
        "Handelsbenaming: "
        + st.session_state.get(
            "rdw_handelsbenaming", "-"
        )
    )

    st.caption(
        "Kenteken: "
        + st.session_state.get(
            "rdw_kenteken", "-"
        )
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# SECTIE 3: DIAGNOSEFORMULIER
# ============================================================

st.divider()

st.subheader("2. Diagnosegegevens")

with st.form("diagnose_form"):

    c1, c2 = st.columns(2)

    with c1:

        model = st.text_input(
            "Mercedes-Benz model",
            key="rdw_model",
            placeholder="Bijvoorbeeld C-Klasse"
        )

        bouwjaar = st.text_input(
            "Bouwjaar",
            key="rdw_jaar",
            placeholder="Bijvoorbeeld 2018"
        )

        handelsbenaming = st.text_input(
            "Handelsbenaming",
            key="rdw_handelsbenaming",
            placeholder="Bijvoorbeeld C 220 D"
        )

    with c2:

        motorisering = st.text_input(
            "Motor / Brandstof",
            key="rdw_motor",
            placeholder="Bijvoorbeeld OM654 / Diesel"
        )

        kilometerstand = st.text_input(
            "Kilometerstand",
            placeholder="Bijvoorbeeld 145000"
        )

        foutcode = st.text_input(
            "Storingscode(s) / DTC",
            placeholder="Bijvoorbeeld P0401 of P2002"
        )

    klacht = st.text_area(
        "Omschrijving klacht en symptomen",
        placeholder=(
            "Beschrijf de klacht zo uitgebreid mogelijk. "
            "Bijvoorbeeld: motor houdt in rond 2000 toeren, "
            "motorlamp brandt en voertuig heeft vermogensverlies."
        ),
        height=150
    )

    extra_info = st.text_area(
        "Extra informatie (optioneel)",
        placeholder=(
            "Bijvoorbeeld: klacht koud/warm, "
            "eerder uitgevoerde reparaties, meetwaarden..."
        ),
        height=90
    )

    submit = st.form_submit_button(
        "GENEREER MERCEDES DIAGNOSE",
        use_container_width=True
    )


# ============================================================
# SECTIE 4: DIAGNOSE UITVOEREN
# ============================================================

if submit:

    if not model.strip() or not klacht.strip():

        st.warning(
            "Vul minimaal het model en de klacht in."
        )

    else:

        volledige_klacht = klacht

        if extra_info.strip():

            volledige_klacht += (
                "\n\nExtra informatie:\n"
                + extra_info
            )

        with st.spinner(
            "Gemini analyseert de voertuiggegevens en klacht..."
        ):

            try:

                diagnose = genereer_diagnose(
                    model=model,
                    bouwjaar=bouwjaar,
                    handelsbenaming=handelsbenaming,
                    motorisering=motorisering,
                    kilometerstand=kilometerstand,
                    foutcode=foutcode,
                    klacht=volledige_klacht
                )

                st.session_state[
                    "laatste_diagnose"
                ] = diagnose

            except Exception as e:

                st.error(
                    "Diagnose kon niet worden gegenereerd: "
                    + str(e)
                )


# ============================================================
# SECTIE 5: DIAGNOSE RESULTAAT TONEN
# ============================================================

if st.session_state.get("laatste_diagnose"):

    st.divider()

    st.subheader(
        "3. Mercedes-Benz Diagnoseadvies"
    )

    st.markdown(
        st.session_state["laatste_diagnose"]
    )

    st.download_button(
        label="DOWNLOAD DIAGNOSE ALS TEKSTBESTAND",
        data=st.session_state["laatste_diagnose"],
        file_name="Wensink_Mercedes_Diagnose.txt",
        mime="text/plain",
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Wensink Mercedes-Benz Diagnose Assistent | "
    "RDW Open Data + Google Gemini"
)

# ============================================================
# EINDE DEEL 3
# ============================================================

# ============================================================
# DEEL 4A: INTERACTIEVE GEMINI VERVOLGCHAT
# ============================================================

def genereer_vervolgantwoord(chat_history, vraag):

    api_key = st.secrets.get("GOOGLE_API_KEY", "")

    if not api_key:
        raise ValueError("Google API-sleutel ontbreekt.")

    systeem_prompt = """
Je bent de Mercedes-Benz Master Technician van
de Wensink Diagnose Assistent.

Je voert een doorlopende technische diagnose uit.

BELANGRIJK:

1. Onthoud alle eerdere voertuiggegevens.
2. Onthoud de oorspronkelijke klacht.
3. Onthoud alle eerder besproken storingscodes.
4. Gebruik de eerdere diagnose als uitgangspunt.
5. Verwerk nieuwe meetwaarden en testresultaten.
6. Pas je eerdere conclusies aan als nieuwe informatie
   daar aanleiding toe geeft.
7. Stel gerichte vervolgvragen wanneer informatie ontbreekt.
8. Geef praktische vervolgstappen voor de monteur.
9. Verzin geen technische specificaties of meetwaarden.
10. Maak onderscheid tussen vermoedens en bewezen defecten.
11. Verwijs bij modelspecifieke fabrieksgegevens naar XENTRY
    of officiële Mercedes-Benz documentatie.

Geef antwoord in professioneel Nederlands.

Je hoeft de volledige eerdere diagnose niet steeds te herhalen.
Concentreer je op de nieuwe vraag en de volgende diagnosestap.
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.8-flash:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    # Volledige eerdere gespreksgeschiedenis meesturen

    inhoud = chat_history + [
        {
            "role": "user",
            "parts": [
                {"text": vraag}
            ]
        }
    ]

    payload = {
        "contents": inhoud,
        "systemInstruction": {
            "parts": [
                {"text": systeem_prompt}
            ]
        },
        "generationConfig": {
            "temperature": 0.2
        }
    }

    for poging in range(1, 4):

        try:

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=90
            )

            if response.status_code in (
                429, 500, 502, 503, 504
            ):

                if poging < 3:
                    time.sleep(2 * poging)
                    continue

            response.raise_for_status()

            resultaat = response.json()

            kandidaten = resultaat.get(
                "candidates", []
            )

            if not kandidaten:
                raise ValueError(
                    "Gemini heeft geen antwoord teruggegeven."
                )

            onderdelen = kandidaten[0].get(
                "content", {}
            ).get("parts", [])

            antwoord = "\n".join(
                onderdeel.get("text", "")
                for onderdeel in onderdelen
                if onderdeel.get("text")
            )

            if not antwoord:
                raise ValueError(
                    "Gemini heeft een leeg antwoord teruggegeven."
                )

            return antwoord

        except requests.exceptions.HTTPError:

            if poging == 3:
                raise

            time.sleep(2 * poging)

        except requests.exceptions.RequestException:

            if poging == 3:
                raise

            time.sleep(2 * poging)

    raise RuntimeError(
        "De vervolgdiagnose kon niet worden gegenereerd."
    )


# ============================================================
# EINDE DEEL 4A
# ============================================================

# ============================================================
# DEEL 4B: INTERACTIEVE DIAGNOSECHAT
# ============================================================

if st.session_state.get("laatste_diagnose"):

    st.divider()

    st.subheader("4. Verdieping en vervolgvragen")

    st.write(
        "Stel aanvullende vragen over deze diagnose. "
        "Gemini onthoudt de eerdere voertuiggegevens, "
        "klacht en diagnose."
    )

    # GESPREKSGESCHIEDENIS OPHALEN

    chat_history = st.session_state.get(
        "chat_history", []
    )

    # EERDERE BERICHTEN TONEN
    # De eerste twee berichten zijn de oorspronkelijke
    # voertuiggegevens en diagnose.

    for bericht in chat_history[2:]:

        if bericht["role"] == "user":

            with st.chat_message("user"):

                st.markdown(
                    bericht["parts"][0]["text"]
                )

        elif bericht["role"] == "model":

            with st.chat_message("assistant"):

                st.markdown(
                    bericht["parts"][0]["text"]
                )

    # NIEUWE VRAAG INVOEREN

    nieuwe_vraag = st.chat_input(
        "Stel een vervolgvraag over deze Mercedes...",
        key="diagnose_chat_input"
    )

    if nieuwe_vraag:

        with st.chat_message("user"):

            st.markdown(nieuwe_vraag)

        with st.chat_message("assistant"):

            with st.spinner(
                "Gemini analyseert de vervolggegevens..."
            ):

                try:

                    antwoord = genereer_vervolgantwoord(
                        chat_history,
                        nieuwe_vraag
                    )

                    # VRAAG OPSLAAN

                    st.session_state["chat_history"].append(
                        {
                            "role": "user",
                            "parts": [
                                {"text": nieuwe_vraag}
                            ]
                        }
                    )

                    # ANTWOORD OPSLAAN

                    st.session_state["chat_history"].append(
                        {
                            "role": "model",
                            "parts": [
                                {"text": antwoord}
                            ]
                        }
                    )

                    st.markdown(antwoord)

                except Exception as e:

                    st.error(
                        "Vervolgdiagnose mislukt: " + str(e)
                    )


# ============================================================
# EINDE DEEL 4B
# ============================================================

# ============================================================
# DEEL 5: NIEUWE DIAGNOSE STARTEN
# ============================================================

st.divider()

st.subheader("5. Nieuwe diagnose starten")

st.write(
    "Kies hieronder of je een ander voertuig wilt "
    "invoeren of een nieuwe diagnose voor hetzelfde voertuig wilt starten."
)

col_nieuw, col_zelfde = st.columns(2)

# ============================================================
# KNOP 1: NIEUW VOERTUIG
# ============================================================

with col_nieuw:

    if st.button(
        "NIEUW VOERTUIG",
        use_container_width=True,
        type="primary"
    ):

        # VOERTUIGGEGEVENS WISSEN

        voertuig_sleutels = [
            "rdw_model",
            "rdw_jaar",
            "rdw_motor",
            "rdw_handelsbenaming",
            "rdw_kenteken"
        ]

        for sleutel in voertuig_sleutels:

            st.session_state.pop(
                sleutel,
                None
            )

        # OUDE DIAGNOSE EN CHAT WISSEN

        diagnose_sleutels = [
            "laatste_diagnose",
            "chat_history",
            "diagnose_chat_input"
        ]

        for sleutel in diagnose_sleutels:

            st.session_state.pop(
                sleutel,
                None
            )

        st.success(
            "Alle voertuig- en diagnosegegevens zijn gewist."
        )

        st.rerun()


# ============================================================
# KNOP 2: ZELFDE VOERTUIG
# ============================================================

with col_zelfde:

    if st.button(
        "ZELFDE VOERTUIG",
        use_container_width=True
    ):

        # VOERTUIGGEGEVENS BLIJVEN BEWAARD

        # ALLEEN OUDE DIAGNOSEGEGEVENS WISSEN

        diagnose_sleutels = [
            "laatste_diagnose",
            "chat_history",
            "diagnose_chat_input"
        ]

        for sleutel in diagnose_sleutels:

            st.session_state.pop(
                sleutel,
                None
            )

        st.success(
            "Nieuwe diagnose gestart. "
            "De voertuiggegevens zijn behouden."
        )

        st.rerun()


# ============================================================
# EINDE DEEL 5
# ============================================================
