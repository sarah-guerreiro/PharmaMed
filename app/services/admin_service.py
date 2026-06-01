from app.utils.db import get_db

def get_admin_by_id(admin_id):

    db = get_db()

    return db.execute(
        """
        SELECT id
        FROM admins
        WHERE id = ?
        """,
        (admin_id,)
    ).fetchone()

def get_admin_by_username(db, username):

    return db.execute(
        """
        SELECT * 
        FROM admins 
        WHERE username = ?
        """, 
        (username,)
    ).fetchone()