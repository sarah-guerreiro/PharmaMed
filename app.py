import os
import sqlite3

from flask import Flask, g, render_template

# Configure application
app = Flask(__name__)

# Database connection
DATABASE = "pharmamed.db"

# Open database upon request
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row

        # Enable foreign keys
        g.db.execute("PRAGMA foreign_keys = ON")
        
    return g.db

# Build database structure
def init_db():
    db = get_db()
    with open("schema.sql") as schema_file:
        db.executescript(schema_file.read())
    db.commit()

# Close database after request
@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.route("/")
def index():
    return render_template("layout.html")
