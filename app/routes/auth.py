import sqlite3

from app.utils.validators import PASSWORD_PATTERN, EMAIL_PATTERN

from flask import (
    Blueprint, 
    flash, 
    render_template, 
    redirect, 
    request, 
    url_for
)

from flask_login import (
    login_required,
    login_user, 
    logout_user
)

from werkzeug.security import (
    check_password_hash, 
    generate_password_hash
)

from app.models.user import User

from app.services.cart_service import merge_carts 
from app.services.user_service import (
    create_user,
    get_user_by_email,
    generate_reset_token,
    save_reset_token,
    get_user_by_reset_token,
    get_reset_token_expiry_and_current_time,
    reset_user_password
)

from app.utils.db import get_db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Get register form data 
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms = request.form.get("terms") is not None

        # Error dictionary
        error = {}

        # Input validation
        if not first_name:
            error["first_name"] = "First name is missing"
            
        if not last_name:
            error["last_name"] = "Last name is missing"
        
        if not email:
            error["email"] = "Email is missing"

        elif not EMAIL_PATTERN.match(email):
            error["email"] = "Invalid email format"
                
        if not password:
            error["password"] = "Password is missing"

        elif not PASSWORD_PATTERN.match(password):
            error["password"] = "Password must be at least 8 characters long and include a letter, a number, and a special character"
            
        if not confirm_password:
            error["confirm_password"] = "Must confirm password"

        elif password != confirm_password:
            error["confirm_password"] = "Passwords must match"

        if not terms:
            error["terms"] = "Terms and privacy policy must be accepted"
        
        if error:
            return render_template("register.html", error=error, first_name=first_name, last_name=last_name, email=email, terms=terms)

        # Hash password
        password_hash = generate_password_hash(password)

        try:

            # Connect to database
            db = get_db()

            # Insert user into database and get user ID
            user_id = create_user(db, first_name, last_name, email, password_hash)
            
            db.commit()

        # Check if email already exists
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            return redirect(url_for("auth.register"))

        # Auto login after register
        login_user(User(user_id, email, first_name, last_name))

        # Merge carts
        merge_carts(db, user_id)

        flash("Account created successfully!", "success")
        return redirect(url_for("main.index"))
    
    else:
        return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # Get login form data
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        # Error dictionary
        error = {}

        # Input validation
        if not email:
            error["email"] = "Email is missing"

        if not password:
            error["password"] = "Password is missing"

        if error:
            return render_template("login.html", error=error, email=email)
  
        # Connect to database
        db = get_db()

        # Get user details
        user = get_user_by_email(db, email)

        # Check if email exists and password is correct
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("auth.login"))

        # Remember which user has logged in
        login_user(User(user["id"], email, user["first_name"], user["last_name"]))

        # Merge carts
        merge_carts(db, user["id"])

        return redirect(url_for("main.index"))

    else:
        return render_template("login.html")

# AI assistance: ChatGPT was consulted for guidance on implementing password reset tokens 
# and token expiration.

@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        # Get user email
        email = request.form.get("email", "").lower().strip()

        # Error dictionary
        error = {}

        # Input validation
        if not email:
            error["email"] = "Email is missing"

        if error:
            return render_template("forgot_password.html", error=error)

        # Connect to database
        db = get_db()

        # Get user 
        user = get_user_by_email(db, email)

        if user:

            # Generate reset token and expiry
            token, expiry = generate_reset_token()

            # Save generated reset token and expiry
            save_reset_token(
                db=db,
                token=token,
                expiry=expiry,
                user_id=user["id"]
            )
            
            db.commit()

            # Show reset link
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            flash(f'<a href="{reset_link}">Click here to reset password</a>', "persistent")

        else:

            # For security
            flash("If that email exists, a reset link was generated.", "info")

        return redirect(url_for("auth.login"))

    else:
        return render_template("forgot_password.html")
    
@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    # Connect to database
    db = get_db()
 
    # Get user details
    user = get_user_by_reset_token(db, token)

    if not user:
        flash("Invalid or expired token", "error")
        return redirect(url_for("auth.login"))
    
    # Check reset token expiry
    if not user["reset_token_expiry"]:
        flash("Reset link expired", "error")
        return redirect(url_for("auth.login"))
    
    expiry, now = get_reset_token_expiry_and_current_time(user)

    if  now > expiry:
        flash("Reset link expired", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        # Get form data
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Error dictionary
        error = {}

        # Input validation     
        if not password:
            error["password"] = "Password is missing"

        elif not PASSWORD_PATTERN.match(password):
            error["password"] = "Password must be at least 8 characters long and include a letter, a number, and a special character"
        
        elif check_password_hash(user["password_hash"], password):
            error["password"] = "New password must be different from the old password"
            
        if not confirm_password:
            error["confirm_password"] = "Must confirm password"

        elif password != confirm_password:
            error["confirm_password"] = "Passwords do not match"
        
        if error:
            return render_template("reset_password.html", token=token, error=error, password=password, confirm_password=confirm_password)

        # Hash password
        password_hash = generate_password_hash(password)

        # Reset user password
        reset_user_password(
            db=db,
            password_hash=password_hash,
            user_id=user["id"]
        )
        
        db.commit()

        flash("Password reset successful! Please, login.", "success")
        return redirect(url_for("auth.login"))

    else:
        return render_template("reset_password.html", token=token)

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():

    # Clear any open session
    logout_user()

    # Redirect user to index page
    return redirect(url_for("main.index"))