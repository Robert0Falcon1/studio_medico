from __future__ import annotations

from backend.db import engine


def main() -> None:
    print("ENGINE URL:", engine.url)
    print("DB FILE   :", engine.url.database)


if __name__ == "__main__":
    main()
