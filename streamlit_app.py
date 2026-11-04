import streamlit as st
import time

# Pagina-instellingen
st.set_page_config(page_title="TEST - Werkplaats AI", page_icon="🚗", layout="centered")

st.title("🚗 Werkplaats AI - VERBINDINGSTEST")
st.info("Dit is de testmodus (Zonder merk, mét storingscode). Er worden nog geen kosten gemaakt.")

# Invoerformulier voor de monteur (Aangepast voor Merkdealer)
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
    
    submit_button = st.form_submit_button(label="Test Diagnose Knop")

# Wat er gebeurt als de monteur op de knop drukt:
if submit_button:
    if not model or not klacht:
        st.warning("Vul tenminste het model en de klacht in om te testen.")
    else:
        with st.spinner("Gegevens verwerken..."):
            time.sleep(1.5) # Simuleert de AI wachttijd
            
            st.success("✅ SCHERM GEUPDATE!")
            st.markdown(f"""
            ### Ontvangen gegevens voor de AI:
            * **Model:** {model} ({bouwjaar})
            * **Motor:** {motorisering}
            * **Ingevoerde Storingscode:** {foutcode if foutcode else 'Geen foutcode ingevoerd'}
            * **Klacht:** {klacht}
            
            *Dit formulier is nu perfect afgestemd op jullie merkdealer-werkplaats!*
            """)
