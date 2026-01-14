from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import and_, select

from .db import Base, db_session, engine
from .models import (
    Appuntamento,
    ListaAttesa,
    Medico,
    Notifica,
    Paziente,
    SalaVisita,
    StatoAppuntamento,
    TipoNotifica,
    TipoVisita,
)


# =========================
# Bootstrap DB
# =========================
def init_db() -> None:
    """Crea le tabelle se non esistono."""
    Base.metadata.create_all(bind=engine)


# =========================
# Helper / DTO
# =========================
@dataclass(frozen=True)
class EsitoPrenotazione:
    ok: bool
    appuntamento_id: str | None
    messo_in_waitlist: bool
    messaggio: str


# =========================
# CRUD base
# =========================
def crea_paziente(nome: str, cognome: str, email: str | None = None, telefono: str | None = None) -> str:
    with db_session() as s:
        p = Paziente(nome=nome.strip(), cognome=cognome.strip(), email=email, telefono=telefono)
        s.add(p)
        s.flush()
        return p.id


def crea_medico(nome: str, cognome: str, specializzazione: str, email: str | None = None) -> str:
    with db_session() as s:
        m = Medico(nome=nome.strip(), cognome=cognome.strip(), specializzazione=specializzazione.strip(), email=email)
        s.add(m)
        s.flush()
        return m.id


# =========================
# Query utili
# =========================
def lista_medici_attivi() -> list[Medico]:
    with db_session() as s:
        return list(s.scalars(select(Medico).where(Medico.attivo.is_(True)).order_by(Medico.cognome, Medico.nome)))


def lista_pazienti() -> list[Paziente]:
    with db_session() as s:
        return list(s.scalars(select(Paziente).order_by(Paziente.cognome, Paziente.nome)))


def lista_sale_attive() -> list[SalaVisita]:
    with db_session() as s:
        return list(s.scalars(select(SalaVisita).where(SalaVisita.attiva.is_(True)).order_by(SalaVisita.nome)))


def lista_tipi_visita() -> list[TipoVisita]:
    with db_session() as s:
        return list(s.scalars(select(TipoVisita).order_by(TipoVisita.nome)))


def agenda_giornaliera(medico_id: str, giorno: date) -> list[Appuntamento]:
    inizio = datetime.combine(giorno, datetime.min.time())
    fine = inizio + timedelta(days=1)

    with db_session() as s:
        q = (
            select(Appuntamento)
            .where(
                and_(
                    Appuntamento.medico_id == medico_id,
                    Appuntamento.inizio >= inizio,
                    Appuntamento.inizio < fine,
                    Appuntamento.stato != StatoAppuntamento.ANNULLATO,
                )
            )
            .order_by(Appuntamento.inizio.asc())
        )
        return list(s.scalars(q))

def agenda_giornaliera_flat(medico_id: str, giorno: date) -> list[dict]:
    """
    Versione 'flat' (safe per Streamlit): ritorna dict serializzabili.
    Evita lazy-load e DetachedInstanceError.
    """
    start_day = datetime.combine(giorno, datetime.min.time())
    end_day = start_day + timedelta(days=1)

    with db_session() as s:
        q = (
            select(
                Appuntamento.inizio,
                Appuntamento.fine,
                Appuntamento.stato,
                Appuntamento.note,
                SalaVisita.nome.label("sala_nome"),
                TipoVisita.nome.label("tipo_nome"),
            )
            .join(SalaVisita, SalaVisita.id == Appuntamento.sala_id)
            .join(TipoVisita, TipoVisita.id == Appuntamento.tipo_visita_id)
            .where(
                and_(
                    Appuntamento.medico_id == medico_id,
                    Appuntamento.inizio >= start_day,
                    Appuntamento.inizio < end_day,
                    Appuntamento.stato != StatoAppuntamento.ANNULLATO,
                )
            )
            .order_by(Appuntamento.inizio.asc())
        )

        rows = s.execute(q).all()
        return [
            {
                "inizio": r.inizio.strftime("%H:%M"),
                "fine": r.fine.strftime("%H:%M"),
                "stato": r.stato.value,
                "note": r.note,
                "sala": r.sala_nome,
                "tipo_visita": r.tipo_nome,
            }
            for r in rows
        ]
        
# =========================
# Disponibilità
# =========================
def _slot_libero(s, medico_id: str, sala_id: int, start: datetime, end: datetime) -> bool:
    """
    Regola semplice: nessuna sovrapposizione con appuntamenti non annullati.
    (Versione realistica: verifiche turni medico, buffer, ferie, ecc.)
    """
    overlap = (
        select(Appuntamento.id)
        .where(
            and_(
                Appuntamento.stato != StatoAppuntamento.ANNULLATO,
                # sovrapposizione [start,end)
                Appuntamento.inizio < end,
                Appuntamento.fine > start,
                # vincoli medico o sala
                (Appuntamento.medico_id == medico_id) | (Appuntamento.sala_id == sala_id),
            )
        )
        .limit(1)
    )
    return s.execute(overlap).first() is None


# =========================
# Prenotazione (use case core)
# =========================
def prenota_appuntamento(
    paziente_id: str,
    medico_id: str,
    tipo_visita_id: int,
    sala_id: int,
    start: datetime,
    note: str | None = None,
    inserisci_waitlist_se_pieno: bool = True,
) -> EsitoPrenotazione:
    """
    Use case: Prenotare appuntamento.
    - Calcola la durata dal tipo visita
    - Verifica disponibilità medico+sala
    - Se pieno: opzionale inserimento in lista d'attesa
    - Genera notifiche (conferma o waitlist)
    """
    with db_session() as s:
        tv = s.get(TipoVisita, tipo_visita_id)
        if not tv:
            return EsitoPrenotazione(False, None, False, "Tipo visita non valido.")

        end = start + timedelta(minutes=tv.durata_minuti)

        if not _slot_libero(s, medico_id=medico_id, sala_id=sala_id, start=start, end=end):
            if not inserisci_waitlist_se_pieno:
                return EsitoPrenotazione(False, None, False, "Slot non disponibile (medico o sala occupati).")

            wl = ListaAttesa(
                paziente_id=paziente_id,
                medico_id=medico_id,
                tipo_visita_id=tipo_visita_id,
                priorita=5,
                note=f"Richiesta per {start.isoformat()} (slot non disponibile).",
            )
            s.add(wl)

            s.add(
                Notifica(
                    tipo=TipoNotifica.PROMEMORIA,
                    messaggio="Sei stato inserito in lista d'attesa: ti avviseremo quando si libera uno slot.",
                    appuntamento_id=None,
                )
            )
            return EsitoPrenotazione(True, None, True, "Slot pieno: paziente inserito in lista d'attesa.")

        app = Appuntamento(
            paziente_id=paziente_id,
            medico_id=medico_id,
            tipo_visita_id=tipo_visita_id,
            sala_id=sala_id,
            inizio=start,
            fine=end,
            stato=StatoAppuntamento.CONFERMATO,
            note=note,
        )
        s.add(app)
        s.flush()

        s.add(
            Notifica(
                tipo=TipoNotifica.CONFERMA,
                messaggio=f"Appuntamento confermato per {start.strftime('%d/%m/%Y %H:%M')}.",
                appuntamento_id=app.id,
            )
        )

        return EsitoPrenotazione(True, app.id, False, "Appuntamento confermato.")


def annulla_appuntamento(appuntamento_id: str, motivo: str | None = None) -> bool:
    """
    Use case: Annullare appuntamento.
    - imposta stato ANNULLATO
    - genera notifica annullamento
    - prova a promuovere un paziente dalla lista d'attesa (se disponibile)
    """
    with db_session() as s:
        app = s.get(Appuntamento, appuntamento_id)
        if not app or app.stato == StatoAppuntamento.ANNULLATO:
            return False

        app.stato = StatoAppuntamento.ANNULLATO

        s.add(
            Notifica(
                tipo=TipoNotifica.ANNULLAMENTO,
                messaggio=f"Appuntamento annullato. Motivo: {motivo or 'n/d'}",
                appuntamento_id=app.id,
            )
        )

        _promuovi_da_waitlist(s, medico_id=app.medico_id, tipo_visita_id=app.tipo_visita_id, start=app.inizio, sala_id=app.sala_id)
        return True


def _promuovi_da_waitlist(s, medico_id: str, tipo_visita_id: int, start: datetime, sala_id: int) -> None:
    """
    Quando si libera uno slot, prova a prenotare automaticamente il primo in lista d'attesa
    (priorità più alta = numero più basso, a parità: più vecchio).
    """
    tv = s.get(TipoVisita, tipo_visita_id)
    if not tv:
        return

    end = start + timedelta(minutes=tv.durata_minuti)
    if not _slot_libero(s, medico_id=medico_id, sala_id=sala_id, start=start, end=end):
        return

    q = (
        select(ListaAttesa)
        .where(and_(ListaAttesa.medico_id == medico_id, ListaAttesa.tipo_visita_id == tipo_visita_id))
        .order_by(ListaAttesa.priorita.asc(), ListaAttesa.inserita_il.asc())
        .limit(1)
    )
    wl = s.scalars(q).first()
    if not wl:
        return

    app = Appuntamento(
        paziente_id=wl.paziente_id,
        medico_id=medico_id,
        tipo_visita_id=tipo_visita_id,
        sala_id=sala_id,
        inizio=start,
        fine=end,
        stato=StatoAppuntamento.CONFERMATO,
        note="Generato automaticamente da lista d'attesa.",
    )
    s.add(app)
    s.flush()

    s.add(
        Notifica(
            tipo=TipoNotifica.WAITLIST_PROMOSSA,
            messaggio=f"Si è liberato uno slot: appuntamento assegnato per {start.strftime('%d/%m/%Y %H:%M')}.",
            appuntamento_id=app.id,
        )
    )

    # rimuove la richiesta dalla waitlist
    s.delete(wl)


# =========================
# Notifiche (simulazione sistema esterno)
# =========================
def estrai_notifiche_pendenti(limit: int = 50) -> list[Notifica]:
    """Ritorna notifiche non ancora 'inviate' (inviata_il è NULL)."""
    with db_session() as s:
        q = select(Notifica).where(Notifica.inviata_il.is_(None)).order_by(Notifica.creata_il.asc()).limit(limit)
        return list(s.scalars(q))


def marca_notifica_inviata(notifica_id: int) -> bool:
    with db_session() as s:
        n = s.get(Notifica, notifica_id)
        if not n or n.inviata_il is not None:
            return False
        n.inviata_il = datetime.utcnow()
        return True

from sqlalchemy import select

def lista_medici_flat() -> list[dict]:
    with db_session() as s:
        rows = s.execute(
            select(Medico.id, Medico.nome, Medico.cognome, Medico.specializzazione)
            .where(Medico.attivo.is_(True))
            .order_by(Medico.cognome, Medico.nome)
        ).all()
        return [
            {"id": r.id, "nome": r.nome, "cognome": r.cognome, "specializzazione": r.specializzazione}
            for r in rows
        ]


def lista_pazienti_flat() -> list[dict]:
    with db_session() as s:
        rows = s.execute(
            select(Paziente.id, Paziente.nome, Paziente.cognome, Paziente.email)
            .order_by(Paziente.cognome, Paziente.nome)
        ).all()
        return [
            {"id": r.id, "nome": r.nome, "cognome": r.cognome, "email": r.email}
            for r in rows
        ]


def lista_sale_flat() -> list[dict]:
    with db_session() as s:
        rows = s.execute(
            select(SalaVisita.id, SalaVisita.nome)
            .where(SalaVisita.attiva.is_(True))
            .order_by(SalaVisita.nome)
        ).all()
        return [{"id": r.id, "nome": r.nome} for r in rows]


def lista_tipi_visita_flat() -> list[dict]:
    with db_session() as s:
        rows = s.execute(
            select(TipoVisita.id, TipoVisita.nome, TipoVisita.durata_minuti)
            .order_by(TipoVisita.nome)
        ).all()
        return [{"id": r.id, "nome": r.nome, "durata_minuti": r.durata_minuti} for r in rows]
