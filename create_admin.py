import sqlite3
from helpers import get_db
from werkzeug.security import generate_password_hash

db = get_db()

username = 'admin'
password = 'admin@123'

hashed_password = generate_password_hash(password)

db.execute("""INSERT INTO admins (username, password) VALUES (?, ?)""", (username, hashed_password))

db.commit()
db.close()