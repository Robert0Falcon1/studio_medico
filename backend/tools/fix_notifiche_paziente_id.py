from __future__ import annotations

from sqlalchemy import text

from backend.db import engine
from backend.services import init_db


def _table_names(conn) -> set[str]:
    rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")).fetchall()
    return {r[0] for r in rows}


def _has_column(conn, table: str, col: str) -> bool:
    cols = conn.execute(text(f"PRAGMA table_info({table});")).fetchall()
    return any(c[1] == col for c in cols)  # c[1] = column name


def main() -> None:
    # Assicura che il DB sia inizializzato (nel DB corretto dell'engine)
    init_db()

    print("DB:", engine.url.database)

    with engine.begin() as conn:
        tables = _table_names(conn)
        print("Tabelle:", ", ".join(sorted(tables)))

        if "notifiche" not in tables:
            raise SystemExit("ERRORE: tabella 'notifiche' non trovata nel DB dell'engine.")

        # 1) Aggiunge colonna se manca
        if not _has_column(conn, "notifiche", "paziente_id"):
            conn.execute(text("ALTER TABLE notifiche ADD COLUMN paziente_id VARCHAR(36);"))
            print("OK: aggiunta colonna notifiche.paziente_id")
        else:
            print("OK: colonna notifiche.paziente_id già presente")

        # 2) Backfill: usa appuntamenti -> paziente_id
        if "appuntamenti" in tables and _has_column(conn, "notifiche", "appuntamento_id"):
            before_null = conn.execute(text("SELECT COUNT(*) FROM notifiche WHERE paziente_id IS NULL;")).scalar_one()
            before_total = conn.execute(text("SELECT COUNT(*) FROM notifiche;")).scalar_one()
            print(f"Notifiche: {before_total} totali, {before_null} con paziente_id NULL (prima)")

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
            print(f"Notifiche con paziente_id NULL (dopo): {after_null}")
        else:
            print("ATTENZIONE: tabella 'appuntamenti' non trovata o notifiche.appuntamento_id assente. Backfill saltato.")

        # 3) Verifica: join a pazienti
        if "pazienti" in tables:
            sample = conn.execute(
                text(
                    """
                    SELECT n.id, n.tipo, n.creata_il, n.paziente_id,
                           p.cognome, p.nome
                    FROM notifiche n
                    LEFT JOIN pazienti p ON p.id = n.paziente_id
                    ORDER BY n.id ASC
                    LIMIT 10;
                    """
                )
            ).fetchall()

            print("\nCampione (prime 10 notifiche):")
            for r in sample:
                paz = f"{r[4]} {r[5]}" if r[4] and r[5] else "-"
                print(f"- id={r[0]} tipo={r[1]} paziente={paz} paziente_id={r[3]}")
        else:
            print("ATTENZIONE: tabella 'pazienti' non trovata, join di verifica saltato.")


if __name__ == "__main__":
    main()
