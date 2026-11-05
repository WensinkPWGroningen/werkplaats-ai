import streamlit as st
import requests
import time

# Compact Mercedes-Benz logo Base64 string
LOGO_B64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAMAAAAYrfwNAAAAYFBM"
    "VEVHcEwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADXg6S"
    "0AAAAAnRSTlMA9wYGCQoLDA0OERITFRcYGRobHB0eHyAhIiMkJSYnKCkqKywt77b9OgAA"
    "AAlwSFlzAAAOxAAADsQBlbkmDwAAAGRJREFUeNrtlcsWwyAMREfBwY/y/3/txI3bJnUT1"
    "2MGmYfN69mRbMHOp1gURfEnKHbe0/XOnmshug6gP/RHEEIDoW6E3I3rNoIeBfAgBAH6wZ"
    "9BcAbCvIDuBOsdmB0fXhRF8f0P8lsO6X8mC0UAAAAASUVORK5CYII="
)

st.set_page_config(page_title="Wensink Mercedes Diagnose", page_icon=LOGO_B64, layout="centered")

def haal_rdw_data(kenteken):
    # Verwijder streepjes en spaties
    k = kenteken.replace("-", "").replace(" ", "").upper()
    try:
        # Haal de basis voertuiggegevens op via het stabiele RDW basis-endpoint
        v_url = "https://rdw.nl" + str(k)
        v_resp = requests.get(v_url, timeout=5)
        v_json = v_resp.json()
        
        if not v_json or not isinstance(v_json, list) or len(v_json) == 0:
            return None
            
        # Pak het eerste voertuig-object veilig uit de lijst door de list-methoden te omzeilen
        v = None
        for item in v_json:
            v = item
            break
            
        if not v:
            return None
        
        # Haal de bijbehorende brandstofgegevens op via het brandstof-endpoint
        b_url = "https://rdw.nl" + str(k)
        b_resp = requests.get(b_url, timeout=5)
        b_json = b_resp.json()
        
        brandstof = "Onbekend"
        if b_json and isinstance(b_json, list) and len(b_json) > 0:
            # Verzamel alle brandstofomschrijvingen voor hybride-controle
            omschrijvingen = []
            for b in b_json:
                if b:
                    o = b.get("brandstof_omschrijving", "").upper()
                    if o:
                        omschrijvingen.append(o)
            
            heeft_elektro = any("ELEKTR" in o for o in omschrijvingen)
            heeft_brandstofmotor = any("BENZ" in o or "DIES" in o for o in omschrijvingen)
            
            if heeft_elektro and heeft_brandstofmotor:
                r = v.get("handelsbenaming", "").upper()
                if "PLUG" in r or r.endswith("E") or "PHEV" in r:
                    brandstof = "Plug-in Hybride"
                else:
                    brandstof = "Hybride"
            else:
                # Pak de brandstofomschrijving van het eerste element uit de lus om indexen te omzeilen
                for first_b in b_json:
                    brandstof = first_b.get("brandstof_omschrijving", "Onbekend")
                    break

        # Controleer of het voertuig een Mercedes-Benz is
        if v.get("merk", "").upper() != "MERCEDES-BENZ":
            return "GEEN_MERCEDES"
            
        # Slimme model-opschoning voor Mercedes handelsbenamingen
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
            
        return {"model": schoon_model, "jaar": v.get("datum_eerste_toelating", "0000")[:4], "motor": brandstof}
    except Exception as e:
        print("RDW Fout: " + str(e))
        return None

# Interface opbouw
col1, col2 = st.columns()
with col1:
    st.image(LOGO_B64, width=65)
with col2:
    st.title("Wensink Diagnose Assistent")
st.write("Voer de voertuiggegevens, foutcode en de klacht in voor een gericht Mercedes-Benz diagnose-advies.")

kenteken_invoer = st.text_input("Voer kenteken in voor automatische overname", placeholder="Bijv. GG-123-X")

if st.button("Haal voertuiggegevens op") and kenteken_invoer:
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

with st.form("diagnose_form"):
    c1, c2 = st.columns(2)
    with c1:
        model = st.text_input("Model auto", key="rdw_model", placeholder="Bijv. C-Klasse (W205)")
        bouwjaar = st.text_input("Bouwjaar", key="rdw_jaar", placeholder="Bijv. 2018")
    with c2:
        motorisering = st.text_input("Motor / Brandstof", key="rdw_motor", placeholder="Bijv. 220d / EV")
        foutcode = st.text_input("Storingscode / DTC (Optioneel)", placeholder="Bijv. P0301 of U0100")
        
    klacht = st.text_area("Omschrijving van de klacht / symptomen", placeholder="Bijv. Motor houdt in rond de 2000 toeren...")
    submit = st.form_submit_button("Genereer Diagnose & Teststappen")

if submit and model and klacht:
    with st.spinner("Google AI analyseert de klacht..."):
        sys_p = "Jij bent een gecertificeerde Mercedes-Benz Master Technician bij een officiële merkdealer. Geef op basis van de voertuiggegevens, eventuele storingscodes (DTC's) and de klacht een technisch diagnose-advies. Gebruik de vaste structuur: 1. Meest waarschijnlijke oorzaak (Top 3), 2. Gericht stappenplan & teststappen (Meten is weten!), 3. Bekende kwalen voor dit model, 4. Potentieel te vervangen onderdelen."
        user_p = "Merk: Mercedes-Benz\nModel: " + str(model) + " (" + str(bouwjaar) + ")\nMotor: " + str(motorisering) + "\nStoringscode: " + str(foutcode if foutcode else "Geen") + "\nKlacht: " + str(klacht)
        
        url = "https://googleapis.com" + st.secrets["GOOGLE_API_KEY"]
        payload = {"contents": [{"parts": [{"text": user_p}]}], "systemInstruction": {"parts": [{"text": sys_p}]}}
        
        poging = 1
        succes = False
        while poging <= 3 and not succes:
            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code == 200:
                    st.success("Mercedes-Benz Diagnose Advies & Teststappen:")
                    st.markdown(res.json()["candidates"]["content"]["parts"]["text"])
                    succes = True
                else:
                    time.sleep(2)
                    poging += 1
            except:
                time.sleep(2)
                poging += 1
                
        if not succes:
            st.error("Het AI-systeem is momenteel overbelast of onbereikbaar. Probeer het over een paar minuten nog eens.")
elif submit:
    st.warning("Vul tenminste het model en de klacht van de klant in.")
