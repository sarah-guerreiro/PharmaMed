from flask import (
    flash,
    redirect,
    session,
    url_for
)

from functools import wraps

from app.services.admin_service import get_admin_by_id

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        admin_id = session.get("admin_id")

        if not admin_id:
            flash("Please log in as admin", "error")
            return redirect(url_for("admin.login"))

        # Get admin by ID
        admin = get_admin_by_id(admin_id)

        if not admin:
            session.pop("admin_id", None)
            flash("Please log in as admin", "error")
            return redirect(url_for("admin.login"))

        return f(*args, **kwargs)

    return decorated_function
