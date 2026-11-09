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
if st.button("🔥 START MASTER TECHNICIAN ANALYSE", use_container_width=True):
    if not st.session_state.rdw_kenteken:
        st.warning("Haal eerst een geldig Mercedes-Benz voertuig op via het kenteken.")
    elif not st.session_state.klacht.strip() and not st.session_state.foutcode.strip():
        st.warning("Voer minimaal een klachtomschrijving of een storingscode in.")
    else:
        try:
            with st.spinner("De Master Technician analyseert voertuig, klacht, DTC's en beschikbare foto's..."):
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
            st.error(f"Initiële diagnose genereren mislukt: {exc}")

# -------------------- DIAGNOSERAPPORT --------------------

if st.session_state.laatste_diagnose:
    st.divider()
    st.subheader("📋 Wensink Master Technician – Diagnose")
    st.markdown(st.session_state.laatste_diagnose)

# -------------------- VERVOLGDIAGNOSE --------------------

if st.session_state.laatste_diagnose:
    st.divider()
    st.subheader("💬 Stap voor stap verder diagnosticeren")
    st.write(
        "Geef de meetwaarden, testuitslagen of aanvullende informatie door. "
        "De Master Technician bouwt voort op de volledige eerdere diagnose."
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
            with st.spinner("De Master Technician verwerkt de nieuwe bevindingen..."):
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
