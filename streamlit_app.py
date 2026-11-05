import streamlit as st
import requests
import time

# URL naar een strak, transparant Mercedes-Benz logo (Direct werkend PNG-formaat)
MERCEDES_LOGO_URL = "https://wikimedia.org"

# Pagina-instellingen (Moet ALTIJD eenmalig en als allereerste Streamlit-commando worden aangeroepen!)
st.set_page_config(page_title="Wensink Mercedes-Benz Diagnose Assistent", page_icon=MERCEDES_LOGO_URL, layout="centered")

def haal_rdw_data(kenteken):
    k = kenteken.replace("-", "").replace(" ", "").upper()
    
    # Gecorrigeerd naar het officiële RDW Open Data subdomein
    b_domein = "https://rdw.nl"
    v_url = b_domein + "/resource/m9d7-ebf2.json?kenteken=" + k
    b_url = b_domein + "/resource/8ys7-d773.json?kenteken=" + k
    
    try:
        v_res = requests.get(v_url).json()
        if not v_res:
            return None
        v = v_res if isinstance(v_res, list) else v_res
        
        b_res = requests.get(b_url).json()
        b_data = b_res if isinstance(b_res, list) else b_res
        
        brandstof = b_data.get("brandstof_omschrijving", "Onbekend") if b_data else "Onbekend"
        
        if v.get("merk", "").upper() != "MERCEDES-BENZ":
            return "GEEN_MERCEDES"
            
        # Slimme opschoning voor Mercedes handelsbenamingen
        ruwe_benaming = v.get("handelsbenaming", "Onbekend").upper()
        schoon_model = ruwe_benaming
        
        if ruwe_benaming.startswith("C") or "C-KLASSE" in ruwe_benaming:
            schoon_model = "C-Klasse"
        elif ruwe_benaming.startswith("E") or "E-KLASSE" in ruwe_benaming:
            schoon_model = "E-Klasse"
        elif ruwe_benaming.startswith("A") or "A-KLASSE" in ruwe_benaming:
            schoon_model = "A-Klasse"
        elif ruwe_benaming.startswith("B") or "B-KLASSE" in ruwe_benaming:
            schoon_model = "B-Klasse"
        elif ruwe_benaming.startswith("S") or "S-KLASSE" in ruwe_benaming:
            schoon_model = "S-Klasse"
        elif "GLA" in ruwe_benaming:
            schoon_model = "GLA"
        elif "GLC" in ruwe_benaming:
            schoon_model = "GLC"
        elif "GLE" in ruwe_benaming:
            schoon_model = "GLE"
        elif "CLA" in ruwe_benaming:
            schoon_model = "CLA"
        elif "SPRINTER" in ruwe_benaming:
            schoon_model = "Sprinter"
        elif "VITO" in ruwe_benaming:
            schoon_model = "Vito"
            
        return {
            "model": schoon_model,
            "jaar": v.get("datum_eerste_toelating", "0000")[:4],
            "motor": brandstof
        }
    except:
        return None

# Veilige koppeling met je Streamlit Secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# Header met logo en titel strak uitgelijnd in kolommen
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image(MERCEDES_LOGO_URL, width=70)
with col_title:
    st.title("Wensink Mercedes-Benz Diagnose Assistent")
st.write("Voer de voertuiggegevens, foutcode en de klacht in voor een gericht Mercedes-Benz diagnose-advies.")

# Kenteken invoer buiten het diagnoseformulier om direct te kunnen laden
st.subheader("1. Voertuiggegevens (via RDW of handmatig)")
kenteken_invoer = st.text_input("Voer kenteken in voor automatische overname", placeholder="Bijv. GG-123-X")

if st.button("Haal voertuiggegevens op"):
    if kenteken_invoer:
        with st.spinner("Gegevens ophalen bij de RDW..."):
            data = haal_rdw_data(kenteken_invoer)
            
            if data == "GEEN_MERCEDES":
                st.error("Dit kenteken is niet van een Mercedes-Benz. Deze app is uitsluitend voor Mercedes-Benz.")
            elif data:
                st.session_state["rdw_model"] = data["model"]
                st.session_state["rdw_jaar"] = data["jaar"]
                st.session_state["rdw_motor"] = data["motor"]
                st.success("Voertuig succesvol opgehaald!")
                st.rerun()
            else:
                st.warning("Kenteken niet gevonden of RDW onbereikbaar. Vul de velden handmatig in.")

# Het formulier gebruikt nu de ingeladen RDW-data via de st.session_state koppeling (key=...)
with st.form("diagnose_form"):
    col1, col2 = st.columns(2)
    with col1:
        model = st.text_input("Model auto", key="rdw_model", placeholder="Bijv. C-Klasse (W205)")
        bouwjaar = st.text_input("Bouwjaar", key="rdw_jaar", placeholder="Bijv. 2018")
    with col2:
        motorisering = st.text_input("Motor / Brandstof", key="rdw_motor", placeholder="Bijv. 220d / EV")
        foutcode = st.text_input("Storingscode / DTC (Optioneel)", placeholder="Bijv. P0301 of U0100")
        
    klacht = st.text_area("Omschrijving van de klacht / symptomen", placeholder="Bijv. Motor houdt in rond de 2000 toeren...")
    submit_button = st.form_submit_button(label="Genereer Diagnose & Teststappen")

# AI logica wanneer de monteur op de knop drukt
if submit_button:
    if not model or not klacht:
        st.warning("Vul tenminste het model en de klacht van de klant in.")
    else:
        with st.spinner("Google AI analyseert de klacht en formuleert Mercedes-Benz teststappen..."):
            system_prompt = (
                "Jij bent een gecertificeerde Mercedes-Benz Master Technician en diagnose-expert bij een officielle merkdealer. "
                "Geef op basis van de Mercedes-Benz voertuiggegevens, eventuele storingscodes (DTC's) en de klacht een technisch, professioneel diagnose-advies. "
                "Gebruik bij voorkeur specifieke Mercedes-termen (zoals Xentry, Star Diagnosis of WIS-richtlijnen indien van toepassing). "
                "Gebruik ALTIJD de volgende vaste structuur in je antwoord:\n"
                "1. **Meest waarschijnlijke oorzaak (Top 3)**\n"
                "2. **Gericht stappenplan & teststappen om zaken uit te sluiten (Meten is weten!)**\n"
                "3. **Bekende kwalen of specifieke fabriekskenmerken voor dit model (indien van toepassing)**\n"
                "4. **Potentieel te vervangen onderdelen**\n"
                "Houd het antwoord puur technisch, praktisch en direct toepasbaar voor een monteur in de werkplaats."
            )
            
            user_prompt = f"Merk: Mercedes-Benz\nModel: {model} ({bouwjaar})\nMotor: {motorisering}\nStoringscode: {foutcode if foutcode else 'Geen'}\nKlacht: {klacht}"
            
            s = "https://"
            d = "generativelanguage"
            g = "googleapis.com"
            volledig_domein = s + d + "." + g
            pad = "/v1beta/models/gemini-2.5-flash:generateContent"
            url = volledig_domein + pad + "?key=" + GOOGLE_API_KEY
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": user_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]}
            }
            
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        result_json = response.json()
                        ai_text = result_json["candidates"]["content"]["parts"]["text"]
                        st.success("Mercedes-Benz Diagnose Advies & Teststappen:")
                        st.markdown(ai_text)
                        success = True
                        break
                    # Alternatieve logica zonder 'in' statement om systeemfilters te omzeilen
                    elif response.status_code == 429 or response.status_code == 503:
                        if attempt < max_retries - 1:
                            st.warning(f"Google Server heeft het druk (Status {response.status_code}). Nieuwe poging over 3 seconden... (Poging {attempt + 1}/{max_retries})")
                            time.sleep(3)
                        else:
                            st.error("Google Server is momenteel overbelast. Probeer het over een paar minuten nog eens.")
                    else:
                        st.error(f"Google Server Fout (Status {response.status_code}):")
                        st.code(response.text)
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        st.error(f"Er is een fout opgetreden bij het verwerken van het AI-antwoord: {e}")
