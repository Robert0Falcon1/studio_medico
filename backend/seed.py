from __future__ import annotations

from sqlalchemy import select

from .db import db_session
from .models import AttrezzaturaSala, Medico, SalaVisita, TipoVisita


def seed_base() -> None:
    """
    Popola dati minimi (idempotente):
    - medici
    - sale
    - tipi visita
    - attrezzature sale
    """
    with db_session() as s:
        # Tipi visita
        tipi = [
            ("Visita Generale", 30),
            ("Controllo", 20),
            ("Visita Specialistica", 45),
        ]
        for nome, durata in tipi:
            if s.execute(select(TipoVisita).where(TipoVisita.nome == nome)).scalar_one_or_none() is None:
                s.add(TipoVisita(nome=nome, durata_minuti=durata))

        # Sale
        sale = ["Sala 1", "Sala 2"]
        for nome in sale:
            if s.execute(select(SalaVisita).where(SalaVisita.nome == nome)).scalar_one_or_none() is None:
                s.add(SalaVisita(nome=nome, attiva=True))

        # Medici
        medici = [
            ("Mario", "Rossi", "Medicina Generale", "m.rossi@studio.local"),
            ("Laura", "Bianchi", "Cardiologia", "l.bianchi@studio.local"),
        ]
        for nome, cognome, spec, email in medici:
            exists = s.execute(
                select(Medico).where(Medico.nome == nome, Medico.cognome == cognome, Medico.specializzazione == spec)
            ).scalar_one_or_none()
            if exists is None:
                s.add(Medico(nome=nome, cognome=cognome, specializzazione=spec, email=email))

        s.flush()

        # Attrezzature (semplice esempio)
        sala1 = s.execute(select(SalaVisita).where(SalaVisita.nome == "Sala 1")).scalar_one()
        sala2 = s.execute(select(SalaVisita).where(SalaVisita.nome == "Sala 2")).scalar_one()

        def add_tool(sala_id: int, tool: str) -> None:
            if s.execute(
                select(AttrezzaturaSala).where(AttrezzaturaSala.sala_id == sala_id, AttrezzaturaSala.nome == tool)
            ).scalar_one_or_none() is None:
                s.add(AttrezzaturaSala(sala_id=sala_id, nome=tool))

        add_tool(sala1.id, "ECG")
        add_tool(sala2.id, "Ecoscopio")
