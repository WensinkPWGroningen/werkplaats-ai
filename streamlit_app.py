import streamlit as st
import requests

# Jouw unieke Google AI-sleutel
GOOGLE_API_KEY = "AQ.Ab8RN6JUgEScnQVhSO8DCb6pAwQ1qWZaj3pbvQYef7l3NJw7TA"

# Pagina-instellingen voor de tablet
st.set_page_config(page_title="Werkplaats AI Diagnose Assistent", page_icon="🚗", layout="centered")

st.title("🚗 Werkplaats AI Diagnose Assistent")
st.write("Voer de voertuiggegevens, foutcode en de klacht in voor een gericht diagnose-advies inclusief teststappen.")

# Invoerformulier voor de monteur
with st.form("diagnose_form"):
    col1, col2 = st.columns(2)
    with col1:
        model = st.text_input("Model auto", placeholder="Bijv. Golf 7 / ID.4")
        bouwjaar = st.text_input("Bouwjaar", placeholder="Bijv. 2018")
    with col2:
        motorisering = st.text_input("Motor / Brandstof", placeholder="Bijv. 1.5 TSI / EV")
        foutcode = st.text_input("Storingscode / DTC (Optioneel)", placeholder="Bijv. P0301 of U0100")

    klacht = st.text_area("Omschrijving van de klacht / symptomen", 
                          placeholder="Bijv. Motor houdt in rond de 2000 toeren, storingslampje knippert.")
    
    submit_button = st.form_submit_button(label="Genereer Diagnose & Teststappen")

# AI logica wanneer de monteur op de knop drukt
if submit_button:
    if not model or not klacht:
        st.warning("Vul tenminste het model en de klacht van de klant in.")
    else:
        with st.spinner("Google AI analyseert de klacht en formuleert teststappen..."):
            
            # De strikte instructies voor de AI
            system_prompt = (
                "Jij bent een master-technicus en diagnose-expert bij een officiële merkdealer. "
                "Geef op basis van de voertuiggegevens, eventuele storingscodes (DTC's) en de klacht een technisch, professioneel diagnose-advies. "
                "Gebruik ALTIJD de volgende vaste structuur in je antwoord:\n"
                "1. **Meest waarschijnlijke oorzaak (Top 3)**\n"
                "2. **Gericht stappenplan & teststappen om zaken uit te sluiten (Meten is weten!)**\n"
                "3. **Bekende kwalen of specifieke fabriekskenmerken voor dit model (indien van toepassing)**\n"
                "4. **Potentieel te vervangen onderdelen**\n"
                "Houd het antwoord puur technisch, praktisch en direct toepasbaar voor een monteur in de werkplaats."
            )
            
            user_prompt = f"Model: {model} ({bouwjaar})\nMotor: {motorisering}\nStoringscode: {foutcode if foutcode else 'Geen'}\nKlacht: {klacht}"
            
            # DE GEFIKSTE URL: Nu met een strakke scheiding tussen de website en de API-sleutel (?key=)
            url = "https://googleapis.com"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # We sturen de sleutel mee als een 'parameter' in plaats van hem in de basistekst te plakken
            params = {
                "key": GOOGLE_API_KEY
            }
            
            # De JSON-structuur voor Google Gemini
            payload = {
                "contents": [{
                    "parts": [{"text": user_prompt}]
                }],
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                }
            }
            
            try:
                # We voegen 'params=params' toe om de sleutel veilig en correct te versturen naar de juiste poort
                response = requests.post(url, headers=headers, json=payload, params=params)
                
                if response.status_code != 200:
                    st.error(f"Google Server Fout (Status {response.status_code}):")
                    st.code(response.text)
                else:
                    result_json = response.json()
                    ai_text = result_json['candidates'][0]['content']['parts'][0]['text']
                    st.success("Diagnose Advies & Teststappen (Aangedreven door Google AI):")
                    st.markdown(ai_text)
                
            except Exception as e:
                st.error(f"Er is een fout opgetreden bij het uitlezen van de AI: {e}")
