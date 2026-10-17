"""Seed the database with the estate the generator produces.

Run:  python -m db.seed   (from the data_consolidator folder)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_generator import ESTATE  # noqa: E402
from db.database import add_house, connect  # noqa: E402

# Koivukuja 12, 00930 Helsinki, Finland
LATITUDE = 60.20
LONGITUDE = 24.94


def main() -> None:
    conn = connect()
    house_id = add_house(conn, ESTATE, LATITUDE, LONGITUDE)
    print(f"Seeded house id={house_id}: {ESTATE['address']} ({LATITUDE}, {LONGITUDE})")


if __name__ == "__main__":
    main()
