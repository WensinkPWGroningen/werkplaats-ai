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
    k = kenteken.replace("-", "").replace(" ", "").upper()
    try:
        v = requests.get("https://rdw.nl" + k).json()[0]
        b_res = requests.get("https://rdw.nl" + k).json()
        
        # Hybride en brandstofbepaling
        omschrijvingen = [b.get("brandstof_omschrijving", "").upper() for b in b_res if b]
        brandstof = "Onbekend"
        if len(omschrijvingen) > 0:
            if any("ELEKTR" in o for o in omschrijvingen) and any(o for o in omschrijvingen if "BENZ" in o or "DIES" in o):
                r = v.get("handelsbenaming", "").upper()
                brandstof = "Plug-in Hybride" if ("PLUG" in r or r.endswith("E") or "PHEV" in r) else "Hybride"
            else:
                brandstof = b_res[0].get("brandstof_omschrijving", "Onbekend")

        if v.get("merk", "").upper() != "MERCEDES-BENZ":
            return "GEEN_MERCEDES"
            
        r = v.get("handelsbenaming", "Onbekend").upper()
        schoon = "Mercedes-Benz"
        for m in ["C-KLASSE", "E-KLASSE", "A-KLASSE", "B-KLASSE", "S-KLASSE", "GLA", "GLC", "GLE", "CLA", "SPRINTER", "VITO"]:
            if m in r or (m[0] == r[0] and "-KLASSE" in m):
                schoon = m.title()
                break
        return {"model": schoon, "jaar": v.get("datum_eerste_toelating", "0000")[:4], "motor": brandstof}
    except:
        return None

# Interface
col1, col2 = st.columns([1, 5])
col1.image(LOGO_B64, width=70)
col2.title("Wensink Diagnose Assistent")
st.write("Voer de gegevens in voor een gericht Mercedes-Benz diagnose-advies.")

kenteken_invoer = st.text_input("Voer kenteken in voor automatische overname", placeholder="Bijv. GG-123-X")

if st.button("Haal voertuiggegevens op") and kenteken_invoer:
    with st.spinner("Gegevens ophalen..."):
        data = haal_rdw_data(kenteken_invoer)
        if data == "GEEN_MERCEDES":
            st.error("Dit kenteken is niet van een Mercedes-Benz.")
        elif data:
            st.session_state["rdw_model"], st.session_state["rdw_jaar"], st.session_state["rdw_motor"] = data["model"], data["jaar"], data["motor"]
            st.success("Voertuig succesvol opgehaald!")
            st.rerun()
        else:
            st.warning("Kenteken niet gevonden. Vul de velden handmatig in.")

with st.form("diagnose_form"):
    c1, c2 = st.columns(2)
    model = c1.text_input("Model auto", key="rdw_model", placeholder="Bijv. C-Klasse")
    bouwjaar = c1.text_input("Bouwjaar", key="rdw_jaar", placeholder="Bijv. 2018")
    motorisering = c2.text_input("Motor / Brandstof", key="rdw_motor", placeholder="Bijv. 220d")
    foutcode = c2.text_input("Storingscode / DTC (Optioneel)", placeholder="Bijv. P0301")
    klacht = st.text_area("Omschrijving van de klacht / symptomen", placeholder="Symptomen...")
    submit = st.form_submit_button("Genereer Diagnose")

if submit and model and klacht:
    with st.spinner("Google AI analyseert de klacht..."):
        sys_p = "Jij bent een Mercedes Master Tech. Geef dealeradvies (Top 3 oorzaken, Xentry teststappen, bekende kwalen, onderdelen)."
        user_p = "Model: " + str(model) + " (" + str(bouwjaar) + ") Motor: " + str(motorisering) + " DTC: " + str(foutcode) + " Klacht: " + str(klacht)
        url = "https://googleapis.com" + st.secrets["GOOGLE_API_KEY"]
        payload = {"contents": [{"parts": [{"text": user_p}]}], "systemInstruction": {"parts": [{"text": sys_p}]}}
        
        poging, succes = 1, False
        while poging <= 3 and not succes:
            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code == 200:
                    st.success("Diagnose Advies:")
                    st.markdown(res.json()["candidates"][0]["content"]["parts"][0]["text"])
                    succes = True
                else:
                    time.sleep(2)
                    poging += 1
            except:
                time.sleep(2)
                poging += 1
        if not succes:
            st.error("AI-systeem onbereikbaar. Probeer het over een paar minuten nog eens.")
elif submit:
    st.warning("Vul tenminste het model en de klacht in.")
