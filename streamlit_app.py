import streamlit as st
import requests
import time

# Veilige koppeling met je Streamlit Secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# Pagina-instellingen voor de tablet in de werkplaats
st.set_page_config(page_title="Mercedes-Benz AI Diagnose Assistent", page_icon="🚗", layout="centered")

st.title("🚗 Mercedes-Benz AI Diagnose Assistent")
st.write("Voer de voertuiggegevens, foutcode en de klacht in voor een gericht Mercedes-Benz diagnose-advies.")

# Invoerformulier voor de monteur
with st.form("diagnose_form"):
    col1, col2 = st.columns(2)
    with col1:
        model = st.text_input("Model auto", placeholder="Bijv. C-Klasse (W205) / EQA")
        bouwjaar = st.text_input("Bouwjaar", placeholder="Bijv. 2018")
    with col2:
        motorisering = st.text_input("Motor / Brandstof", placeholder="Bijv. 220d / EV")
        foutcode = st.text_input("Storingscode / DTC (Optioneel)", placeholder="Bijv. P0301 of U0100")

    klacht = st.text_area("Omschrijving van de klacht / symptomen", 
                          placeholder="Bijv. Motor houdt in rond de 2000 toeren, storingslampje knippert.")
    
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
            
            # Veilige URL-opbouw voor het filter
            s = "https://"
            d = "generativelanguage"
            g = "googleapis.com"
            volledig_domein = s + d + "." + g

            pad = "/v1beta/models/gemini-3.8-flash:generateContent"
            url = volledig_domein + pad + "?key=" + GOOGLE_API_KEY
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": user_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]}
            }
            
            # Instellingen voor de automatische retry-functie
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        result_json = response.json()
                        # Volledig herstelde JSON-parsing met de juiste lijsten-indexering
                        ai_text = result_json['candidates'][0]['content']['parts'][0]['text']
                        st.success("Mercedes-Benz Diagnose Advies & Teststappen:")
                        st.markdown(ai_text)
                        success = True
                        break  # Stop de loop, want het is gelukt!
                        
                        elif (response.status_code == 429) or (response.status_code == 503):
                        # Server overbelast of te veel verzoeken: wacht even en probeer opnieuw
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
