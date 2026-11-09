import base64
import re
import requests
import streamlit as st

# ============================================================
# WENSINK MERCEDES-BENZ DIAGNOSE ASSISTENT
# Herbouwde basis: RDW + Gemini + stapsgewijze vervolgdiagnose
# ============================================================

st.set_page_config(
    page_title="Wensink Mercedes Diagnose",
    page_icon="ðŸš˜",
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

    st.title("Wensink Diagnose Assistent")
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
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_nieuw_voertuig():
    keys = [
        "rdw_kenteken", "rdw_model", "rdw_jaar", "rdw_motor",
        "rdw_handelsbenaming", "rdw_voertuigsoort", "rdw_cilinderinhoud",
        "rdw_vermogen", "rdw_transmissie", "laatste_diagnose", "kenteken_invoer",
        "kilometerstand", "foutcode", "klacht", "extra_info",
        "diagnose_fotos", "diagnose_foto_upload", "laatste_kenteken_opgehaald",
    ]
    for key in keys:
        st.session_state[key] = "" if key not in ("diagnose_fotos",) else []
    st.session_state.chat_history = []
    st.session_state.reset_melding = "Nieuw voertuig gestart. De vorige voertuig- en diagnosegegevens zijn gewist."


def reset_zelfde_voertuig():
    keys = ["kilometerstand", "foutcode", "klacht", "extra_info", "laatste_diagnose", "diagnose_fotos", "diagnose_foto_upload"]
    for key in keys:
        st.session_state[key] = [] if key == "diagnose_fotos" else ""
    st.session_state.chat_history = []
    st.session_state.reset_melding = "Nieuwe diagnose gestart voor hetzelfde voertuig."


# -------------------- RDW --------------------

def normaliseer_kenteken(kenteken):
    return re.sub(r"[^A-Z0-9]", "", (kenteken or "").upper())


def rdw_get(url, kenteken, limit):
    headers = {
        "Accept": "application/json",
        "User-Agent": "Wensink-Mercedes-Diagnose/2.0",
    }
    response = requests.get(
        url,
        params={"kenteken": kenteken, "$limit": limit},
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def haal_rdw_data(kenteken):
    kenteken = normaliseer_kenteken(kenteken)
    if not kenteken:
        return None

    voertuigen = rdw_get(RDW_VOERTUIG_URL, kenteken, 1)
    if not voertuigen:
        return None

    voertuig = voertuigen[0]
    merk = (voertuig.get("merk") or "").strip().upper()
    if merk not in ("MERCEDES-BENZ", "MERCEDES BENZ"):
        return "GEEN_MERCEDES"

    brandstofregels = rdw_get(RDW_BRANDSTOF_URL, kenteken, 10)
    brandstoffen = [
        (item.get("brandstof_omschrijving") or "").upper()
        for item in brandstofregels
    ]
    elektrisch = any("ELEKTR" in item for item in brandstoffen)
    benzine = any("BENZINE" in item for item in brandstoffen)
    diesel = any("DIESEL" in item for item in brandstoffen)

    if elektrisch and (benzine or diesel):
        brandstof = "Hybride"
    elif elektrisch:
        brandstof = "Elektrisch"
    elif benzine:
        brandstof = "Benzine"
    elif diesel:
        brandstof = "Diesel"
    elif brandstoffen:
        brandstof = ", ".join(dict.fromkeys(brandstoffen))
    else:
        brandstof = "Onbekend volgens RDW"

    handelsbenaming = (voertuig.get("handelsbenaming") or "Onbekend").strip()
    eerste_toelating = str(
        voertuig.get("datum_eerste_toelating")
        or voertuig.get("datum_eerste_toelating_dt")
        or ""
    )
    bouwjaar = eerste_toelating[:4] if len(eerste_toelating) >= 4 else "Onbekend"

    return {
        "kenteken": kenteken,
        "merk": merk,
        "model": handelsbenaming,
        "handelsbenaming": handelsbenaming,
        "jaar": bouwjaar,
        "motor": brandstof,
        "voertuigsoort": voertuig.get("voertuigsoort", "Onbekend"),
        "cilinderinhoud": voertuig.get("cilinderinhoud", ""),
        "vermogen": voertuig.get("vermogen_massarijklaar", ""),
        "transmissie": voertuig.get("transmissie", ""),
    }


# -------------------- GEMINI --------------------

MASTER_TECHNICIAN_PROMPT = """
Je bent de digitale Mercedes-Benz Master Technician van de Wensink werkplaats.
Je ondersteunt professionele monteurs bij systematische foutdiagnose.

WERKWIJZE
- Denk als een ervaren diagnosetechnicus: systematisch, kritisch en stap voor stap.
- Gebruik alle beschikbare voertuiggegevens, klachtinformatie, DTC's, meetwaarden,
  uitgevoerde tests en eerdere berichten in deze sessie.
- Begin met de drie meest waarschijnlijke oorzaken en motiveer de rangschikking.
- Maak steeds onderscheid tussen BEWEZEN, AANNEMELIJK en NOG NIET ONDERZOCHT.
- Geef concrete, veilige en logisch geordende controles.
- Vraag gericht om de meetwaarde of testuitslag die de diagnose verder kan bewijzen
  of uitsluiten. Stel niet tien algemene vragen tegelijk: kies de belangrijkste
  volgende test(s).
- Vermeld bij relevante stappen welke XENTRY-functie, actuele waarde,
  actuatortest of begeleide test de monteur kan raadplegen.
- Benoem welke aanvullende gegevens nodig zijn als motorcode, VIN, bouwjaar,
  transmissievariant of exacte ECU-versie bepalend zijn.
- Leg uit wat een afwijkende en een normale meetuitkomst betekent.
- Pas de waarschijnlijkheid van oorzaken aan zodra nieuwe resultaten binnenkomen.
- Sluit een diagnose niet als bewezen af zonder voldoende meet- of testbewijs.

BETROUWBAARHEID
- Verzin geen Mercedes-fabriekswaarden, aanhaalmomenten, pinbezettingen,
  testplannen, servicebulletins of bekende productmaatregelen.
- Je hebt niet automatisch toegang tot live XENTRY, WIS, VeDoc of Mercedes-
  fabrieksdocumentatie. Zeg dat eerlijk wanneer informatie daaruit gecontroleerd
  moet worden.
- Geef bij ontbrekende of variantafhankelijke specificaties aan dat de monteur
  deze in actuele Mercedes-documentatie moet controleren.
- Geef veiligheidswaarschuwingen bij hoogvoltagesystemen, airbags, brandstofdruk,
  draaiende delen en andere gevaarlijke werkzaamheden.
- Adviseer geen onderdelen te vervangen uitsluitend op basis van een foutcode.
- Als een vraag buiten de beschikbare informatie valt, zeg dat en vraag om
  relevante gegevens in plaats van te gokken.

RAPPORTOPBOUW BIJ DE EERSTE DIAGNOSE
1. Samenvatting voertuig en klacht
2. Eerste technische beoordeling
3. Top 3 waarschijnlijke oorzaken (met argumenten en zekerheid)
4. Diagnoseplan in prioriteitsvolgorde
5. Benodigde XENTRY-gegevens en meetwaarden
6. Wat de mogelijke testresultaten betekenen
7. Veiligheids- en aandachtspunten
8. Voorlopige conclusie en eerstvolgende actie

Bij vervolgvragen: antwoord gericht op de nieuwe informatie, behoud de volledige
diagnosecontext en geef aan hoe de nieuwe informatie de eerdere diagnose verandert.
Schrijf in professioneel, duidelijk Nederlands voor een automonteur.
"""


def get_api_key():
    key = st.secrets.get("GOOGLE_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
    return str(key).strip()


def get_model():
    return str(st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash")).strip()


def extract_gemini_text(data):
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = data.get("promptFeedback", {})
        reason = feedback.get("blockReason", "geen kandidaatantwoord ontvangen")
        raise RuntimeError(f"Gemini heeft geen antwoord teruggegeven ({reason}).")
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    if not text_parts:
        raise RuntimeError("Gemini gaf een leeg antwoord terug.")
    return "\n".join(text_parts).strip()


def roep_gemini_aan(contents):
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY ontbreekt in Streamlit secrets. "
            "Voeg je bestaande Google AI API-sleutel toe."
        )

    model = get_model()
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": MASTER_TECHNICIAN_PROMPT.strip()}]},
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        },
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                detail = response.text
            raise RuntimeError(f"Google Gemini API ({response.status_code}): {detail}")
        return extract_gemini_text(response.json())
    except requests.Timeout:
        raise RuntimeError("De verbinding met Gemini duurde te lang. Probeer het opnieuw.")
    except requests.RequestException as exc:
        raise RuntimeError(f"Verbindingsfout met Gemini: {exc}")


def maak_foto_parts(uploaded_files):
    parts = []
    for uploaded in uploaded_files or []:
        image_bytes = uploaded.getvalue()
        mime_type = uploaded.type or "image/jpeg"
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        })
    return parts


def genereer_eerste_diagnose(prompt, foto_parts):
    contents = [{
        "role": "user",
        "parts": [{"text": prompt}] + foto_parts,
    }]
    antwoord = roep_gemini_aan(contents)
    # Bewaar de oorspronkelijke vraag inclusief afbeeldingen voor de vervolgchat.
    return antwoord, contents


def genereer_vervolgantwoord(chat_history, vraag):
    inhoud = list(chat_history)
    inhoud.append({"role": "user", "parts": [{"text": vraag.strip()}]})
    antwoord = roep_gemini_aan(inhoud)
    return antwoord, {"role": "user", "parts": [{"text": vraag.strip()}]}, {
        "role": "model", "parts": [{"text": antwoord}]
    }


# -------------------- PAGINA --------------------

st.markdown(
    "<h1 class='main-title'>Wensink Mercedes-Benz Diagnose Assistent</h1>",
    unsafe_allow_html=True,
)


if st.session_state.reset_melding:
    st.success(st.session_state.reset_melding)
    st.session_state.reset_melding = ""

st.divider()

# -------------------- VOERTUIG OPHALEN --------------------

st.subheader("Voertuiggegevens")
kenteken_invoer = st.text_input(
    "Kenteken invoeren",
    key="kenteken_invoer",
    placeholder="Bijvoorbeeld: XX-123-X",
)

if kenteken_invoer:
    schoon_kenteken = normaliseer_kenteken(kenteken_invoer)
    if schoon_kenteken and schoon_kenteken != st.session_state.laatste_kenteken_opgehaald:
        with st.spinner("Voertuiggegevens ophalen bij de RDW..."):
            try:
                voertuig_data = haal_rdw_data(schoon_kenteken)
                if voertuig_data == "GEEN_MERCEDES":
                    st.error("Dit voertuig is geen Mercedes-Benz. Deze assistent ondersteunt alleen Mercedes-Benz.")
                    st.session_state.rdw_kenteken = ""
                    st.session_state.laatste_kenteken_opgehaald = schoon_kenteken
                elif voertuig_data is None:
                    st.warning("Geen voertuig gevonden bij de RDW. Controleer het kenteken.")
                    st.session_state.rdw_kenteken = ""
                    st.session_state.laatste_kenteken_opgehaald = schoon_kenteken
                else:
                    st.session_state.rdw_kenteken = voertuig_data["kenteken"]
                    st.session_state.rdw_model = voertuig_data["model"]
                    st.session_state.rdw_jaar = voertuig_data["jaar"]
                    st.session_state.rdw_motor = voertuig_data["motor"]
                    st.session_state.rdw_handelsbenaming = voertuig_data["handelsbenaming"]
                    st.session_state.rdw_voertuigsoort = voertuig_data["voertuigsoort"]
                    st.session_state.rdw_cilinderinhoud = voertuig_data["cilinderinhoud"]
                    st.session_state.rdw_vermogen = voertuig_data["vermogen"]
                    st.session_state.rdw_transmissie = voertuig_data["transmissie"]
                    st.session_state.laatste_kenteken_opgehaald = schoon_kenteken
            except requests.RequestException as exc:
                st.error(f"De RDW-koppeling is tijdelijk niet bereikbaar: {exc}")
            except Exception as exc:
                st.error(f"Fout bij ophalen voertuiggegevens: {exc}")

if st.session_state.rdw_kenteken:
    extra_voertuigregels = []
    if st.session_state.rdw_cilinderinhoud:
        extra_voertuigregels.append(f"Cilinderinhoud: {st.session_state.rdw_cilinderinhoud} cc")
    if st.session_state.rdw_vermogen:
        extra_voertuigregels.append(f"Vermogen (RDW-veld): {st.session_state.rdw_vermogen}")
    if st.session_state.rdw_transmissie:
        extra_voertuigregels.append(f"Transmissie: {st.session_state.rdw_transmissie}")

    st.markdown(
        f"""
        <div class="vehicle-card">
          <strong>âœ“ Geregistreerd voertuig: Mercedes-Benz {st.session_state.rdw_model}</strong><br>
          Kenteken: {st.session_state.rdw_kenteken}<br>
          <small>Handelsbenaming: {st.session_state.rdw_handelsbenaming}
          &nbsp;|&nbsp; Eerste toelating: {st.session_state.rdw_jaar}
          &nbsp;|&nbsp; Brandstof: {st.session_state.rdw_motor}
          &nbsp;|&nbsp; Voertuigsoort: {st.session_state.rdw_voertuigsoort}</small>
          {"<br><small>" + " | ".join(extra_voertuigregels) + "</small>" if extra_voertuigregels else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Let op: RDW-gegevens identificeren niet altijd de exacte motorcode, uitvoering of ECU-variant. Controleer die zo nodig via VIN/XENTRY.")

# -------------------- WERKPLAATSINVOER --------------------

st.subheader("Werkplaatsgegevens")
col1, col2 = st.columns(2)
with col1:
    st.text_input("Kilometerstand (km)", key="kilometerstand")
    st.text_input("Actieve storingscodes / DTC's", key="foutcode", placeholder="Bijv. P0299, P0101, Uxxxx")
with col2:
    st.text_area("Klachtomschrijving van de klant", key="klacht", height=110)
    st.text_area("Extra parameters, meetwaarden en reeds uitgevoerde tests", key="extra_info", height=110)

st.write("**Foto's toevoegen (optioneel, maximaal 3)**")
fotos = st.file_uploader(
    "Voeg foto's toe van bijvoorbeeld componenten, lekkages, schade of meetresultaten.",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key="diagnose_foto_upload",
)
if fotos:
    if len(fotos) > MAX_FOTOS:
        st.warning(f"Je kunt maximaal {MAX_FOTOS} foto's toevoegen. Alleen de eerste {MAX_FOTOS} worden gebruikt.")
        fotos = fotos[:MAX_FOTOS]
    te_groot = [f.name for f in fotos if f.size > MAX_FOTO_GROOTTE_MB * 1024 * 1024]
    if te_groot:
        st.error(
            f"Deze foto('s) zijn groter dan {MAX_FOTO_GROOTTE_MB} MB en worden niet meegestuurd: "
            + ", ".join(te_groot)
        )
    geldige_fotos = [f for f in fotos if f.size <= MAX_FOTO_GROOTTE_MB * 1024 * 1024]
    if geldige_fotos:
        st.caption(f"{len(geldige_fotos)} foto('s) klaar om mee te sturen.")
        preview_cols = st.columns(min(len(geldige_fotos), 3))
        for index, foto in enumerate(geldige_fotos):
            with preview_cols[index]:
                st.image(foto, caption=foto.name, use_container_width=True)

# -------------------- EERSTE DIAGNOSE --------------------

st.divider()
if st.button("START DIAGNOSE", use_container_width=True):
    if not st.session_state.rdw_kenteken:
        st.warning("Haal eerst een geldig Mercedes-Benz voertuig op via het kenteken.")
    elif not st.session_state.klacht.strip() and not st.session_state.foutcode.strip():
        st.warning("Voer minimaal een klachtomschrijving of een storingscode in.")
    else:
        try:
            with st.spinner("Analyse wordt uitgevoerd..."):
                foto_parts = []
                if fotos:
                    geldige_fotos = [
                        foto for foto in fotos
                        if foto.size <= MAX_FOTO_GROOTTE_MB * 1024 * 1024
                    ][:MAX_FOTOS]
                    foto_parts = maak_foto_parts(geldige_fotos)

                gebruikers_prompt = f"""
NIEUWE DIAGNOSE-AANVRAAG

VOERTUIGGEGEVENS UIT RDW
- Merk: Mercedes-Benz
- Model/handelsbenaming: {st.session_state.rdw_model}
- Kenteken: {st.session_state.rdw_kenteken}
- Eerste toelating/bouwjaarveld: {st.session_state.rdw_jaar}
- Brandstof volgens RDW: {st.session_state.rdw_motor}
- Voertuigsoort: {st.session_state.rdw_voertuigsoort}
- Cilinderinhoud: {st.session_state.rdw_cilinderinhoud or 'Niet beschikbaar'}
- Vermogensveld RDW: {st.session_state.rdw_vermogen or 'Niet beschikbaar'}
- Transmissieveld RDW: {st.session_state.rdw_transmissie or 'Niet beschikbaar'}

WERKPLAATSINFORMATIE
- Kilometerstand: {st.session_state.kilometerstand or 'Niet opgegeven'}
- DTC/storingscodes: {st.session_state.foutcode or 'Geen opgegeven'}
- Klachtomschrijving: {st.session_state.klacht or 'Geen opgegeven'}
- Extra informatie, meetwaarden en uitgevoerde tests: {st.session_state.extra_info or 'Geen opgegeven'}

Analyseer de klacht volgens de afgesproken rapportopbouw. Benoem expliciet welke cruciale voertuigidentificatie of meetwaarden nog ontbreken. Geef daarna de belangrijkste eerstvolgende test waarmee de monteur onderscheid kan maken tussen de waarschijnlijkste oorzaken.
"""
                antwoord, eerste_contents = genereer_eerste_diagnose(gebruikers_prompt, foto_parts)
                st.session_state.laatste_diagnose = antwoord
                st.session_state.chat_history = eerste_contents + [
                    {"role": "model", "parts": [{"text": antwoord}]}
                ]
            st.rerun()
        except Exception as exc:
            st.error(f"InitiÃ«le diagnose genereren mislukt: {exc}")

# -------------------- DIAGNOSERAPPORT --------------------

if st.session_state.laatste_diagnose:
    st.divider()
    st.subheader("Wensink Master Technician - Diagnose")
    st.markdown(st.session_state.laatste_diagnose)

# -------------------- VERVOLGDIAGNOSE --------------------

if st.session_state.laatste_diagnose:
    st.divider()
    st.subheader("Stap voor stap verder diagnosticeren")
    st.write(
        "Geef de meetwaarden, testuitslagen of aanvullende informatie door. "
        
    )

    for bericht in st.session_state.chat_history[2:]:
        rol = bericht.get("role")
        if rol not in ("user", "model"):
            continue
        # De eerste gebruikersbeurt bevat eventueel foto's; toon alleen tekst.
        tekst = "\n".join(
            part.get("text", "")
            for part in bericht.get("parts", [])
            if isinstance(part, dict) and part.get("text")
        )
        if not tekst:
            continue
        with st.chat_message("user" if rol == "user" else "assistant"):
            st.markdown(tekst)

    nieuwe_vraag = st.chat_input("Geef een meetwaarde, testuitslag of vervolgvraag...")
    if nieuwe_vraag:
        try:
            with st.spinner("Analyse wordt uitgevoerd..."):
                antwoord, user_turn, model_turn = genereer_vervolgantwoord(
                    st.session_state.chat_history,
                    nieuwe_vraag,
                )
                st.session_state.chat_history.extend([user_turn, model_turn])
                # Bewaar de oorspronkelijke diagnose; vervolgantwoorden blijven in de chatgeschiedenis.
            st.rerun()
        except Exception as exc:
            st.error(f"Vervolgdiagnose mislukt: {exc}")

st.divider()
st.caption(
    "Wensink Mercedes-Benz Werkplaats Assistent. AI-advies is ondersteunend: "
    "controleer veiligheidskritische werkzaamheden en fabriekswaarden altijd in actuele Mercedes-documentatie."
)

st.divider()
st.subheader("Nieuwe diagnose of nieuw voertuig")
st.caption("Kies hieronder of je met hetzelfde voertuig verder wilt met een nieuwe diagnose, of een ander voertuig wilt invoeren.")
reset_col1, reset_col2 = st.columns(2)
with reset_col1:
    if st.button("NIEUWE DIAGNOSE STARTEN", use_container_width=True):
        reset_nieuw_voertuig()
        st.rerun()
with reset_col2:
    if st.button("NIEUWE DIAGNOSE (ZELFDE AUTO)", use_container_width=True):
        reset_zelfde_voertuig()
        st.rerun()


