from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

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
    notifiche_pendenti_flat
)
from backend.seed import seed_base

# Import per registrare le tabelle Auth nel metadata
from backend.auth_models import Utente  # noqa: F401
from backend.auth_service import autentica, crea_utente, get_utente_by_id
from backend.auth_security import create_access_token, get_subject

# OAuth2 Bearer (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(title="Studio Medico API", version="1.0.0")



# Startup

@app.on_event("startup")
def startup() -> None:
    # Crea tabelle (incluse Utente) e seed base (idempotente)
    init_db()
    seed_base()



# Schemi Auth

class RegisterIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    username: str
    is_active: bool



# Schemi Domain

class PazienteCreateIn(BaseModel):
    nome: str
    cognome: str
    email: str | None = None
    telefono: str | None = None


class AppuntamentoCreateIn(BaseModel):
    # prenotazione “interna” (paziente esistente)
    paziente_id: str
    medico_id: str
    tipo_visita_id: int
    sala_id: int
    start: datetime
    note: str | None = None
    inserisci_waitlist_se_pieno: bool = True


class PrenotazionePubblicaIn(BaseModel):
    # prenotazione “pubblica” (crea paziente al volo)
    medico_id: str
    tipo_visita_id: int
    sala_id: int
    start: datetime
    note: str | None = None
    inserisci_waitlist_se_pieno: bool = True

    # dati paziente “pubblico”
    nome: str = Field(..., min_length=1)
    cognome: str = Field(..., min_length=1)
    email: str | None = None
    telefono: str | None = None



# Dipendenze auth

def get_current_user(token: str = Depends(oauth2_scheme)) -> Utente:
    # protezione extra: elimina spazi / virgolette accidentali
    token = token.strip().strip('"').strip("'")

    user_id = get_subject(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")

    u = get_utente_by_id(user_id)
    if not u or not u.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utente non valido")
    return u



# AUTH endpoints

@app.post("/api/auth/register", response_model=dict)
def register(payload: RegisterIn) -> dict[str, Any]:
    try:
        user_id = crea_utente(payload.username, payload.password)
        return {"ok": True, "user_id": user_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenOut:
    u = autentica(form.username, form.password)
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    token = create_access_token(subject=u.id, extra={"username": u.username})
    return TokenOut(access_token=token)


@app.get("/api/me", response_model=MeOut)
def me(user: Utente = Depends(get_current_user)) -> MeOut:
    return MeOut(id=user.id, username=user.username, is_active=user.is_active)


@app.get("/api/protected/ping")
def protected_ping(user: Utente = Depends(get_current_user)) -> dict[str, Any]:
    return {"ok": True, "message": f"Ciao {user.username}, accesso autorizzato."}



# PUBLIC endpoints (no JWT)

@app.get("/api/medici")
def api_medici() -> list[dict]:
    return lista_medici_flat()


@app.get("/api/sale")
def api_sale() -> list[dict]:
    return lista_sale_flat()


@app.get("/api/tipi-visita")
def api_tipi_visita() -> list[dict]:
    return lista_tipi_visita_flat()


@app.post("/api/public/prenotazioni")
def prenotazione_pubblica(payload: PrenotazionePubblicaIn) -> dict[str, Any]:
    """
    Prenotazione senza login:
    - crea un paziente al volo
    - prova a prenotare l’appuntamento
    """
    paziente_id = crea_paziente(
        payload.nome,
        payload.cognome,
        payload.email,
        payload.telefono,
    )

    esito = prenota_appuntamento(
        paziente_id=paziente_id,
        medico_id=payload.medico_id,
        tipo_visita_id=payload.tipo_visita_id,
        sala_id=payload.sala_id,
        start=payload.start,
        note=payload.note,
        inserisci_waitlist_se_pieno=payload.inserisci_waitlist_se_pieno,
    )

    return {
        "ok": bool(getattr(esito, "ok", False)),
        "messaggio": getattr(esito, "messaggio", ""),
        "appuntamento_id": getattr(esito, "appuntamento_id", None),
        "messo_in_waitlist": bool(getattr(esito, "messo_in_waitlist", False)),
        "paziente_id": paziente_id,
    }



# PROTECTED endpoints (JWT)

@app.get("/api/pazienti")
def api_pazienti(user: Utente = Depends(get_current_user)) -> list[dict]:
    return lista_pazienti_flat()


@app.post("/api/pazienti")
def api_crea_paziente(payload: PazienteCreateIn, user: Utente = Depends(get_current_user)) -> dict[str, Any]:
    pid = crea_paziente(payload.nome, payload.cognome, payload.email, payload.telefono)
    return {"ok": True, "paziente_id": pid}


@app.post("/api/appuntamenti")
def api_crea_appuntamento(payload: AppuntamentoCreateIn, user: Utente = Depends(get_current_user)) -> dict[str, Any]:
    esito = prenota_appuntamento(
        paziente_id=payload.paziente_id,
        medico_id=payload.medico_id,
        tipo_visita_id=payload.tipo_visita_id,
        sala_id=payload.sala_id,
        start=payload.start,
        note=payload.note,
        inserisci_waitlist_se_pieno=payload.inserisci_waitlist_se_pieno,
    )

    return {
        "ok": bool(getattr(esito, "ok", False)),
        "messaggio": getattr(esito, "messaggio", ""),
        "appuntamento_id": getattr(esito, "appuntamento_id", None),
        "messo_in_waitlist": bool(getattr(esito, "messo_in_waitlist", False)),
    }


@app.get("/api/agenda")
def api_agenda(
    medico_id: str = Query(...),
    giorno: date = Query(...),
    user: Utente = Depends(get_current_user),
) -> list[dict]:
    return agenda_giornaliera_flat(medico_id, giorno)


@app.get("/api/notifiche/pendenti")
def api_notifiche_pendenti(limit: int = 200, user=Depends(get_current_user)) -> list[dict]:
    return notifiche_pendenti_flat(limit=limit)