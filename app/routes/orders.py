from flask import (
    Blueprint, 
    flash,
    redirect, 
    render_template, 
    request, 
    session,
    url_for
)

from flask_login import (
    login_required,
    current_user
)

from app.services.address_service import (
    get_user_addresses, 
    reset_existing_addresses,
    count_existing_addresses,
    create_user_address
)

from app.services.order_service import (
    get_checkout_data,
    get_checkout_address,
    get_cart,
    get_cart_items_for_order,
    get_shipping_cost,
    calculate_order_totals,
    reserve_stock,
    create_order,
    get_user_order,
    get_order_items
)

from app.utils.db import get_db

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():

    # Connect to database
    db = get_db()

    # Get user addresses
    addresses = get_user_addresses(db, current_user.id)

    # Error dictionaries
    address_error = {}
    form_error = {}
    shipping_error = {}

    if request.method == "POST":

        # Check if user wants to add a new address
        adding_address = any([
            request.form.get("full_name"),
            request.form.get("address_line"),
            request.form.get("postal_code"),
            request.form.get("city"),
            request.form.get("country")
        ])

        if adding_address:
            
            # Get address form data
            full_name = request.form.get("full_name", "").strip().title()
            address_line = request.form.get("address_line", "").strip().title()
            postal_code = request.form.get("postal_code", "").strip()
            city = request.form.get("city", "").strip().title()
            country = request.form.get("country", "").strip().title()
            is_default = 1 if request.form.get("is_default") else 0
            
            # Input validation
            if not full_name:
                form_error["full_name"] = "Full name is required"

            if not address_line:
                form_error["address_line"] = "Address is required"

            if not postal_code:
                form_error["postal_code"] = "Postal code is required"

            if not city:
                form_error["city"] = "City is required"

            if not country:
                form_error["country"] = "Country is required"

            if form_error:

                # Get user addresses
                addresses = get_user_addresses(db, current_user.id)

                return render_template("checkout.html", addresses=addresses, form_error=form_error)
            
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

            flash("Address added successfully", "success")
            return redirect(url_for("orders.checkout"))
        
        else:

            # Get address ID and shipping method
            address_id = request.form.get("address_id", "")
            shipping_method = request.form.get("shipping_method", "")

            # Check if user selected shipping address and method
            if not address_id:
                address_error["address"] = "Please select or add a shipping address"

            if not shipping_method:
                shipping_error["shipping"] = "Please select a shipping method"

            if address_error or shipping_error:

                # Get user addresses
                addresses = get_user_addresses(db, current_user.id)

                return render_template("checkout.html", addresses=addresses, address_error=address_error, shipping_error=shipping_error)
        
        # Store selected address ID and shipping method
        session["checkout"] = {
            "address_id": address_id,
            "shipping_method": shipping_method
        }

        return redirect(url_for("orders.order_summary"))

    else:
        return render_template("checkout.html", addresses=addresses, address_error=address_error, shipping_error=shipping_error, form_error=form_error)
    
@orders_bp.route("/order_summary")
@login_required
def order_summary():

    # Connect to database
    db = get_db()

    # Get selected address ID and shipping method on checkout
    checkout = get_checkout_data()

    if not checkout:
        flash("Please complete checkout first", "error")
        return redirect(url_for("orders.checkout"))

    # Get selected address
    address = get_checkout_address(db, checkout["address_id"], current_user.id)

    if not address:
        flash("Selected address was not found", "error")
        return redirect(url_for("orders.checkout"))
    
    # Get cart
    cart = get_cart(db, current_user.id)

    if not cart:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart.cart"))

    cart_id = cart["id"]

    # Get cart items
    cart_items = get_cart_items_for_order(db, cart_id)
    
    if not cart_items:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart.cart"))

    # Calculate totals
    shipping_cost = get_shipping_cost(checkout["shipping_method"])

    if shipping_cost is None:
        flash("Invalid shipping method selected", "error")
        return redirect(url_for("orders.checkout"))

    totals = calculate_order_totals(cart_items, shipping_cost)

    return render_template("order_summary.html", address=address, cart_items=cart_items, subtotal=totals["subtotal"], shipping_cost=shipping_cost, total=totals["total"], 
                           shipping_method=checkout["shipping_method"])

@orders_bp.route("/place_order", methods=["POST"])
@login_required
def place_order():

    # Connect to database
    db = get_db()

    # Get selected address ID and shipping method on checkout
    checkout = get_checkout_data()

    if not checkout:
        flash("Please complete checkout first", "error")
        return redirect(url_for("orders.checkout"))

    # Get selected address
    address = get_checkout_address(db, checkout["address_id"], current_user.id)

    if not address:
        flash("Selected address was not found", "error")
        return redirect(url_for("orders.checkout"))

    # Get cart
    cart = get_cart(db, current_user.id)

    if not cart:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart.cart"))

    cart_id = cart["id"]

    # Get cart items
    cart_items = get_cart_items_for_order(db, cart_id)

    if not cart_items:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart.cart"))

    # Calculate totals
    shipping_cost = get_shipping_cost(checkout["shipping_method"])

    if shipping_cost is None:
        flash("Invalid shipping method selected", "error")
        return redirect(url_for("orders.checkout"))

    totals = calculate_order_totals(cart_items, shipping_cost)

    try: 

        # Stock validation
        if not reserve_stock(db, cart_items):
            flash("Some items are out of stock", "error")
            return redirect(url_for("cart.cart"))

        # Create order
        order_id = create_order(
            db=db,             
            user_id=current_user.id,
            address_id=checkout["address_id"],
            address=address,
            shipping_method=checkout["shipping_method"],
            cart_items=cart_items,
            subtotal=totals["subtotal"],
            shipping_cost=totals["shipping_cost"],
            total=totals["total"],
            cart_id=cart_id
        )

        db.commit()

        # Clear session checkout
        session.pop("checkout", None)

        return redirect(url_for("orders.order_success", order_id=order_id))
    
    except Exception:
        db.rollback()
        flash("Something went wrong while placing your order", "error")
        return redirect(url_for("cart.cart"))

@orders_bp.route("/order_success/<int:order_id>")
@login_required
def order_success(order_id):

    # Connect to database
    db = get_db()

    # Get order
    order = get_user_order(db, order_id, current_user.id)

    if not order:
        flash("Order not found", "error")
        return redirect(url_for("orders.checkout"))

    # Get order items
    items = get_order_items(db, order_id)

    return render_template("order_success.html", order_id=order_id, order=order, items=items)