import streamlit as st
import time

# Pagina-instellingen
st.set_page_config(page_title="TEST - Werkplaats AI", page_icon="🚗", layout="centered")

st.title("🚗 Werkplaats AI - VERBINDINGSTEST")
st.info("Dit is de testmodus. Er worden nog geen kosten gemaakt bij OpenAI.")

# Invoerformulier voor de monteur
with st.form("diagnose_form"):
    col1, col2 = st.columns(2)
    with col1:
        merk = st.text_input("Merk auto", placeholder="Bijv. Volkswagen")
        model = st.text_input("Model", placeholder="Bijv. Golf 7")
    with col2:
        bouwjaar = st.text_input("Bouwjaar", placeholder="Bijv. 2015")
        motorisering = st.text_input("Motor / Brandstof", placeholder="Bijv. 1.2 TSI")

    klacht = st.text_area("Omschrijving van de klacht", 
                          placeholder="Bijv. Tikken in de motor bij koude start.")
    
    submit_button = st.form_submit_button(label="Test Diagnose Knop")

# Wat er gebeurt als de monteur op de knop drukt:
if submit_button:
    if not klacht or not merk:
        st.warning("Vul tenminste het merk en de klacht in om te testen.")
    else:
        with st.spinner("Verbinding testen met de hoofdcomputer..."):
            time.sleep(1.5) # Dit simuleert de wachttijd van de AI
            
            st.success("✅ VERBINDING SUCCESVOL!")
            st.markdown(f"""
            ### Ontvangen gegevens op de hoofdcomputer:
            * **Voertuig:** {merk} {model} ({bouwjaar}) - {motorisering}
            * **Ingevoerde klacht:** {klacht}
            
            *Als je dit blok ziet op de tablet, werkt de netwerkverbinding in de werkplaats perfect!*
            """)
