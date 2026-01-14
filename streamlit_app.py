from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from backend.seed import seed_base
from backend.services import (
    agenda_giornaliera_flat,
    crea_paziente,
    estrai_notifiche_pendenti,
    init_db,
    lista_medici_flat,
    lista_pazienti_flat,
    lista_sale_flat,
    lista_tipi_visita_flat,
    prenota_appuntamento,
)

st.set_page_config(page_title="Studio Medico", layout="wide")


# =========================
# Bootstrap DB
# =========================
# Nota: NON usare st.stop nei tab: fermerebbe l'intera app e "sparirebbero" gli altri tab.
init_db()
seed_base()

st.title("Sistema Studio Medico (SQLite + SQLAlchemy + Streamlit)")

tab1, tab2, tab3, tab4 = st.tabs(["Prenotazioni", "Agenda Medico", "Pazienti", "Notifiche"])


# =========================
# Cache lookup (UI)
# =========================
@st.cache_data(ttl=10)
def load_medici() -> list[dict]:
    return lista_medici_flat()


@st.cache_data(ttl=10)
def load_pazienti() -> list[dict]:
    return lista_pazienti_flat()


@st.cache_data(ttl=10)
def load_sale() -> list[dict]:
    return lista_sale_flat()


@st.cache_data(ttl=10)
def load_tipi_visita() -> list[dict]:
    return lista_tipi_visita_flat()


# =========================
# TAB 1 - Prenotazioni
# =========================
with tab1:
    st.subheader("Prenota appuntamento")

    medici = load_medici()
    pazienti = load_pazienti()
    sale = load_sale()
    tipi = load_tipi_visita()

    # Se mancano dati base, mostro errore ma NON fermo l'app
    if not medici or not sale or not tipi:
        st.error("Dati di base mancanti. Esegui: `python -m backend.cli init` (oppure verifica il seed).")

    # Se mancano pazienti, mostro warning ma lascio gli altri tab utilizzabili
    if not pazienti:
        st.warning("Nessun paziente presente. Vai nel tab 'Pazienti' e creane uno, poi torna qui.")

    colA, colB, colC = st.columns(3)

    with colA:
        medico = st.selectbox(
            "Medico",
            options=medici if medici else [{"id": "", "nome": "-", "cognome": "-", "specializzazione": "-"}],
            format_func=lambda m: f"{m['cognome']} {m['nome']} ({m['specializzazione']})",
            key="pren_medico",
            index=0,
        )

        sala = st.selectbox(
            "Sala",
            options=sale if sale else [{"id": 0, "nome": "-"}],
            format_func=lambda s: s["nome"],
            key="pren_sala",
            index=0,
        )

    with colB:
        tipo = st.selectbox(
            "Tipo visita",
            options=tipi if tipi else [{"id": 0, "nome": "-", "durata_minuti": 0}],
            format_func=lambda t: f"{t['nome']} ({t['durata_minuti']} min)",
            key="pren_tipo",
            index=0,
        )

        start_date = st.date_input("Data", value=date.today(), key="pren_data")
        start_time = st.time_input(
            "Ora",
            value=datetime.now().time().replace(second=0, microsecond=0),
            key="pren_ora",
        )

    with colC:
        paziente = st.selectbox(
            "Paziente",
            options=pazienti if pazienti else [{"id": "", "nome": "-", "cognome": "-", "email": None, "telefono": None}],
            format_func=lambda p: f"{p['cognome']} {p['nome']} ({p.get('email') or '-'})",
            key="pren_paziente",
            index=0,
        )

        note = st.text_area("Note (opzionale)", height=100, key="pren_note")
        waitlist = st.checkbox("Se pieno, inserisci in lista d'attesa", value=True, key="pren_waitlist")

    # Abilita prenotazione solo se i dati sono reali
    can_book = bool(medici) and bool(sale) and bool(tipi) and bool(pazienti) and paziente.get("id") and medico.get("id")

    if st.button("Conferma prenotazione", key="pren_submit", disabled=not can_book):
        start_dt = datetime.combine(start_date, start_time)

        esito = prenota_appuntamento(
            paziente_id=paziente["id"],
            medico_id=medico["id"],
            tipo_visita_id=tipo["id"],
            sala_id=sala["id"],
            start=start_dt,
            note=note or None,
            inserisci_waitlist_se_pieno=waitlist,
        )

        if esito.ok and esito.appuntamento_id:
            st.success(f"{esito.messaggio} (ID: {esito.appuntamento_id})")
        elif esito.ok and esito.messo_in_waitlist:
            st.warning(esito.messaggio)
        else:
            st.error(esito.messaggio)

        # Aggiorna liste/notifiche/agenda
        st.cache_data.clear()

    st.divider()
    st.caption("Se il pulsante è disabilitato: crea prima almeno 1 paziente (tab 'Pazienti').")


# =========================
# TAB 2 - Agenda medico
# =========================
with tab2:
    st.subheader("Agenda giornaliera")

    medici = load_medici()
    if not medici:
        st.warning("Nessun medico disponibile. Esegui: `python -m backend.cli init` (oppure verifica il seed).")
        # Non blocco il tab: mostro solo placeholder
        st.stop()

    medico_agenda = st.selectbox(
        "Medico",
        options=medici,
        format_func=lambda m: f"{m['cognome']} {m['nome']} ({m['specializzazione']})",
        key="agenda_medico",
        index=0,
    )
    giorno = st.date_input("Giorno", value=date.today(), key="agenda_giorno")

    items = agenda_giornaliera_flat(medico_agenda["id"], giorno)
    if not items:
        st.info("Nessun appuntamento per questo giorno.")
    else:
        for a in items:
            st.write(
                f"- **{a['inizio']} - {a['fine']}** | "
                f"Tipo: {a['tipo_visita']} | Sala: {a['sala']} | Stato: {a['stato']} | Note: {a['note'] or '-'}"
            )


# =========================
# TAB 3 - Pazienti
# =========================
with tab3:
    st.subheader("Gestione pazienti")

    with st.expander("Crea nuovo paziente"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", key="paz_nome")
        cognome = c2.text_input("Cognome", key="paz_cognome")
        email = st.text_input("Email (opzionale)", key="paz_email")
        tel = st.text_input("Telefono (opzionale)", key="paz_tel")

        if st.button("Crea paziente", key="paz_submit"):
            if not nome.strip() or not cognome.strip():
                st.error("Nome e cognome sono obbligatori.")
            else:
                pid = crea_paziente(nome, cognome, email or None, tel or None)
                st.success(f"Paziente creato: {pid}")
                st.cache_data.clear()

    st.divider()
    st.write("Elenco pazienti:")
    pazienti = load_pazienti()
    if not pazienti:
        st.info("Nessun paziente presente.")
    else:
        for p in pazienti:
            st.write(f"- {p['cognome']} {p['nome']} | {p.get('email') or '-'} | {p.get('telefono') or '-'}")


# =========================
# TAB 4 - Notifiche
# =========================
with tab4:
    st.subheader("Notifiche pendenti (simulazione)")

    pendenti = estrai_notifiche_pendenti(limit=200)
    if not pendenti:
        st.info("Nessuna notifica pendente.")
    else:
        for n in pendenti:
            st.write(f"[{n.id}] **{n.tipo.value}** | {n.creata_il.strftime('%d/%m/%Y %H:%M')} | {n.messaggio}")

    st.caption("Invio simulato: `python -m backend.cli notifications --mark-sent`")
