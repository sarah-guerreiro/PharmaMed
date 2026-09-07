# AI assistance: ChatGPT was consulted for discussing implementation approaches,
# debugging, reviewing route structure, and suggesting improvements to account
# management functionality, including profile, addresses, orders, and password
# management.

from flask import (
    Blueprint, 
    flash, 
    redirect, 
    render_template, 
    request, 
    url_for
)

from flask_login import (
    login_required, 
    current_user
)

from werkzeug.security import (
    check_password_hash, 
    generate_password_hash
)

from app.services.address_service import (
    get_user_addresses,
    reset_existing_addresses,
    count_existing_addresses,
    create_user_address,
    update_user_address,
    delete_user_address
)

from app.services.order_service import (
    get_user_order,
    get_order_items,
    get_user_orders
)

from app.services.user_service import (
    get_user_profile,
    update_user_profile,
    get_user_password,
    update_user_password
)

from app.utils.db import get_db
from app.utils.validators import PASSWORD_PATTERN

account_bp = Blueprint("account", __name__, url_prefix="/account")

@account_bp.route("/home")
@login_required
def account_home():

    # Connect to database
    db = get_db()

    # Get user first name
    user = get_user_profile(db, current_user.id)
    first_name = user["first_name"]

    # Get orders and number of items per order
    orders = get_user_orders(db, current_user.id, limit=1)

    return render_template("account/dashboard.html", first_name=first_name, active_page=None, orders=orders)

@account_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = get_user_profile(db, current_user.id)

    # Get user addresses
    addresses = get_user_addresses(db, current_user.id)

    # Error dictionary
    error = {}

    if request.method == "POST":

        # Get first and last names from form
        first_name = request.form.get("first_name", "").strip().title()
        last_name = request.form.get("last_name", "").strip().title()

        # Prevent empty fields 
        if not first_name:
            error["first_name"] = "First name is required"
            
        if not last_name:
            error["last_name"] = "Last name is required"

        if error:
            return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], profile_error=error, addresses=addresses)

        # Update database if first name or last name changed
        if (first_name != user["first_name"] or last_name != user["last_name"]):
            
            update_user_profile(db=db, first_name=first_name, last_name=last_name, user_id=current_user.id)

            db.commit()

            flash("Profile updated successfully!", "success")

            # Get updated names
            user = get_user_profile(db, current_user.id)

        return redirect(url_for("account.profile"))
    
    else:
        return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], profile_error=error, addresses=addresses)

@account_bp.route("/addresses", methods=["GET", "POST"])
@login_required
def addresses():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = get_user_profile(db, current_user.id)

    # Get user addresses
    addresses = get_user_addresses(db, current_user.id)

    # Error dictionary
    add_error = {}

    if request.method == "POST":

        # Get address form data
        full_name = request.form.get("full_name", "").strip().title()
        address_line = request.form.get("address_line", "").strip().title()
        postal_code = request.form.get("postal_code", "").strip()
        city = request.form.get("city", "").strip().title()
        country = request.form.get("country", "").strip().title()
        is_default = 1 if request.form.get("is_default") else 0
     
        # Input validation
        if not full_name:
            add_error["full_name"] = "Full name is required"

        if not address_line:
            add_error["address_line"] = "Address is required"

        if not postal_code:
            add_error["postal_code"] = "Postal code is required"

        if not city:
            add_error["city"] = "City is required"

        if not country:
            add_error["country"] = "Country is required"

        if add_error:

            # Get user addresses
            addresses = get_user_addresses(db, current_user.id)

            # Get form values
            add_form={
                "full_name": full_name,
                "address_line": address_line,
                "postal_code": postal_code,
                "city": city,
                "country": country
            }

            return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], addresses=addresses, add_error=add_error, add_form=add_form)
        
        # Reset existing addresses
        if is_default:
            reset_existing_addresses(db=db, user_id=current_user.id)

        # Auto-set first address to default
        existing_addresses = count_existing_addresses(db, current_user.id)

        if existing_addresses == 0:
            is_default = 1

        # Insert new address into database
        create_user_address(
            db=db, 
            user_id=current_user.id,
            full_name=full_name, 
            address_line=address_line, 
            postal_code=postal_code, 
            city=city, 
            country=country, 
            is_default=is_default
        )

        db.commit()

        flash("Address added successfully!", "success")
        return redirect(url_for("account.addresses"))

    else:     
        return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], addresses=addresses, add_error=add_error)

@account_bp.route("/addresses/edit", methods=["POST"])
@login_required
def edit_address():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = get_user_profile(db, current_user.id)

    # Get edit address form data
    address_id = request.form.get("address_id")
    full_name = request.form.get("full_name", "").strip().title()
    address_line = request.form.get("address_line", "").strip().title()
    postal_code = request.form.get("postal_code", "").strip()
    city = request.form.get("city", "").strip().title()
    country = request.form.get("country", "").strip().title()

    # Error dictionary
    edit_error = {}

    # Input validation
    if not full_name:
        edit_error["full_name"] = "Full name is required"

    if not address_line:
        edit_error["address_line"] = "Address is required"

    if not postal_code:
        edit_error["postal_code"] = "Postal code is required"

    if not city:
        edit_error["city"] = "City is required"

    if not country:
        edit_error["country"] = "Country is required"

    if edit_error:

        # Get user addresses
        addresses = get_user_addresses(db, current_user.id)

        # Get form values
        edit_form={
            "full_name": full_name,
            "address_line": address_line,
            "postal_code": postal_code,
            "city": city,
            "country": country
        }

        return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], addresses=addresses, edit_error=edit_error, edit_address_id=address_id, edit_form=edit_form)
    
    # Update address in database
    update_user_address(
        db=db,
        full_name=full_name, 
        address_line=address_line, 
        postal_code=postal_code, 
        city=city, 
        country=country, 
        address_id=address_id, 
        user_id=current_user.id
    )

    db.commit()

    flash("Address updated!", "success")
    return redirect(url_for("account.addresses"))

@account_bp.route("/addresses/delete", methods=["POST"])
@login_required
def delete_address():

    # Connect to database
    db = get_db()

    # Get user address ID
    address_id = request.form.get("address_id")

    # Delete address from database
    delete_user_address(db=db, address_id=address_id, user_id=current_user.id)

    db.commit()

    flash("Address deleted!", "success")
    return redirect(url_for("account.addresses"))

@account_bp.route("/orders")
@login_required
def orders():

    # Connect to database
    db = get_db()

    # Get orders and number of items per order
    orders = get_user_orders(db, current_user.id)

    return render_template("account/orders.html", active_page="orders", orders=orders)

@account_bp.route("/order_details/<int:order_id>")
@login_required
def order_details(order_id):

    # Connect to database
    db = get_db()

    # Get order
    order = get_user_order(db, order_id, current_user.id)

    if not order:
        flash("Order not found", "error")
        return redirect(url_for("account.orders"))

    # Get order items
    items = get_order_items(db, order_id)

    return render_template("account/order_details.html", active_page="orders", order=order, items=items)

@account_bp.route("/security", methods=["GET", "POST"])
@login_required
def change_password():

    # Connect to database
    db = get_db()

    if request.method == "POST":

        # Get form data
        current_password = request.form.get("current_password", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Error dictionary
        error = {}

        # Get current password
        user = get_user_password(db, current_user.id)

        # Input validation
        if not current_password:
            error["current_password"] = "Current password is required"

        elif not check_password_hash(user["password_hash"], current_password):
            error["current_password"] = "Incorrect current password"

        if not password:
            error["password"] = "Password is required"

        elif not PASSWORD_PATTERN.match(password):
            error["password"] = "Password must be at least 8 characters long and include a letter, a number, and a special character"
       
        elif check_password_hash(user["password_hash"], password):
            error["password"] = "New password must be different from the old password"

        if not confirm_password:
            error["confirm_password"] = "Must confirm password"

        elif password != confirm_password:
            error["confirm_password"] = "Passwords do not match"

        if error:
            return render_template("account/security.html", active_page="security", error=error)
        
        # Hash new password
        password_hash = generate_password_hash(password)

        # Update user password
        update_user_password(db=db, password_hash=password_hash, user_id=current_user.id)

        db.commit()

        flash("Password updated successfully!", "success")
        return redirect(url_for("account.change_password"))

    else:
        return render_template("account/security.html", active_page="security")