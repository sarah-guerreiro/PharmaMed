from flask import session

def get_checkout_data():
    checkout = session.get("checkout")

    if not checkout:
        return None

    return {
        "address_id": checkout.get("address_id"),
        "shipping_method": checkout.get("shipping_method")
    }

def get_checkout_address(db, address_id, user_id):

    return db.execute(
        """
        SELECT *
        FROM addresses
        WHERE id = ?
        AND user_id = ?
        """,
        (address_id, user_id)
    ).fetchone()

def get_cart(db, user_id):

    return db.execute(
        """
        SELECT id
        FROM carts
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

def get_cart_items_for_order(db, cart_id):

    return db.execute(
        """
        SELECT p.name, p.price, p.pack_size, p.image_url, ci.product_id, ci.quantity 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.product_id 
        WHERE ci.cart_id = ?
        """, 
        (cart_id,)
    ).fetchall()

def get_shipping_cost(shipping_method):

    shipping_methods = {
        "standard": 1.99,
        "express": 5.99
    }

    return shipping_methods.get(shipping_method)

def calculate_order_totals(cart_items, shipping_cost):

    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    total = subtotal + shipping_cost

    return {
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "total": total
    }

# AI assistance: ChatGPT was consulted for guidance on implementing the stock reservation logic 
# used when placing orders, including checking available stock and preventing an order from reserving 
# more stock than is available.

def reserve_stock(db, cart_items):

    for item in cart_items:
        updated = db.execute(
            """
            UPDATE products
            SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            AND stock >= ?
            """,
            (item["quantity"], item["product_id"], item["quantity"])
        )

        if updated.rowcount == 0:
            return False

    return True

def create_order(
    db,
    user_id,
    address_id,
    address,
    shipping_method,
    cart_items,
    subtotal,
    shipping_cost,
    total,
    cart_id
):
    # Create order 
    cursor = db.execute(
        """
        INSERT INTO orders (user_id, address_id, full_name, address_line, postal_code, city, country, shipping_method, subtotal, shipping_cost, total, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        (user_id, address_id, address["full_name"], address["address_line"], address["postal_code"], 
         address["city"], address["country"], shipping_method, subtotal, shipping_cost, total, "pending")
    )

    order_id = cursor.lastrowid

    # Insert order items
    for item in cart_items:
        db.execute(
            """
            INSERT INTO order_items (order_id, product_id, name, pack_size, quantity, price) 
            VALUES (?, ?, ?, ?, ?, ?)
            """, 
            (order_id, item["product_id"], item["name"], item["pack_size"], item["quantity"], item["price"])
        )

    # Clear cart
    db.execute(
        """
        DELETE FROM cart_items 
        WHERE cart_id = ?
        """, 
        (cart_id,)
    )

    return order_id

def get_user_order(db, order_id, user_id):

    return db.execute(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        AND user_id = ?
        """,
        (order_id, user_id)
    ).fetchone()

def get_order_items(db, order_id):

    return db.execute(
        """
        SELECT * 
        FROM order_items 
        WHERE order_id = ?
        """, 
        (order_id,)
    ).fetchall()

def get_user_orders(db, user_id, limit=None):

    query = """
        SELECT o.*, SUM(oi.quantity) AS item_count
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.user_id = ?
        GROUP BY o.id
        ORDER BY o.created_at DESC
    """

    params = [user_id]

    # Add limit only if provided
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    orders = db.execute(query, tuple(params)).fetchall()

    return orders

def get_recent_orders(db):

    return db.execute(
        """
        SELECT id, full_name, total, status, created_at 
        FROM orders 
        ORDER BY created_at DESC 
        LIMIT 5
        """
    ).fetchall()

def get_order_by_id(db, order_id):

    return db.execute(
        """
        SELECT * 
        FROM orders 
        WHERE id = ?
        """, 
        (order_id,)
    ).fetchone()

def update_order_status(db, status, order_id):

    db.execute(
        """
        UPDATE orders 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        """, 
        (status, order_id)
    )

def count_orders(db, status=None):

    query = "SELECT COUNT(*) AS total FROM orders"
    params = []

    if status:
        query += " WHERE status = ?"
        params.append(status)

    return db.execute(query, tuple(params)).fetchone()["total"]