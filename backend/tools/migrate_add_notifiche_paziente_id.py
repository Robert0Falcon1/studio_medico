from __future__ import annotations

from sqlalchemy import text

from backend.db import engine
from backend.services import init_db


def main() -> None:
    # Assicura che le tabelle esistano NEL DB corretto (quello dell'engine)
    init_db()

    print("DB:", engine.url.database)

    with engine.begin() as conn:
        # Elenco tabelle reali presenti nel DB
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")).fetchall()
        table_names = {t[0] for t in tables}
        print("Tabelle:", ", ".join(sorted(table_names)))

        if "notifiche" not in table_names:
            raise SystemExit("ERRORE: tabella 'notifiche' non trovata nel DB dell'engine (stai puntando a un DB diverso).")

        # Colonne attuali
        cols = conn.execute(text("PRAGMA table_info(notifiche);")).fetchall()
        col_names = {c[1] for c in cols}  # c[1] = name
        if "paziente_id" in col_names:
            print("OK: colonna 'paziente_id' già presente su 'notifiche'.")
            return

        # Aggiunge colonna
        conn.execute(text("ALTER TABLE notifiche ADD COLUMN paziente_id VARCHAR(36);"))
        print("OK: aggiunta colonna 'paziente_id' su 'notifiche'.")

        # (Opzionale ma utile) Backfill: se una notifica ha appuntamento_id, ricavo paziente_id dall'appuntamento
        # Nota: per PROMEMORIA lista d'attesa con appuntamento_id NULL non si può dedurre automaticamente.
        conn.execute(
            text(
                """
                UPDATE notifiche
                SET paziente_id = (
                    SELECT a.paziente_id
                    FROM appuntamenti a
                    WHERE a.id = notifiche.appuntamento_id
                )
                WHERE paziente_id IS NULL
                  AND appuntamento_id IS NOT NULL;
                """
            )
        )
        print("OK: backfill paziente_id per notifiche collegate ad appuntamenti.")


if __name__ == "__main__":
    main()
