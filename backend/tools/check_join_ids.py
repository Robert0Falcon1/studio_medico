from __future__ import annotations

from sqlalchemy import text
from backend.db import engine


def main() -> None:
    with engine.connect() as c:
        direct = c.execute(
            text("SELECT COUNT(*) FROM notifiche n JOIN appuntamenti a ON a.id = n.appuntamento_id")
        ).scalar()
        normalized = c.execute(
            text(
                "SELECT COUNT(*) FROM notifiche n "
                "JOIN appuntamenti a ON REPLACE(a.id,'-','') = REPLACE(n.appuntamento_id,'-','')"
            )
        ).scalar()
        notif_sample = c.execute(
            text("SELECT id, appuntamento_id FROM notifiche WHERE appuntamento_id IS NOT NULL LIMIT 3")
        ).fetchall()
        app_sample = c.execute(text("SELECT id, paziente_id FROM appuntamenti LIMIT 3")).fetchall()

    print("direct join:", direct)
    print("normalized join:", normalized)
    print("notif sample:", notif_sample)
    print("app sample:", app_sample)


if __name__ == "__main__":
    main()
