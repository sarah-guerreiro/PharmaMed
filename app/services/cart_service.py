from flask import session

from flask_login import current_user

from app.utils.db import get_db

def get_cart_count():

    db = get_db()

    # Logged in user
    if current_user.is_authenticated:
        return db_cart_count(db, current_user.id)

    # Anonymous user
    session_cart = session.get('cart', {})
    return sum(session_cart.values())

def db_cart_count(db, user_id):

    cart_count = db.execute(
        """
        SELECT SUM(quantity) as total 
        FROM cart_items ci 
        JOIN carts c ON ci.cart_id = c.id 
        WHERE c.user_id = ?
        """, 
        (user_id,)
    ).fetchone()
    
    return cart_count["total"] or 0

def add_to_session_cart(product_id, quantity):

    cart = session.get('cart', {})

    product_id = str(product_id)

    cart[product_id] = cart.get(product_id, 0) + quantity

    session['cart'] = cart
    session.modified = True

def add_to_db_cart(user_id, product_id, quantity):

    db = get_db()

    # Get or create new cart
    cart = db.execute(
        """
        SELECT id 
        FROM carts 
        WHERE user_id = ?
        """, 
        (user_id,)
    ).fetchone()

    if not cart:
        cursor = db.execute(
            """
            INSERT INTO carts (user_id) 
            VALUES (?)
            """, 
            (user_id,)
        )

        cart_id = cursor.lastrowid
        db.commit()
    
    else:
        cart_id = cart["id"]

    # Check if item exists
    item = db.execute(
        """
        SELECT quantity 
        FROM cart_items 
        WHERE cart_id = ? 
        AND product_id = ?
        """, 
        (cart_id, product_id)
    ).fetchone()

    if item:
        db.execute(
            """
            UPDATE cart_items 
            SET quantity = quantity + ? 
            WHERE cart_id = ? 
            AND product_id = ?
            """, 
            (quantity, cart_id, product_id)
        )
    
    else:
        db.execute(
            """
            INSERT INTO cart_items (cart_id, product_id, quantity) 
            VALUES (?, ?, ?)
            """, 
            (cart_id, product_id, quantity)
        )

    db.commit()

def get_db_cart_items(db, user_id):
    rows = db.execute(
        """
        SELECT p.product_id, p.image_url, p.name, b.name AS brand, p.pack_size, p.price, p.stock, ci.quantity
        FROM cart_items ci
        JOIN carts c ON ci.cart_id = c.id
        JOIN products p ON ci.product_id = p.product_id
        JOIN brands b ON p.brand_id = b.brand_id
        WHERE c.user_id = ?
        AND p.is_active = 1
        """,
        (user_id,)
    ).fetchall()

    return [dict(row) for row in rows]

def get_session_cart_items(db, session_cart):
    if not session_cart:
        return []

    product_ids = list(session_cart.keys())

    placeholders = ",".join("?" * len(product_ids))

    rows = db.execute(
        f"""
        SELECT p.product_id, p.image_url, p.name, b.name AS brand, p.pack_size, p.price, p.stock 
        FROM products p
        JOIN brands b ON p.brand_id = b.brand_id
        WHERE p.is_active = 1
        AND p.product_id IN ({placeholders})
        """,
        tuple(product_ids)
    ).fetchall()

    cart_items = []

    for row in rows:
        pid = str(row["product_id"])

        cart_items.append({
            "product_id": row["product_id"],
            "image_url": row["image_url"],
            "name": row["name"],
            "brand": row["brand"],
            "pack_size": row["pack_size"],
            "price": row["price"],
            "quantity": session_cart.get(pid, 0),
            "stock": row["stock"]
        })

    return cart_items

def calculate_item_total(items):
    for item in items:
        item["item_total"] = item["price"] * item["quantity"]

    return items

def get_cart_total(db, user_id=None):

    # Logged in user
    if user_id:
        result = db.execute(
            """
            SELECT SUM(ci.quantity * p.price) as total 
            FROM cart_items ci 
            JOIN carts c ON ci.cart_id = c.id 
            JOIN products p ON ci.product_id = p.product_id 
            WHERE c.user_id = ?
            """, 
            (user_id,)
        ).fetchone()

        return result["total"] or 0
    
    # Anonymous session
    else:
        session_cart = session.get("cart", {})
        total = 0

        if session_cart:
            placeholders = ",".join("?" * len(session_cart.keys()))
            products = db.execute(f"SELECT product_id, price FROM products WHERE product_id IN ({placeholders})", tuple(session_cart.keys())).fetchall()

            for product in products:
                p_id = str(product["product_id"])
                total += product["price"] * session_cart[p_id]

        return total
    
def apply_cart_action(quantity, stock, action):
    
    if action == "increase":
        return min(quantity + 1, stock)

    elif action == "decrease":
        return quantity - 1 if quantity > 1 else 0

    elif action == "remove":
        return 0

    return quantity

def update_cart_item(product_id, action):

    # Connect to database
    db = get_db()

    # Get user ID
    user_id = current_user.id if current_user.is_authenticated else None

    # Logged in user
    if user_id:

        # Get cart
        cart = db.execute(
            """
            SELECT id 
            FROM carts 
            WHERE user_id = ?
            """, 
            (user_id,)
        ).fetchone()
        
        if not cart:
            return None
        
        cart_id = cart["id"]

        # Get cart item
        item = db.execute(
            """
            SELECT ci.quantity, p.stock, p.price 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.product_id 
            WHERE ci.cart_id = ? 
            AND ci.product_id = ? 
            AND p.is_active = 1
            """, 
            (cart_id, product_id)
        ).fetchone()

        if not item:
            return None

        # Get item quantity, stock and price
        quantity = item["quantity"]
        stock = item["stock"]
        price = item["price"]

        # Get item updated quantity
        updated_quantity = apply_cart_action(quantity, stock, action)
        
        if updated_quantity > 0:
            db.execute(
                """
                UPDATE cart_items 
                SET quantity = ? 
                WHERE cart_id = ? 
                AND product_id = ?
                """, 
                (updated_quantity, cart_id, product_id)
            )
        
        else:
            db.execute(
                """
                DELETE FROM cart_items 
                WHERE cart_id = ? 
                AND product_id = ?
                """, 
                (cart_id, product_id)
            )  
        
        db.commit()

    # Anonymous session
    else:

        # Get session cart
        cart = session.get("cart", {})
        p_id = str(product_id)

        if p_id not in cart:
            return None

        # Get cart item
        item = db.execute(
            """
            SELECT stock, price 
            FROM products 
            WHERE product_id = ? 
            AND is_active = 1
            """, 
            (product_id,)
        ).fetchone()

        if not item:
            return None
        
        # Get item quantity, stock and price
        quantity = cart[p_id]
        stock = item["stock"]
        price = item["price"]

        # Get item updated quantity
        updated_quantity = apply_cart_action(quantity, stock, action)

        if updated_quantity > 0:
            cart[p_id] = updated_quantity

        else:
            cart.pop(p_id, None)

        session["cart"] = cart
        session.modified = True

    return {
        "product_id": product_id,
        "updated_quantity": updated_quantity,
        "stock": stock,
        "price": price
    }

def merge_carts(db, user_id):

    # Get session cart
    session_cart = session.get("cart", {})

    if not session_cart:
        return

    # Ensure cart exists
    cart = db.execute(
        """
        SELECT id 
        FROM carts 
        WHERE user_id = ?
        """, 
        (user_id,)
    ).fetchone()

    if not cart:
        db.execute(
            """
            INSERT INTO carts (user_id) 
            VALUES (?)
            """, 
            (user_id,)
        )

        cart = db.execute(
            """
            SELECT id 
            FROM carts 
            WHERE user_id = ?
            """, 
            (user_id,)
        ).fetchone()

    # Get user cart id
    cart_id = cart["id"]

    for product_id, session_quantity in session_cart.items():

        # Check if item already exists in database carts
        item = db.execute(
            """
            SELECT ci.quantity, p.stock 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.product_id 
            WHERE ci.cart_id = ? 
            AND ci.product_id = ?
            """, 
            (cart_id, product_id)
        ).fetchone()

        if item:

            # Get item quantity, respecting stock
            new_quantity = min(item["quantity"] + session_quantity, item["stock"])

            # Update database
            db.execute(
                """UPDATE cart_items 
                SET quantity = ? 
                WHERE cart_id = ? 
                AND product_id = ?
                """, 
                (new_quantity, cart_id, product_id)
            )

        else:

            # Get stock
            product = db.execute(
                """
                SELECT stock 
                FROM products 
                WHERE product_id = ?
                """, 
                (product_id,)
            ).fetchone()

            if product:

                # Get item quantity, respecting stock
                quantity = min(session_quantity, product["stock"])

                # Update database
                db.execute(
                    """
                    INSERT INTO cart_items (cart_id, product_id, quantity) 
                    VALUES (?, ?, ?)
                    """, 
                    (cart_id, product_id, quantity)
                )

    db.commit()

    # Clear session cart
    session.pop("cart", None)