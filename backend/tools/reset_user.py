from __future__ import annotations

import sys

from sqlalchemy import text

from backend.db import db_session


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m backend.tools.reset_user <username>")
        raise SystemExit(2)

    username = sys.argv[1].strip().lower()
    if not username:
        print("Username non valido.")
        raise SystemExit(2)

    with db_session() as s:
        s.execute(text("DELETE FROM utenti WHERE username = :u"), {"u": username})
        s.commit()

    print(f"OK: utente '{username}' cancellato (se esisteva).")


if __name__ == "__main__":
    main()
