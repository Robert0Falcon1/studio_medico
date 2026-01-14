from __future__ import annotations

import base64
import json
import os
from datetime import date, datetime, timezone

import requests
import streamlit as st

st.set_page_config(page_title="Studio Medico", layout="wide")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")



# JWT helpers (solo per UI, senza verifica firma)

def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def jwt_is_expired(token: str) -> bool:
    p = jwt_payload(token)
    exp = p.get("exp")
    try:
        exp_int = int(exp)
    except Exception:
        return False

    now = int(datetime.now(tz=timezone.utc).timestamp())
    return now >= (exp_int - 5)



def jwt_username(token: str) -> str:
    p = jwt_payload(token)
    return str(p.get("username") or p.get("sub") or "utente")



# HTTP client (con JWT)

def api_get(path: str, token: str | None = None, params: dict | None = None) -> dict | list:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=10)

    if r.status_code == 401:
        raise PermissionError("401 Unauthorized (token non valido/scaduto oppure backend riavviato).")

    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{API_BASE}{path}", headers=headers, json=payload, timeout=10)

    if r.status_code == 401:
        raise PermissionError("401 Unauthorized (token non valido/scaduto oppure backend riavviato).")

    r.raise_for_status()
    return r.json()


def api_login(username: str, password: str) -> str:
    # OAuth2PasswordRequestForm => x-www-form-urlencoded
    r = requests.post(
        f"{API_BASE}/api/auth/login",
        data={"username": username, "password": password},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def is_logged_in() -> bool:
    token = st.session_state.get("token")
    return bool(token) and isinstance(token, str) and len(token) > 0


def do_logout() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("auth_error", None)
    st.rerun()


def require_auth() -> str | None:
    token = st.session_state.get("token")
    if not token:
        st.warning("Sezione riservata. Effettua il login dalla sidebar.")
        return None

    if jwt_is_expired(token):
        st.error("Sessione scaduta. Effettua Logout dalla sidebar e rifai login.")
        return None

    return token




# Sidebar login

with st.sidebar:
    st.header("Accesso")

    token = st.session_state.get("token")

    if not is_logged_in():
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", key="login_btn"):
            try:
                new_token = api_login(u.strip().lower(), p)
                st.session_state["token"] = new_token
                st.session_state.pop("auth_error", None)
                st.success("Login effettuato.")
                st.rerun()
            except requests.HTTPError:
                st.error("Credenziali non valide.")
            except Exception as e:
                st.error(str(e))
    else:
        # Mostro info dal token senza chiamare /api/me (evita logout su rerun)
        user = jwt_username(token)
        st.write(f"Utente: **{user}**")

        if st.session_state.get("auth_error"):
            st.error(st.session_state["auth_error"])

        if st.button("Logout", key="logout_btn"):
            do_logout()

    st.divider()
    st.caption(f"API: {API_BASE}")



# UI

st.title("Sistema Studio Medico (API REST + JWT + Streamlit)")

tab1, tab2, tab3, tab4 = st.tabs(["Prenotazioni", "Agenda Medico", "Pazienti", "Notifiche"])



# Dati base (pubblici)

@st.cache_data(ttl=10)
def load_medici() -> list[dict]:
    return api_get("/api/medici")  # public


@st.cache_data(ttl=10)
def load_sale() -> list[dict]:
    return api_get("/api/sale")  # public


@st.cache_data(ttl=10)
def load_tipi() -> list[dict]:
    return api_get("/api/tipi-visita")  # public



# TAB 1 - Prenotazioni

with tab1:
    st.subheader("Prenota appuntamento")

    try:
        medici = load_medici()
        sale = load_sale()
        tipi = load_tipi()
    except Exception as e:
        st.error(f"API non raggiungibile o errore: {e}")
        st.stop()

    colA, colB, colC = st.columns(3)

    with colA:
        medico = st.selectbox(
            "Medico",
            options=medici,
            format_func=lambda m: f"{m['cognome']} {m['nome']} ({m['specializzazione']})",
            key="pren_medico",
        )
        sala = st.selectbox(
            "Sala",
            options=sale,
            format_func=lambda s: s["nome"],
            key="pren_sala",
        )

    with colB:
        tipo = st.selectbox(
            "Tipo visita",
            options=tipi,
            format_func=lambda t: f"{t['nome']} ({t['durata_minuti']} min)",
            key="pren_tipo",
        )
        start_date = st.date_input("Data", value=date.today(), key="pren_data")
        start_time = st.time_input(
            "Ora",
            value=datetime.now().time().replace(second=0, microsecond=0),
            key="pren_ora",
        )

    with colC:
        note = st.text_area("Note (opzionale)", height=100, key="pren_note")
        waitlist = st.checkbox("Se pieno, inserisci in lista d'attesa", value=True, key="pren_waitlist")

    st.divider()

    token = st.session_state.get("token")

    if not is_logged_in():
        st.info("Prenotazione pubblica (senza login): inserisci i dati del paziente.")

        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome paziente", key="pub_nome")
        cognome = c2.text_input("Cognome paziente", key="pub_cognome")
        email = st.text_input("Email (opzionale)", key="pub_email")
        tel = st.text_input("Telefono (opzionale)", key="pub_tel")

        if st.button("Conferma prenotazione (pubblica)", key="pren_pub_submit"):
            if not nome.strip() or not cognome.strip():
                st.error("Nome e cognome del paziente sono obbligatori.")
            else:
                start_dt = datetime.combine(start_date, start_time)
                payload = {
                    "medico_id": medico["id"],
                    "tipo_visita_id": tipo["id"],
                    "sala_id": sala["id"],
                    "start": start_dt.isoformat(),
                    "note": note or None,
                    "inserisci_waitlist_se_pieno": waitlist,
                    "nome": nome.strip(),
                    "cognome": cognome.strip(),
                    "email": email.strip() or None,
                    "telefono": tel.strip() or None,
                }
                try:
                    res = api_post("/api/public/prenotazioni", payload)
                    if res.get("ok") and res.get("appuntamento_id"):
                        st.success(f"{res.get('messaggio')} (ID: {res.get('appuntamento_id')})")
                    elif res.get("ok") and res.get("messo_in_waitlist"):
                        st.warning(res.get("messaggio"))
                    else:
                        st.error(res.get("messaggio") or "Errore prenotazione.")
                except Exception as e:
                    st.error(str(e))

    else:
        st.success("Modalità interna (loggato): seleziona un paziente esistente.")

        if jwt_is_expired(token):
            st.error("Sessione scaduta. Premi Logout e rifai login.")
        else:
            try:
                pazienti = api_get("/api/pazienti", token=token)
            except PermissionError as e:
                st.session_state["auth_error"] = str(e)
                st.error("Sessione non valida. Premi Logout e rifai login.")
                pazienti = []
            except Exception as e:
                # non logout automatico: errore temporaneo
                st.error(f"Errore caricamento pazienti: {e}")
                pazienti = []

            paziente = st.selectbox(
                "Paziente",
                options=pazienti,
                format_func=lambda p: f"{p['cognome']} {p['nome']} ({p.get('email') or '-'}) | {p.get('telefono') or '-'}",
                key="pren_paziente",
            )

            if st.button("Conferma prenotazione (interna)", key="pren_int_submit", disabled=not bool(pazienti)):
                start_dt = datetime.combine(start_date, start_time)
                payload = {
                    "paziente_id": paziente["id"],
                    "medico_id": medico["id"],
                    "tipo_visita_id": tipo["id"],
                    "sala_id": sala["id"],
                    "start": start_dt.isoformat(),
                    "note": note or None,
                    "inserisci_waitlist_se_pieno": waitlist,
                }
                try:
                    res = api_post("/api/appuntamenti", payload, token=token)
                    if res.get("ok") and res.get("appuntamento_id"):
                        st.success(f"{res.get('messaggio')} (ID: {res.get('appuntamento_id')})")
                    elif res.get("ok") and res.get("messo_in_waitlist"):
                        st.warning(res.get("messaggio"))
                    else:
                        st.error(res.get("messaggio") or "Errore prenotazione.")
                except PermissionError as e:
                    st.session_state["auth_error"] = str(e)
                    st.error("Sessione non valida. Premi Logout e rifai login.")
                except Exception as e:
                    st.error(str(e))



# TAB 2 - Agenda medico (PROTETTO)

with tab2:
    st.subheader("Agenda giornaliera (sezione riservata)")

    token = require_auth()
    if token:
        medici = load_medici()

        medico_agenda = st.selectbox(
            "Medico",
            options=medici,
            format_func=lambda m: f"{m['cognome']} {m['nome']} ({m['specializzazione']})",
            key="agenda_medico",
        )
        giorno = st.date_input("Giorno", value=date.today(), key="agenda_giorno")

        try:
            items = api_get(
                "/api/agenda",
                token=token,
                params={"medico_id": medico_agenda["id"], "giorno": giorno.isoformat()},
            )
            if not items:
                st.info("Nessun appuntamento per questo giorno.")
            else:
                for a in items:
                    st.write(
                        f"- **{a['inizio']} - {a['fine']}** | "
                        f"Tipo: {a['tipo_visita']} | Sala: {a['sala']} | Stato: {a['stato']} | Note: {a['note'] or '-'}"
                    )
        except PermissionError as e:
            st.session_state["auth_error"] = str(e)
            st.error("Sessione non valida. Premi Logout e rifai login.")
        except Exception as e:
            st.error(f"Errore agenda: {e}")



# TAB 3 - Pazienti (PROTETTO)

with tab3:
    st.subheader("Gestione pazienti (sezione riservata)")

    token = require_auth()
    if token:
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
                    try:
                        res = api_post(
                            "/api/pazienti",
                            {"nome": nome.strip(), "cognome": cognome.strip(), "email": email.strip() or None, "telefono": tel.strip() or None},
                            token=token,
                        )
                        st.success(f"Paziente creato: {res.get('paziente_id')}")
                    except PermissionError as e:
                        st.session_state["auth_error"] = str(e)
                        st.error("Sessione non valida. Premi Logout e rifai login.")
                    except Exception as e:
                        st.error(str(e))

        st.divider()
        st.write("Elenco pazienti:")

        try:
            pazienti = api_get("/api/pazienti", token=token)
            if not pazienti:
                st.info("Nessun paziente presente.")
            else:
                for p in pazienti:
                    st.write(f"- {p['cognome']} {p['nome']} | {p.get('email') or '-'} | {p.get('telefono') or '-'}")
        except PermissionError as e:
            st.session_state["auth_error"] = str(e)
            st.error("Sessione non valida. Premi Logout e rifai login.")
        except Exception as e:
            st.error(f"Errore caricamento pazienti: {e}")



# TAB 4 - Notifiche (PROTETTO)

with tab4:
    st.subheader("Notifiche pendenti (sezione riservata)")

    token = require_auth()
    if token:
        try:
            pendenti = api_get("/api/notifiche/pendenti", token=token, params={"limit": 200})
            if not pendenti:
                st.info("Nessuna notifica pendente.")
            else:
                for n in pendenti:
                    paz = n.get("paziente") or "-"

                    msg = (n.get("messaggio") or "").strip()

                    prefix = "Appuntamento confermato per "
                    if msg.startswith(prefix):
                        tail = msg[len(prefix):].strip().rstrip(".")  # es: "13/01/2026 16:00"
                        parts = tail.split()
                        if len(parts) >= 2:
                            d, t = parts[0], parts[1]
                            msg = f"Appuntamento confermato per il {d} h {t}."

                    st.write(f"[{n['id']}] **{n['tipo']}** | Paziente: **{paz}** - {msg}")

        except PermissionError as e:
            st.session_state["auth_error"] = str(e)
            st.error("Sessione non valida. Premi Logout e rifai login.")
        except Exception as e:
            st.error(f"Errore notifiche: {e}")
