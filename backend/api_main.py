from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.services import init_db
from backend.seed import seed_base

from backend.auth_models import Utente  # importa per registrare tabella
from backend.auth_service import autentica, crea_utente, get_utente_by_id
from backend.auth_security import get_subject, create_access_token

# Per estrarre token: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(title="Studio Medico API", version="1.0.0")


# Startup
@app.on_event("startup")
def startup() -> None:
    # Crea tabelle (incluse Utente)
    init_db()
    # Dati base (medici/sale/tipi visita)
    seed_base()


# Schemi
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


# Dipendenze auth
def get_current_user(token: str = Depends(oauth2_scheme)) -> Utente:
    token = token.strip().strip('"').strip("'")  # <-- aggiungi questa riga

    user_id = get_subject(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")

    u = get_utente_by_id(user_id)
    if not u or not u.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utente non valido")
    return u

# Auth endpoints
@app.post("/api/auth/register", response_model=dict)
def register(payload: RegisterIn) -> dict:
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


# Esempio endpoint protetto (test)
@app.get("/api/protected/ping")
def protected_ping(user: Utente = Depends(get_current_user)) -> dict:
    return {"ok": True, "message": f"Ciao {user.username}, accesso autorizzato."}
