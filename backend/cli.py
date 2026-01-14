from __future__ import annotations

import argparse
from datetime import datetime

from backend.seed import seed_base
from backend.services import (
    crea_paziente,
    estrai_notifiche_pendenti,
    init_db,
    lista_medici_attivi,
    lista_pazienti,
    lista_sale_attive,
    lista_tipi_visita,
    marca_notifica_inviata,
    prenota_appuntamento,
    annulla_appuntamento,
)


def cmd_init(args: argparse.Namespace) -> None:
    init_db()
    seed_base()
    print("DB inizializzato e seed completato.")


def cmd_list(args: argparse.Namespace) -> None:
    if args.entity == "medici":
        for m in lista_medici_attivi():
            print(f"{m.id} | {m.cognome} {m.nome} | {m.specializzazione}")
    elif args.entity == "pazienti":
        for p in lista_pazienti():
            print(f"{p.id} | {p.cognome} {p.nome} | {p.email or '-'}")
    elif args.entity == "sale":
        for s in lista_sale_attive():
            print(f"{s.id} | {s.nome}")
    elif args.entity == "tipi_visita":
        for tv in lista_tipi_visita():
            print(f"{tv.id} | {tv.nome} ({tv.durata_minuti} min)")


def cmd_add_patient(args: argparse.Namespace) -> None:
    pid = crea_paziente(args.nome, args.cognome, args.email, args.telefono)
    print(f"Paziente creato: {pid}")


def cmd_book(args: argparse.Namespace) -> None:
    start = datetime.fromisoformat(args.start)  # formato: 2026-01-14T10:30
    esito = prenota_appuntamento(
        paziente_id=args.paziente_id,
        medico_id=args.medico_id,
        tipo_visita_id=args.tipo_visita_id,
        sala_id=args.sala_id,
        start=start,
        note=args.note,
        inserisci_waitlist_se_pieno=not args.no_waitlist,
    )
    print(esito.messaggio)
    if esito.appuntamento_id:
        print(f"Appuntamento ID: {esito.appuntamento_id}")


def cmd_cancel(args: argparse.Namespace) -> None:
    ok = annulla_appuntamento(args.appuntamento_id, motivo=args.motivo)
    print("Annullato." if ok else "Non trovato / già annullato.")


def cmd_notifications(args: argparse.Namespace) -> None:
    """
    Simula un “Sistema Notifiche” esterno:
    - legge notifiche pendenti
    - le stampa su console
    - le marca come inviate
    """
    pendenti = estrai_notifiche_pendenti(limit=args.limit)
    if not pendenti:
        print("Nessuna notifica pendente.")
        return

    for n in pendenti:
        print(f"[{n.id}] {n.tipo.value} | {n.creata_il.isoformat()} | {n.messaggio}")
        if args.mark_sent:
            marca_notifica_inviata(n.id)

    if args.mark_sent:
        print("Notifiche marcate come inviate.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio_medico_cli", description="CLI Studio Medico (simulazione sistemi esterni)")
    sub = p.add_subparsers(required=True)

    p_init = sub.add_parser("init", help="Crea DB e carica seed")
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser("list", help="Lista entità")
    p_list.add_argument("entity", choices=["medici", "pazienti", "sale", "tipi_visita"])
    p_list.set_defaults(func=cmd_list)

    p_addp = sub.add_parser("add-patient", help="Crea paziente")
    p_addp.add_argument("--nome", required=True)
    p_addp.add_argument("--cognome", required=True)
    p_addp.add_argument("--email", default=None)
    p_addp.add_argument("--telefono", default=None)
    p_addp.set_defaults(func=cmd_add_patient)

    p_book = sub.add_parser("book", help="Prenota appuntamento")
    p_book.add_argument("--paziente-id", required=True)
    p_book.add_argument("--medico-id", required=True)
    p_book.add_argument("--tipo-visita-id", type=int, required=True)
    p_book.add_argument("--sala-id", type=int, required=True)
    p_book.add_argument("--start", required=True, help="ISO datetime es: 2026-01-14T10:30")
    p_book.add_argument("--note", default=None)
    p_book.add_argument("--no-waitlist", action="store_true", help="Se slot pieno, NON inserire in lista d'attesa")
    p_book.set_defaults(func=cmd_book)

    p_cancel = sub.add_parser("cancel", help="Annulla appuntamento")
    p_cancel.add_argument("--appuntamento-id", required=True)
    p_cancel.add_argument("--motivo", default=None)
    p_cancel.set_defaults(func=cmd_cancel)

    p_not = sub.add_parser("notifications", help="Legge e invia notifiche pendenti (simulazione)")
    p_not.add_argument("--limit", type=int, default=50)
    p_not.add_argument("--mark-sent", action="store_true", help="Marca come inviate dopo averle stampate")
    p_not.set_defaults(func=cmd_notifications)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    init_db()  # garantisce tabelle
    args.func(args)


if __name__ == "__main__":
    main()
