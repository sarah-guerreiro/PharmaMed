from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session
)

from flask_login import (
    current_user
)

from app.services.cart_service import (
    get_cart_count, 
    add_to_session_cart, 
    add_to_db_cart, 
    get_db_cart_items,
    get_session_cart_items,
    calculate_item_total,
    get_cart_total,
    update_cart_item
)

from app.utils.db import get_db

cart_bp = Blueprint("cart", __name__)

@cart_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    
    # Get product ID and quantity
    try:
        product_id = int(request.form.get('product_id'))
        quantity = int(request.form.get('quantity', 1))
    
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid product"}), 400

    # Logged in user
    if current_user.is_authenticated:
        add_to_db_cart(current_user.id, product_id, quantity)
    
    # Anonymous session
    else:
        add_to_session_cart(product_id, quantity)

    # Return updated data
    return jsonify({
        "cart_count": get_cart_count(),
        "message": "Item successfully added to cart!",
        "category": "success"
    })

@cart_bp.route('/cart')
def cart():

    # Connect to database
    db = get_db()

    # Get user id
    user_id = current_user.id if current_user.is_authenticated else None

    # Logged in user
    if user_id:

        # Get cart items 
        cart_items = get_db_cart_items(db, user_id)
        
    # Anonymous session
    else:

        # Get session cart
        session_cart = session.get("cart", {})

        # Get cart items
        cart_items = get_session_cart_items(db, session_cart)

    # Get total number of cart items
    total_items = get_cart_count()

    # Get item total price
    calculate_item_total(cart_items)

    # Get cart total price
    cart_total = get_cart_total(db, user_id)

    return render_template("cart.html", cart_items=cart_items, total_items=total_items, cart_total=cart_total)

@cart_bp.route("/update_cart", methods=["POST"])
def update_cart():
      
    # Get product ID
    try:
        product_id = int(request.form.get("product_id"))

    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid product"}), 400
    
    # Get action
    action = request.form.get("action") 

    if action not in ["increase", "decrease", "remove"]:
        return jsonify({"success": False}), 400
    
    # Get updated item
    updated_item = update_cart_item(product_id, action)

    if not updated_item:
        return jsonify({"success": False, "message": "Item not found"}), 400

    # Get item total price
    item_total = updated_item["price"] * updated_item["updated_quantity"]

    # Get cart total price
    cart_total = get_cart_total(get_db(), current_user.id if current_user.is_authenticated else None)

    # Return updated data
    return jsonify({
        "success": True,
        "cart_count": get_cart_count(),
        "product_id": updated_item["product_id"],
        "updated_quantity": updated_item["updated_quantity"],
        "item_total": item_total,
        "cart_total": cart_total,
        "stock": updated_item["stock"]
    })
