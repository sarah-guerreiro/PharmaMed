import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("pharmamed.db")
cursor = conn.cursor()

username = "admin"
password = "admin@123"

hashed_password = generate_password_hash(password)

cursor.execute("""INSERT INTO admins (username, password_hash) VALUES (?, ?)""", (username, hashed_password))

conn.commit()
conn.close()

print("Admin created successfully.")