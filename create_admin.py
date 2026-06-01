import getpass
import sqlite3

from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pharmamed.db"

def create_admin():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password: ").strip()

    existing_admin = cursor.execute(
        """
        SELECT id
        FROM admins
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    if existing_admin:
        print("Admin already exists.")
        conn.close()
        exit()

    hashed_password = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO admins (username, password_hash) 
        VALUES (?, ?)
        """, 
        (username, hashed_password)
    )

    conn.commit()
    conn.close()

    print("Admin created successfully.")

if __name__ == "__main__":
    create_admin()