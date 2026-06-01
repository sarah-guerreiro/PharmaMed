import secrets

from datetime import datetime, timedelta, timezone

def create_user(db, first_name, last_name, email, password_hash):

    cursor = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash) 
                VALUES (?, ?, ?, ?)
                """, 
                (first_name, last_name, email, password_hash)
            )
    
    return cursor.lastrowid

def get_user_by_email(db, email):

    return db.execute(
            """
            SELECT id, email, password_hash, first_name, last_name 
            FROM users 
            WHERE email = ?
            """, 
            (email,)
        ).fetchone()

def generate_reset_token():

    token = secrets.token_urlsafe(32)
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    
    return token, expiry

def save_reset_token(db, token, expiry, user_id):

    db.execute(
        """
        UPDATE users 
        SET reset_token = ?, reset_token_expiry = ? 
        WHERE id = ?
        """, 
        (token, expiry, user_id)
    )

def get_user_by_reset_token(db, token):

    return db.execute(
        """
        SELECT * FROM users 
        WHERE reset_token = ?
        """, 
        (token,)
    ).fetchone()

def get_reset_token_expiry_and_current_time(user):

    expiry = datetime.fromisoformat(user["reset_token_expiry"])
    now = datetime.now(timezone.utc)

    return expiry, now

def reset_user_password(db, password_hash, user_id):

    db.execute(
        """
        UPDATE users 
        SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL 
        WHERE id = ?
        """, 
        (password_hash, user_id)
    )

def get_user_profile(db, user_id):

    return db.execute(
        """
        SELECT first_name, last_name 
        FROM users 
        WHERE id = ?
        """, 
        (user_id,)
    ).fetchone()

def update_user_profile(db, first_name, last_name, user_id):

    db.execute(
        """
        UPDATE users 
        SET first_name = ?, last_name = ? 
        WHERE id = ?
        """, 
        (first_name, last_name, user_id)
    )

def get_user_password(db, user_id):

    return db.execute(
        """
        SELECT password_hash 
        FROM users 
        WHERE id = ?
        """, 
        (user_id,)
    ).fetchone()

def update_user_password(db, password_hash, user_id):

    db.execute(
            """
            UPDATE users 
            SET password_hash = ? 
            WHERE id = ?
            """, 
            (password_hash, user_id)
        )