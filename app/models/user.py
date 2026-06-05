from flask_login import UserMixin

from app.extensions import login_manager

from app.utils.db import get_db

class User(UserMixin):

    def __init__(self, id, email, first_name, last_name):

        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

# Load user
@login_manager.user_loader
def load_user(user_id):

    # Connect to database
    db = get_db()
    
    # Get user
    user = db.execute(
        """
        SELECT id, email, first_name, last_name 
        FROM users 
        WHERE id = ?
        """, 
        (int(user_id),)
    ).fetchone()

    if user is None:
        return None

    return User(
        user["id"], 
        user["email"], 
        user["first_name"], 
        user["last_name"]
    )