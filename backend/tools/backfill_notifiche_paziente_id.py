from __future__ import annotations

from sqlalchemy import text

from backend.db import engine


def main() -> None:
    print("DB:", engine.url.database)

    with engine.begin() as conn:
        # Controlli base
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()}
        if "notifiche" not in tables or "appuntamenti" not in tables:
            raise SystemExit("ERRORE: tabelle 'notifiche' o 'appuntamenti' non presenti nel DB.")

        cols = {c[1] for c in conn.execute(text("PRAGMA table_info(notifiche);")).fetchall()}
        if "paziente_id" not in cols:
            raise SystemExit("ERRORE: colonna 'paziente_id' non presente su 'notifiche' (migrazione non fatta).")

        before_null = conn.execute(text("SELECT COUNT(*) FROM notifiche WHERE paziente_id IS NULL;")).scalar_one()
        join_match = conn.execute(
            text("SELECT COUNT(*) FROM notifiche n JOIN appuntamenti a ON a.id = n.appuntamento_id;")
        ).scalar_one()

        print(f"NULL paziente_id (prima): {before_null}")
        print(f"Notifiche matchabili via appuntamento_id: {join_match}")

        # Backfill: solo dove appuntamento_id è valorizzato
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

        after_null = conn.execute(text("SELECT COUNT(*) FROM notifiche WHERE paziente_id IS NULL;")).scalar_one()
        print(f"NULL paziente_id (dopo): {after_null}")

        # Campione verifica (prime 10)
        sample = conn.execute(
            text(
                """
                SELECT n.id, n.tipo, n.appuntamento_id, n.paziente_id, p.cognome, p.nome
                FROM notifiche n
                LEFT JOIN pazienti p ON p.id = n.paziente_id
                ORDER BY n.id ASC
                LIMIT 10;
                """
            )
        ).fetchall()

        print("Campione:")
        for r in sample:
            paz = f"{r[4]} {r[5]}" if r[4] and r[5] else "-"
            print(f"- id={r[0]} tipo={r[1]} paziente={paz} app_id={r[2]} paz_id={r[3]}")


if __name__ == "__main__":
    main()
