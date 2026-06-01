from pathlib import Path
import sqlite3
from flask import g

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "pharmamed.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# Open database upon request
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row

        # Enable foreign keys
        g.db.execute("PRAGMA foreign_keys = ON")
        
    return g.db

# Build database structure
def init_db():
    db = get_db()

    with open(SCHEMA_PATH) as schema_file:
        db.executescript(schema_file.read())

    db.commit()

# Close database after request
def close_db(exception=None):
    db = g.pop("db", None)
    
    if db is not None:
        db.close()