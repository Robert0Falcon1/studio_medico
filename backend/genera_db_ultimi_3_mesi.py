from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, select

from backend.db import db_session
from backend.models import (
    Appuntamento,
    AttrezzaturaSala,
    CartellaClinica,
    ContattoEmergenza,
    DisponibilitaMedico,
    Medico,
    Paziente,
    SalaVisita,
    StatoAppuntamento,
    TipoVisita,
)
from backend.services import init_db


# =========================
# Config generazione
# =========================
RANDOM_SEED = 42

PAZIENTI_COUNT = 140
MEDICI = [
    ("Mario", "Rossi", "Medicina Generale"),
    ("Laura", "Bianchi", "Cardiologia"),
    ("Giulia", "Verdi", "Ortopedia"),
    ("Paolo", "Neri", "Dermatologia"),
    ("Francesca", "Gallo", "Ginecologia"),
    ("Luca", "Conti", "Oculistica"),
]

TIPI_VISITA = [
    ("Visita Generale", 30),
    ("Controllo", 20),
    ("Visita Specialistica", 45),
    ("ECG", 25),
    ("Ecografia", 35),
    ("Visita Dermatologica", 30),
]

SALE = [
    ("Sala 1", ["ECG", "Holter", "Misuratore pressione"]),
    ("Sala 2", ["Ecoscopio", "Lettino visita", "Bilancia"]),
    ("Sala 3", ["Lampada scialitica", "Kit medicazioni", "Lettino visita"]),
]

# Distribuzione affluenza per giorno della settimana (0=lun...6=dom)
# Valori più alti -> più appuntamenti
AFFLUENZA_FATTORE = {
    0: 1.15,  # lun
    1: 1.05,  # mar
    2: 1.00,  # mer
    3: 1.05,  # gio
    4: 1.10,  # ven
    5: 0.55,  # sab
    6: 0.00,  # dom (chiuso)
}


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime


def _random_codice_fiscale() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    nums = "0123456789"
    return "".join(random.choice(letters) for _ in range(6)) + "".join(random.choice(nums) for _ in range(10))


def _random_phone() -> str:
    return f"3{random.randint(20, 99)}{random.randint(1000000, 9999999)}"


def _random_email(nome: str, cognome: str) -> str:
    domains = ["mail.it", "gmail.com", "outlook.com", "icloud.com"]
    return f"{nome.lower()}.{cognome.lower()}{random.randint(1, 99)}@{random.choice(domains)}"


def _make_slots_for_day(day: date, start_hm: str, end_hm: str, step_minutes: int = 5) -> list[datetime]:
    """Genera timestamps ogni X minuti tra start e end (start incluso, end escluso)."""
    sh, sm = map(int, start_hm.split(":"))
    eh, em = map(int, end_hm.split(":"))
    start_dt = datetime.combine(day, time(sh, sm))
    end_dt = datetime.combine(day, time(eh, em))

    out: list[datetime] = []
    cur = start_dt
    while cur < end_dt:
        out.append(cur)
        cur += timedelta(minutes=step_minutes)
    return out


def reset_db() -> None:
    """Cancella i dati principali (mantiene lo schema)."""
    with db_session() as s:
        # Ordine importante per vincoli FK
        s.execute(delete(Appuntamento))
        s.execute(delete(DisponibilitaMedico))
        s.execute(delete(AttrezzaturaSala))
        s.execute(delete(SalaVisita))
        s.execute(delete(TipoVisita))
        s.execute(delete(ContattoEmergenza))
        s.execute(delete(CartellaClinica))
        s.execute(delete(Paziente))
        s.execute(delete(Medico))


def seed_struttura() -> None:
    """Crea medici, disponibilità, tipi visita, sale e attrezzature."""
    with db_session() as s:
        # Tipi visita
        for nome, durata in TIPI_VISITA:
            exists = s.execute(select(TipoVisita).where(TipoVisita.nome == nome)).scalar_one_or_none()
            if not exists:
                s.add(TipoVisita(nome=nome, durata_minuti=durata))

        # Sale + attrezzature
        for sala_nome, tools in SALE:
            sala = s.execute(select(SalaVisita).where(SalaVisita.nome == sala_nome)).scalar_one_or_none()
            if not sala:
                sala = SalaVisita(nome=sala_nome, attiva=True)
                s.add(sala)
                s.flush()

            for tool in tools:
                tool_exists = s.execute(
                    select(AttrezzaturaSala).where(
                        AttrezzaturaSala.sala_id == sala.id,
                        AttrezzaturaSala.nome == tool,
                    )
                ).scalar_one_or_none()
                if not tool_exists:
                    s.add(AttrezzaturaSala(sala_id=sala.id, nome=tool))

        # Medici + disponibilità settimanale
        for nome, cognome, spec in MEDICI:
            m = s.execute(
                select(Medico).where(Medico.nome == nome, Medico.cognome == cognome, Medico.specializzazione == spec)
            ).scalar_one_or_none()

            if not m:
                m = Medico(
                    nome=nome,
                    cognome=cognome,
                    specializzazione=spec,
                    email=_random_email(nome, cognome),
                    telefono=_random_phone(),
                    attivo=True,
                )
                s.add(m)
                s.flush()

            # disponibilità standard:
            # lun-ven 09-13 e 14-18
            # sab per alcuni medici 09-13
            s.execute(delete(DisponibilitaMedico).where(DisponibilitaMedico.medico_id == m.id))

            for dow in range(0, 5):
                s.add(DisponibilitaMedico(medico_id=m.id, giorno_settimana=dow, ora_inizio="09:00", ora_fine="13:00"))
                s.add(DisponibilitaMedico(medico_id=m.id, giorno_settimana=dow, ora_inizio="14:00", ora_fine="18:00"))

            if spec in {"Medicina Generale", "Cardiologia"}:
                s.add(DisponibilitaMedico(medico_id=m.id, giorno_settimana=5, ora_inizio="09:00", ora_fine="13:00"))


def seed_pazienti() -> None:
    nomi = [
        "Roberto", "Marco", "Luca", "Paolo", "Giovanni", "Andrea", "Matteo", "Simone",
        "Sara", "Giulia", "Francesca", "Elena", "Chiara", "Martina", "Laura", "Valentina",
    ]
    cognomi = [
        "Falconi", "Rossi", "Bianchi", "Verdi", "Neri", "Gallo", "Conti", "Romano",
        "Greco", "Costa", "Fontana", "Moretti", "Barbieri", "Lombardi", "Mariani",
    ]

    with db_session() as s:
        for _ in range(PAZIENTI_COUNT):
            nome = random.choice(nomi)
            cognome = random.choice(cognomi)
            p = Paziente(
                nome=nome,
                cognome=cognome,
                data_nascita=date.today() - timedelta(days=random.randint(18 * 365, 85 * 365)),
                telefono=_random_phone(),
                email=_random_email(nome, cognome),
                codice_fiscale=_random_codice_fiscale(),
            )
            s.add(p)
            s.flush()

            # contatto emergenza (circa 55% dei pazienti)
            if random.random() < 0.55:
                s.add(
                    ContattoEmergenza(
                        paziente_id=p.id,
                        nome=random.choice(nomi),
                        telefono=_random_phone(),
                        relazione=random.choice(["Coniuge", "Genitore", "Figlio/a", "Fratello/Sorella", "Partner"]),
                    )
                )

            # cartella clinica base
            s.add(CartellaClinica(paziente_id=p.id, note_generali=None))


def _pick_tipo_visita(tipi: list[TipoVisita], medico: Medico) -> TipoVisita:
    # Scelta “realistica” in base a specializzazione
    name_to_weight = {}
    for tv in tipi:
        w = 1.0
        if medico.specializzazione == "Medicina Generale":
            w = 4.0 if tv.nome in {"Visita Generale", "Controllo"} else 0.6
        elif medico.specializzazione == "Cardiologia":
            w = 3.0 if tv.nome in {"Visita Specialistica", "ECG", "Controllo"} else 0.5
        elif medico.specializzazione == "Dermatologia":
            w = 3.0 if tv.nome in {"Visita Dermatologica", "Controllo"} else 0.5
        else:
            w = 2.2 if tv.nome in {"Visita Specialistica", "Controllo"} else 0.7
        name_to_weight[tv.id] = w

    # weighted random
    ids = [tv.id for tv in tipi]
    weights = [name_to_weight[tv.id] for tv in tipi]
    chosen_id = random.choices(ids, weights=weights, k=1)[0]
    return next(tv for tv in tipi if tv.id == chosen_id)


def _stato_per_data(app_date: date) -> StatoAppuntamento:
    """Stato coerente con il fatto che stiamo generando per gli ultimi 90 giorni."""
    today = date.today()
    delta = (today - app_date).days

    if delta >= 2:
        # appuntamenti passati: quasi tutti completati, alcuni annullati
        return StatoAppuntamento.COMPLETATO if random.random() < 0.92 else StatoAppuntamento.ANNULLATO
    if delta in {0, 1}:
        # oggi / ieri: mix
        r = random.random()
        if r < 0.65:
            return StatoAppuntamento.COMPLETATO
        if r < 0.85:
            return StatoAppuntamento.CONFERMATO
        return StatoAppuntamento.ANNULLATO
    # (in teoria non dovremmo avere futuro, ma per sicurezza)
    return StatoAppuntamento.CONFERMATO


def genera_appuntamenti_ultimi_90_giorni() -> None:
    start_day = date.today() - timedelta(days=90)
    end_day = date.today()

    with db_session() as s:
        medici = list(s.scalars(select(Medico).where(Medico.attivo.is_(True))).all())
        pazienti = list(s.scalars(select(Paziente)).all())
        sale = list(s.scalars(select(SalaVisita).where(SalaVisita.attiva.is_(True))).all())
        tipi = list(s.scalars(select(TipoVisita)).all())

        if not medici or not pazienti or not sale or not tipi:
            raise RuntimeError("Mancano dati base (medici/pazienti/sale/tipi visita). Esegui seed_struttura + seed_pazienti.")

        # Indicatore occupazione media (regolabile)
        base_occupancy = 0.62

        # set per evitare doppioni paziente nello stesso giorno con lo stesso medico (realismo)
        seen_patient_day: set[tuple[str, str, date]] = set()

        day = start_day
        while day <= end_day:
            dow = day.weekday()
            fattore = AFFLUENZA_FATTORE.get(dow, 1.0)
            if fattore <= 0:
                day += timedelta(days=1)
                continue

            # variazione casuale giorno per giorno
            occupancy = min(0.92, max(0.25, base_occupancy * fattore + random.uniform(-0.08, 0.10)))

            for medico in medici:
                # disponibilità del medico per quel giorno
                disps = s.execute(
                    select(DisponibilitaMedico).where(
                        DisponibilitaMedico.medico_id == medico.id,
                        DisponibilitaMedico.giorno_settimana == dow,
                    )
                ).scalars().all()

                if not disps:
                    continue

                # costruiamo una lista di start possibili ogni 5 minuti (poi filtreremo per durata)
                possible_starts: list[datetime] = []
                for d in disps:
                    possible_starts.extend(_make_slots_for_day(day, d.ora_inizio, d.ora_fine, step_minutes=5))

                random.shuffle(possible_starts)

                # target appuntamenti per quel medico/giorno (realistico: 6-18)
                # dipende dalla presenza del sabato e specializzazione
                cap_base = 14 if dow < 5 else 7
                cap = int(cap_base * fattore + random.randint(-2, 2))
                cap = max(3, min(cap, 20))

                created = 0
                timeline: list[Slot] = []  # per evitare sovrapposizioni del medico (semplificazione)

                for start_dt in possible_starts:
                    if created >= cap:
                        break
                    if random.random() > occupancy:
                        continue

                    tv = _pick_tipo_visita(tipi, medico)
                    end_dt = start_dt + timedelta(minutes=tv.durata_minuti)

                    # rientro nella fascia?
                    # (assumo che possible_starts sia dentro, ma fine può sforare)
                    ok_window = any(
                        datetime.combine(day, time(*map(int, d.ora_inizio.split(":")))) <= start_dt
                        and end_dt <= datetime.combine(day, time(*map(int, d.ora_fine.split(":"))))
                        for d in disps
                    )
                    if not ok_window:
                        continue

                    # no overlap con altri slot del medico
                    if any(sl.start < end_dt and sl.end > start_dt for sl in timeline):
                        continue

                    paziente = random.choice(pazienti)
                    key = (paziente.id, medico.id, day)
                    if key in seen_patient_day and random.random() < 0.8:
                        continue

                    sala = random.choice(sale)

                    stato = _stato_per_data(day)

                    app = Appuntamento(
                        paziente_id=paziente.id,
                        medico_id=medico.id,
                        tipo_visita_id=tv.id,
                        sala_id=sala.id,
                        inizio=start_dt,
                        fine=end_dt,
                        stato=stato,
                        note=random.choice(
                            [
                                None,
                                "Paziente con sintomi riferiti da monitorare.",
                                "Controllo periodico.",
                                "Richiesta approfondimento.",
                                "Follow-up terapia.",
                            ]
                        ),
                    )
                    s.add(app)

                    timeline.append(Slot(start=start_dt, end=end_dt))
                    seen_patient_day.add(key)
                    created += 1

            day += timedelta(days=1)


def main(reset: bool = True) -> None:
    random.seed(RANDOM_SEED)

    init_db()

    if reset:
        reset_db()

    seed_struttura()
    seed_pazienti()
    genera_appuntamenti_ultimi_90_giorni()

    print("OK: database popolato con dati realistici degli ultimi 90 giorni.")


if __name__ == "__main__":
    # default: reset True
    main(reset=True)
