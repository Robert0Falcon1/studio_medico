from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class StatoAppuntamento(enum.Enum):
    PROGRAMMATO = "PROGRAMMATO"
    CONFERMATO = "CONFERMATO"
    ANNULLATO = "ANNULLATO"
    COMPLETATO = "COMPLETATO"


class TipoNotifica(enum.Enum):
    PROMEMORIA = "PROMEMORIA"
    CONFERMA = "CONFERMA"
    ANNULLAMENTO = "ANNULLAMENTO"
    SPOSTAMENTO = "SPOSTAMENTO"
    WAITLIST_PROMOSSA = "WAITLIST_PROMOSSA"


class Medico(Base):
    __tablename__ = "medici"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    cognome: Mapped[str] = mapped_column(String(80), nullable=False)
    specializzazione: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=True)
    email: Mapped[str] = mapped_column(String(120), nullable=True)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    appuntamenti: Mapped[list["Appuntamento"]] = relationship(back_populates="medico", cascade="all, delete-orphan")
    waitlist: Mapped[list["ListaAttesa"]] = relationship(back_populates="medico", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Medico({self.nome} {self.cognome}, {self.specializzazione})"


class Paziente(Base):
    __tablename__ = "pazienti"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    cognome: Mapped[str] = mapped_column(String(80), nullable=False)
    data_nascita: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(16), nullable=True, unique=True)

    contatti_emergenza: Mapped[list["ContattoEmergenza"]] = relationship(
        back_populates="paziente", cascade="all, delete-orphan"
    )
    cartelle: Mapped[list["CartellaClinica"]] = relationship(back_populates="paziente", cascade="all, delete-orphan")
    appuntamenti: Mapped[list["Appuntamento"]] = relationship(back_populates="paziente", cascade="all, delete-orphan")
    waitlist: Mapped[list["ListaAttesa"]] = relationship(back_populates="paziente", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Paziente({self.nome} {self.cognome})"


class ContattoEmergenza(Base):
    __tablename__ = "contatti_emergenza"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paziente_id: Mapped[str] = mapped_column(ForeignKey("pazienti.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    relazione: Mapped[str | None] = mapped_column(String(80), nullable=True)

    paziente: Mapped["Paziente"] = relationship(back_populates="contatti_emergenza")


class CartellaClinica(Base):
    __tablename__ = "cartelle_cliniche"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paziente_id: Mapped[str] = mapped_column(ForeignKey("pazienti.id"), nullable=False)
    creata_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    note_generali: Mapped[str | None] = mapped_column(Text, nullable=True)

    paziente: Mapped["Paziente"] = relationship(back_populates="cartelle")


class TipoVisita(Base):
    __tablename__ = "tipi_visita"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    durata_minuti: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    appuntamenti: Mapped[list["Appuntamento"]] = relationship(back_populates="tipo_visita")
    waitlist: Mapped[list["ListaAttesa"]] = relationship(back_populates="tipo_visita")


class SalaVisita(Base):
    __tablename__ = "sale_visita"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    attiva: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    attrezzature: Mapped[list["AttrezzaturaSala"]] = relationship(
        back_populates="sala", cascade="all, delete-orphan"
    )
    appuntamenti: Mapped[list["Appuntamento"]] = relationship(back_populates="sala")


class AttrezzaturaSala(Base):
    __tablename__ = "attrezzature_sala"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("sale_visita.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)

    sala: Mapped["SalaVisita"] = relationship(back_populates="attrezzature")


class Appuntamento(Base):
    __tablename__ = "appuntamenti"
    __table_args__ = (
        # Evita doppie prenotazioni identiche (stesso medico + stessa sala + stesso orario)
        UniqueConstraint("medico_id", "inizio", name="uq_app_medico_inizio"),
        UniqueConstraint("sala_id", "inizio", name="uq_app_sala_inizio"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    paziente_id: Mapped[str] = mapped_column(ForeignKey("pazienti.id"), nullable=False)
    medico_id: Mapped[str] = mapped_column(ForeignKey("medici.id"), nullable=False)
    tipo_visita_id: Mapped[int] = mapped_column(ForeignKey("tipi_visita.id"), nullable=False)
    sala_id: Mapped[int] = mapped_column(ForeignKey("sale_visita.id"), nullable=False)

    inizio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fine: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    stato: Mapped[StatoAppuntamento] = mapped_column(
        Enum(StatoAppuntamento), default=StatoAppuntamento.PROGRAMMATO, nullable=False
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    paziente: Mapped["Paziente"] = relationship(back_populates="appuntamenti")
    medico: Mapped["Medico"] = relationship(back_populates="appuntamenti")
    tipo_visita: Mapped["TipoVisita"] = relationship(back_populates="appuntamenti")
    sala: Mapped["SalaVisita"] = relationship(back_populates="appuntamenti")
    notifiche: Mapped[list["Notifica"]] = relationship(back_populates="appuntamento", cascade="all, delete-orphan")


class ListaAttesa(Base):
    __tablename__ = "lista_attesa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paziente_id: Mapped[str] = mapped_column(ForeignKey("pazienti.id"), nullable=False)
    medico_id: Mapped[str] = mapped_column(ForeignKey("medici.id"), nullable=False)
    tipo_visita_id: Mapped[int] = mapped_column(ForeignKey("tipi_visita.id"), nullable=False)

    priorita: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1=alta, 10=bassa
    inserita_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    paziente: Mapped["Paziente"] = relationship(back_populates="waitlist")
    medico: Mapped["Medico"] = relationship(back_populates="waitlist")
    tipo_visita: Mapped["TipoVisita"] = relationship(back_populates="waitlist")


class Notifica(Base):
    __tablename__ = "notifiche"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo: Mapped[TipoNotifica] = mapped_column(Enum(TipoNotifica), nullable=False)
    messaggio: Mapped[str] = mapped_column(Text, nullable=False)

    creata_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    inviata_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # opzionale: notifica riferita a un appuntamento
    appuntamento_id: Mapped[str | None] = mapped_column(ForeignKey("appuntamenti.id"), nullable=True)

    appuntamento: Mapped["Appuntamento"] = relationship(back_populates="notifiche")
