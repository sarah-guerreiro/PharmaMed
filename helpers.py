import sqlite3
from flask import g, url_for, session

# Open database upon request
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("pharmamed.db")
        g.db.row_factory = sqlite3.Row

        # Enable foreign keys
        g.db.execute("PRAGMA foreign_keys = ON")
        
    return g.db

# Build database structure
def init_db():
    db = get_db()
    with open("schema.sql") as schema_file:
        db.executescript(schema_file.read())
    db.commit()

# Close database after request
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def load_categories_menu():
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM categories")
    rows = cursor.fetchall()
    conn.close()

    categories_menu = {}

    # Create main categories
    for row in rows:
        if row["parent_id"] == 0:
            categories_menu[row["category_id"]] = {
                "category_data": row,
                "subcategories": []
            }
    
    # Attach subcategories
    for row in rows:
        if row["parent_id"] != 0 and row["parent_id"] in categories_menu:
            categories_menu[row["parent_id"]]["subcategories"].append(row)

    return categories_menu

def get_breadcrumb(category_id, db):
    
    breadcrumb = []
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,))
    current = cursor.fetchone()
    
    while current:
        breadcrumb.insert(0, current) 
        if current["parent_id"] == 0:
            break
        cursor.execute("SELECT * FROM categories WHERE category_id = ?", (current["parent_id"],))
        current = cursor.fetchone()
    
    return breadcrumb

def price_filter(args, query, query_params):

    min_price = args.get('min_price', type=float)
    max_price = args.get('max_price', type=float)

    if min_price is not None:
        query += " AND p.price >= ?"
        query_params.append(min_price)

    if max_price is not None:
        query += " AND p.price <= ?"
        query_params.append(max_price)

    return min_price, max_price, query, query_params

def count_products(cursor, query, query_params):
    
    count_query = f"SELECT COUNT(*) {query}"
    cursor.execute(count_query, query_params)
    
    return cursor.fetchone()[0]

def sorting(args, query):
    
    sort_option = args.get('sort', 'name_asc')
    
    if sort_option == 'name_desc':
        query += " ORDER BY p.name DESC"
    elif sort_option == 'price_asc':
        query += " ORDER BY p.price ASC"
    elif sort_option == 'price_desc':
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.name ASC" 
    
    return query

def pagination(args, query, query_params, products_per_page):
    
    page = args.get("page", 1, type=int)
    offset = (page - 1) * products_per_page
    query += " LIMIT ? OFFSET ?"
    query_params.extend([products_per_page, offset])

    return query, query_params, page

def get_cart_count():
    db = get_db()
    user_id = session.get('user_id')

    # Logged in user
    if user_id:
        return db_cart_count(db, user_id)

    # Anonymous user
    session_cart = session.get('cart', {})
    return sum(session_cart.values())

def db_cart_count(db, user_id):
    cart_count = db.execute("""SELECT SUM(quantity) as total FROM cart_items ci JOIN cart c ON ci.cart_id = c.id WHERE c.user_id = ?""", (user_id,)).fetchone()
    return cart_count["total"] if cart_count["total"] else 0

def add_to_session_cart(product_id, quantity):
    cart = session.get('cart', {})

    product_id = str(product_id)

    cart[product_id] = cart.get(product_id, 0) + quantity

    session['cart'] = cart
    session.modified = True

def add_to_db_cart(user_id, product_id, quantity):
    db = get_db()

    # Get or create new cart
    cart = db.execute("SELECT id FROM cart WHERE user_id = ?", (user_id,)).fetchone()

    if not cart:
        db.execute("INSERT INTO cart (user_id) VALUES (?)", (user_id,))
        db.commit()
        cart = db.execute("SELECT id FROM cart WHERE user_id = ?", (user_id,)).fetchone()

    cart_id = cart["id"]

    # Check if item exists
    item = db.execute("""SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?""", (cart_id, product_id)).fetchone()

    if item:
        db.execute("""UPDATE cart_items SET quantity = quantity + ? WHERE cart_id = ? AND product_id = ?""", (quantity, cart_id, product_id))
    else:
        db.execute("""INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)""", (cart_id, product_id, quantity))

    db.commit()

def get_cart_total(db, user_id=None):

    # Logged in user
    if user_id:
        result = db.execute("""SELECT SUM(ci.quantity * p.price) as total FROM cart_items ci JOIN cart c ON ci.cart_id = c.id JOIN products p ON ci.product_id = p.product_id 
                            WHERE c.user_id = ?""", (user_id,)).fetchone()

        return result["total"] or 0
    
    # Anonymous session
    else:
        session_cart = session.get("cart", {})
        total = 0

        for product_id, quantity in session_cart.items():
            product = db.execute("SELECT price FROM products WHERE product_id = ?", (product_id,)).fetchone()

            if product:
                total += product["price"] * quantity

        return total
    
def apply_cart_action(quantity, stock, action):
    if action == "increase":
        return min(quantity + 1, stock)

    elif action == "decrease":
        return quantity - 1 if quantity > 1 else 0

    elif action == "remove":
        return 0

    return quantity