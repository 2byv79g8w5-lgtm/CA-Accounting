"""Run once to create all tables: `python init_db.py`

For schema changes after this, you'll want Alembic migrations rather than
re-running this (it won't alter existing tables, only create missing ones).
"""

from app.database import Base, engine
from app import models  # noqa: F401 — import ensures models are registered on Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
