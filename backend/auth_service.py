from __future__ import annotations

from sqlalchemy import select

from backend.db import db_session
from backend.auth_models import Utente
from backend.auth_security import hash_password, verify_password


def crea_utente(username: str, password: str) -> str:
    username = username.strip().lower()
    if not username or not password:
        raise ValueError("Username e password sono obbligatori.")

    with db_session() as s:
        exists = s.execute(select(Utente).where(Utente.username == username)).scalar_one_or_none()
        if exists:
            raise ValueError("Username già registrato.")

        u = Utente(username=username, password_hash=hash_password(password), is_active=True)
        s.add(u)
        s.flush()
        return u.id


def autentica(username: str, password: str) -> Utente | None:
    username = username.strip().lower()
    with db_session() as s:
        u = s.execute(select(Utente).where(Utente.username == username)).scalar_one_or_none()
        if not u or not u.is_active:
            return None
        if not verify_password(password, u.password_hash):
            return None
        return u


def get_utente_by_id(user_id: str) -> Utente | None:
    with db_session() as s:
        return s.get(Utente, user_id)
