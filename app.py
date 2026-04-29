import math, os, re, secrets, sqlite3

from datetime import datetime, timedelta, timezone
from flask import abort, flash, Flask, jsonify, render_template, redirect, request, session, url_for
from flask_login import LoginManager, login_required, login_user, current_user, logout_user, UserMixin
from helpers import get_db, close_db, load_categories_menu, get_breadcrumb, price_filter, count_products, sorting, pagination, get_cart_count, add_to_session_cart, add_to_db_cart, get_cart_total, apply_cart_action
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application
app = Flask(__name__)

# Get secret key
app.secret_key = "S0j0P1g9A2a4O9u0"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, first_name, last_name):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

# Load user
@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    if db is None: 
        return None
    
    user = db.execute("SELECT id, email, first_name, last_name FROM users WHERE id = ?",(user_id,)).fetchone()

    if user is None:
        return None

    return User(user["id"], user["email"], user["first_name"], user["last_name"])

# Close database after request
app.teardown_appcontext(close_db)

# Password pattern
PASSWORD_PATTERN = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$')

# Email pattern
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# Make variables available in all templates
@app.context_processor
def inject_globals():
    return {
        "categories_menu": load_categories_menu(),
        "cart_count": get_cart_count()
    }

@app.route("/")
def index():
    carousel_categories = [
        {"name": "Pain Relief", "id": 10, "image": "carousel/pain_relief_banner.png"},
        {"name": "Supplements", "id": 2, "image": "carousel/supplements_banner.png"},
        {"name": "Skincare", "id": 3, "image": "carousel/skincare_banner.png"}
    ]

    brands = [
        {"file": "centrum.png", "name": "Centrum"},
        {"file": "now.png", "name": "Now"},
        {"file": "uriage.png", "name": "Uriage"},
        {"file": "bioderma.png", "name": "Bioderma"},
        {"file": "avène.png", "name": "Avène"},
        {"file": "a-derma.png", "name": "A-Derma"},
        {"file": "neutrogena.png", "name": "Neutrogena"},
        {"file": "isdin.png", "name": "ISDIN"},
        {"file": "klorane.png", "name": "Klorane"},
        {"file": "elgydium.png", "name": "Elgydium"},
        {"file": "eludril.png", "name": "Eludril"},
        {"file": "medela.png", "name": "Medela"},
        {"file": "chicco.png", "name": "Chicco"},
        {"file": "philips_avent.png", "name": "Philips Avent"},
        {"file": "nan.png", "name": "Nan"},
        {"file": "advantage.png", "name": "Advantage"},
        {"file": "seresto.png", "name": "Seresto"},
        {"file": "adtab.png", "name": "AdTab"},
    ]

    db = get_db()
    cursor = db.cursor()

    # Get main categories name, id and image
    cursor = db.execute("""SELECT category_id, name, image_url FROM categories WHERE parent_id = 0""")
    main_categories = cursor.fetchall()

    return render_template("index.html", carousel_categories=carousel_categories, main_categories=main_categories, brands=brands)

@app.route("/products/<int:category_id>")
def display_category(category_id):
    db = get_db()
    cursor = db.cursor()

    # Get category/subcategory
    cursor = db.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,))
    category = cursor.fetchone()

    # Build breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], "url": url_for("display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(category["category_id"], db)
    ]

    # Get all subcategories in current category
    cursor = db.execute("SELECT category_id, name FROM categories WHERE parent_id = ?", (category_id,))
    subcategories = cursor.fetchall()
    category_ids = [category_id] + [subcategory["category_id"] for subcategory in subcategories]

    # Base query
    query = "FROM products p WHERE p.category_id IN ({})".format(",".join("?"*len(category_ids)))
    query_params = category_ids.copy() 
    
    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    selected_brands = request.args.getlist('brand')
    
    # Subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?"*len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Brand filter
    if selected_brands:
        query += " AND p.brand_id IN ({})".format(",".join("?"*len(selected_brands)))
        query_params.extend([int(brand) for brand in selected_brands])

    # Get brands based on filtered subcategories and brands
    cursor = db.execute(f"""SELECT DISTINCT b.brand_id, b.name FROM brands b JOIN products p ON b.brand_id = p.brand_id """ + query.replace("FROM products p", "") 
                   + """ORDER BY b.name""", query_params)
    brands = cursor.fetchall()

    # Apply min price and max price filter if set
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)
    
    # Count products
    total_products = count_products(cursor, query, query_params)

    # Sort products based on selected sorting option
    query = sorting(request.args, query)

    # Calculate the total number of pages
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    # Add pagination
    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Get products in current category/subcategory
    products_query = "SELECT p.name, p.price, p.image_url, p.product_id " + query
    cursor.execute(products_query, query_params)
    products = cursor.fetchall()

    # Count the number of active filters
    active_filters_count = (len(selected_subcategories) + len(selected_brands) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Route for url_for
    route_name = 'display_category'

    # Parameters for url_for
    base_params = {
        "category_id": category["category_id"],
        "subcategory": request.args.getlist('subcategory'),
        "brand": request.args.getlist('brand'),
        "min_price": request.args.get('min_price'),
        "max_price": request.args.get('max_price'),
        "sort": request.args.get('sort'),
    }

    # Get page type
    page_type = "category"

    return render_template("products.html", category=category, page_title=category["name"] if category else "Products", breadcrumb=breadcrumb, products=products, 
                           page=page, total_pages=total_pages, subcategories=subcategories, brands=brands, total_products=total_products,
                           active_filters_count=active_filters_count, route_name=route_name, base_params=base_params, page_type=page_type)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    cursor = db.cursor()

    # Get product info
    cursor.execute("""SELECT p.product_id, p.name, p.price, p.image_url, p.description, p.pack_size, p.category_id, b.brand_id, b.name as brand FROM products p 
                   JOIN brands b ON p.brand_id = b.brand_id WHERE p.product_id = ?""", (product_id,))

    product = cursor.fetchone()

    # Get breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], "url": url_for("display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(product["category_id"], db)
    ]

    # Get page type
    page_type = "product"

    return render_template("product_detail.html", product=product, breadcrumb=breadcrumb, page_type=page_type)

@app.route("/brands/<int:brand_id>")
def display_brand(brand_id):
    db = get_db()
    cursor = db.cursor()

    # Get brand
    cursor.execute("SELECT * FROM brands WHERE brand_id = ?", (brand_id,))
    brand = cursor.fetchone()

    if not brand:
        abort(404)

    # Base query
    query = "FROM products p WHERE p.brand_id = ?"
    query_params = [brand_id] 

    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    
    # Subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?"*len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Get subcategories based on selected brand
    cursor.execute(f"""SELECT DISTINCT c.category_id, c.name """ + query.replace("FROM products p", "FROM categories c JOIN products p ON p.category_id = c.category_id") 
                   + """ORDER BY c.name""", query_params)
    subcategories = cursor.fetchall()

    # Apply min price and max price filter if set
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)
    
    # Count products
    total_products = count_products(cursor, query, query_params)

    # Sort products based on selected sorting option 
    query = sorting(request.args, query)

    # Calculate the total number of pages
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    # Add pagination
    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Get products in current brand
    products_query = "SELECT p.name, p.price, p.image_url, p.product_id " + query
    cursor.execute(products_query, query_params)
    products = cursor.fetchall()

    # Count the number of active filters
    active_filters_count = (len(selected_subcategories) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Get breadcrumb list
    breadcrumb = [
        {"name": brand["name"], "url": None}
    ]

    # Route for url_for
    route_name = 'display_brand'

    # Parameters for url_for
    base_params = {
        "brand_id": brand["brand_id"],
        "min_price": request.args.get('min_price'),
        "max_price": request.args.get('max_price'),
        "sort": request.args.get('sort'),
    }

    # Get page type
    page_type = "brand"

    return render_template("products.html", brand=brand, page_title=brand["name"], subcategories=subcategories, page=page, total_pages=total_pages, total_products=total_products,
                            products=products, active_filters_count=active_filters_count, breadcrumb=breadcrumb, route_name=route_name, base_params=base_params, page_type=page_type)

@app.route("/search")
def search():
    db = get_db()
    cursor = db.cursor()

    search_query = request.args.get("search_query", "").strip()

    if not search_query:
        return redirect(url_for("index"))

    # Base query (search in product name, category name or brand name)
    query = """FROM products p JOIN categories C ON p.category_id = c.category_id JOIN brands b ON p.brand_id = b.brand_id 
    WHERE (p.name LIKE ? OR b.name LIKE ? OR c.name LIKE ?)"""
    query_params = [f"%{search_query}%"] * 3

    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    selected_brands = request.args.getlist('brand')
    
    # Subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?"*len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Brand filter
    if selected_brands:
        query += " AND p.brand_id IN ({})".format(",".join("?"*len(selected_brands)))
        query_params.extend([int(b) for b in selected_brands])

    # Price filter
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)

    # Get brands based on search query
    cursor.execute(f"""SELECT DISTINCT b.brand_id, b.name {query} ORDER BY b.name""", query_params)
    brands = cursor.fetchall()

    # Get subcategories based on search query
    cursor.execute(f"""SELECT DISTINCT c.category_id, c.name {query} ORDER BY b.name""", query_params)
    subcategories = cursor.fetchall()

    # Count products
    total_products = count_products(cursor, query, query_params)

    # Sorting
    query = sorting(request.args, query)

    # Pagination
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Fetch products
    products_query = "SELECT p.name, p.price, p.image_url, p.product_id " + query
    cursor.execute(products_query, query_params)
    products = cursor.fetchall()

    # Active filters count
    active_filters_count = (len(selected_subcategories) + len(selected_brands) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Route for url_for
    route_name = "search"

    # Parameters for url_for
    base_params = {
        "search_query": search_query,
        "subcategory": request.args.getlist('subcategory'),
        "brand": request.args.getlist('brand'),
        "min_price": request.args.get('max_price'),
        "max_price": request.args.get('max_price'),
        "sort": request.args.get('sort'),
    }

    # Get page type
    page_type = "search"

    return render_template("products.html", page_title=f"Search results for '{search_query}'", products=products, page=page, total_pages=total_pages, subcategories=subcategories,
                            brands=brands, total_products=total_products, active_filters_count=active_filters_count, route_name=route_name, base_params=base_params,
                            page_type=page_type)

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Get data from register form
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms = request.form.get("terms") is not None

        # List of errors
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
            return render_template("register.html", error=error, first_name=first_name, last_name=last_name, email=email, password=password, 
                                   confirm_password=confirm_password, terms=terms)

        # Hash password
        password_hash = generate_password_hash(password)

        try:
            # Connect to database
            db = get_db()

            # Insert user into database
            cursor = db.execute("""INSERT INTO users (first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?)""", (first_name, last_name, email, password_hash))

            user_id = cursor.lastrowid
            db.commit()

        # Check if email already exists
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        # Auto login after register
        login_user(User(user_id, email, first_name, last_name))
        flash("Account created successfully!", "success")
        return redirect(url_for("index"))
    
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # Get data from login form
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        # List of errors
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

        # Query database for user id, email and password
        cursor = db.execute("SELECT id, email, password_hash, first_name, last_name FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        # Check if email exists and password is correct
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

        # Remember which user has logged in
        login_user(User(user["id"], email, user["first_name"], user["last_name"]))

        # Redirect user to index page
        return redirect(url_for("index"))

    else:
        return render_template("login.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        # Get user email
        email = request.form.get("email", "").lower().strip()

        # List of errors
        error = {}

        # Input validation
        if not email:
            error["email"] = "Email is missing"

        if error:
            return render_template("forgot_password.html", error=error)

        # Connect to database
        db = get_db()

        # Query database for user
        cursor = db.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:

            # Generate token and expiry
            token = secrets.token_urlsafe(32)
            expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()

            # Update users table with generated token and expiry
            cursor.execute("""UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?""", (token, expiry, user["id"]))
            db.commit()

            # Show reset link
            reset_link = url_for("reset_password", token=token, _external=True)

            flash(f'<a href="{reset_link}">Click here to reset password</a>', "persistent")

        else:
            # For security
            flash("If that email exists, a reset link was generated.", "info")

        return redirect(url_for("login"))

    else:
        return render_template("forgot_password.html")
    
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    # Connect to database
    db = get_db()
 
    # Query for user data
    cursor = db.execute("SELECT * FROM users WHERE reset_token = ?", (token,))
    user = cursor.fetchone()

    if not user:
        flash("Invalid or expired token", "error")
        return redirect(url_for("login"))
    
    # Check expiry
    expiry = datetime.fromisoformat(user["reset_token_expiry"])
    if datetime.now(timezone.utc) > expiry:
        flash("Reset link expired", "error")
        return redirect(url_for("login"))

    if request.method == "POST":

        # Get data from form
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # List of errors
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

        # Update user password
        cursor.execute("""UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?""", (password_hash, user["id"]))
        db.commit()

        flash("Password reset successful! Please, login.", "success")
        return redirect(url_for("login"))

    else:
        return render_template("reset_password.html", token=token)

@app.route("/logout", methods=["POST"])
def logout():

    # Clear any open session
    logout_user()

    # Redirect user to index page
    return redirect(url_for("index"))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    
    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity', 1))

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

@app.route('/cart')
def cart():

    # Connect to database
    db = get_db()

    # Get user id
    user_id = current_user.id if current_user.is_authenticated else None

    # Logged in user
    if user_id:

        # Get cart items data
        rows = db.execute("""SELECT p.product_id, p.image_url, p.name, b.name as brand, p.pack_size, p.price, p.stock, ci.quantity FROM cart_items ci 
                                JOIN cart c ON ci.cart_id = c.id JOIN products p ON ci.product_id = p.product_id JOIN brands b ON p.brand_id = b.brand_id 
                                WHERE c.user_id = ?""", (user_id,)).fetchall()

        cart_items = []
        for row in rows:
            item = dict(row)
            item["image"] = item["image_url"]
            cart_items.append(item)
    
    # Anonymous session
    else:

        # Get session cart
        session_cart = session.get("cart", {})

        if not session_cart:
            return render_template("cart.html", items=[], total=0)

        placeholders = ",".join("?" * len(session_cart.keys()))

        # Get product data
        products = db.execute(f"""SELECT p.product_id, p.image_url, p.name, b.name as brand, p.pack_size, p.price, p.stock FROM products p JOIN brands b ON p.brand_id = b.brand_id 
                              WHERE p.product_id IN ({placeholders})""", tuple(session_cart.keys())).fetchall()

        # Build cart items list
        cart_items = []
        for product in products:
            p_id = str(product["product_id"])
            cart_items.append({
                "product_id": product["product_id"],
                "image": product["image_url"],
                "name": product["name"],
                "brand": product["brand"],
                "pack_size": product["pack_size"],
                "price": product["price"],
                "quantity": session_cart[p_id],
                "stock": product["stock"]
            })

    # Get total number of cart items
    total_items = get_cart_count()

    # Get item total price
    for item in cart_items:
        item["item_total"] = item["price"] * item["quantity"] 

    # Get cart total price
    cart_total = get_cart_total(db, user_id)

    return render_template("cart.html", cart_items=cart_items, total_items=total_items, cart_total=cart_total)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    
    # Connect to database
    db = get_db()
    
    try:
        product_id = int(request.form.get("product_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False}), 400
    
    action = request.form.get("action") 
    if action not in ["increase", "decrease", "remove"]:
        return jsonify({"success": False}), 400
    
    # Get user id
    user_id = current_user.id if current_user.is_authenticated else None

    # Initialize updated cart item quantity, stock and item total
    updated_quantity = 0
    stock = 0
    item_total = 0

    # Logged in user
    if user_id:

        # Get cart
        cart = db.execute("SELECT id FROM cart WHERE user_id = ?", (user_id,)).fetchone()
        
        if not cart:
            return jsonify({"success": False, "message": "Cart not found"}), 400
        
        cart_id = cart["id"]

        item = db.execute("""SELECT ci.quantity, p.stock, p.price FROM cart_items ci JOIN products p ON ci.product_id = p.product_id WHERE ci.cart_id = ? 
                            AND ci.product_id = ?""", (cart_id, product_id)).fetchone()

        if not item:
            return jsonify({"success": False, "message": "Item not in cart"}), 400

        # Get item quantity, stock and price
        quantity = item["quantity"]
        stock = item["stock"]
        price = item["price"]

        # Get item updated quantity
        updated_quantity = apply_cart_action(quantity, stock, action)
        
        if updated_quantity > 0:
            db.execute("""UPDATE cart_items SET quantity = ? WHERE cart_id = ? AND product_id = ?""", (updated_quantity, cart_id, product_id))
        else:
            db.execute("""DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?""", (cart_id, product_id))  
        
        db.commit()

    # Anonymous session
    else:

        # Get session cart
        cart = session.get("cart", {})
        p_id = str(product_id)

        if p_id not in cart:
            return jsonify({"success": False, "message": "Item not in cart"}), 400

        item = db.execute("SELECT stock, price FROM products WHERE product_id = ?", (product_id,)).fetchone()

        if not item:
            return jsonify({"success": False, "message": "Product not found"}), 400
        
        # Get item quantity, stock and price
        quantity = cart[p_id]
        stock = item["stock"]
        price = item["price"]

        # Get item updated quantity
        updated_quantity = apply_cart_action(quantity, stock, action)

        if updated_quantity > 0:
            cart[p_id] = updated_quantity
        else:
            del cart[p_id]

        session["cart"] = cart
        session.modified = True     

    # Get item total price
    item_total = price * updated_quantity

    # Get cart total price
    cart_total = get_cart_total(db, user_id)

    # Return updated data
    return jsonify({
        "success": True,
        "cart_count": get_cart_count(),
        "product_id": product_id,
        "updated_quantity": updated_quantity,
        "item_total": item_total,
        "cart_total": cart_total,
        "stock": stock
    })

@app.route("/account")
@login_required
def account_home():

    # Connect to database
    db = get_db()

    # Get user first name
    user = db.execute("SELECT first_name FROM users WHERE id = ?", (current_user.id,)).fetchone()
    first_name = user["first_name"]

    return render_template("account/dashboard.html", first_name=first_name, active_page=None)

@app.route("/account/profile", methods=["GET", "POST"])
@login_required
def profile():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = db.execute("SELECT first_name, last_name FROM users WHERE id = ?", (current_user.id,)).fetchone()

    # Get user addresses
    addresses = db.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,)).fetchall()

    # List of error
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

        # Update DB if first name or last name changed
        if (first_name != user["first_name"] or last_name != user["last_name"]):
            db.execute("UPDATE users SET first_name = ?, last_name = ? WHERE id = ?", (first_name, last_name, current_user.id))
            db.commit()

            flash("Profile updated successfully!", "success")

            # Get updated names
            user = db.execute("SELECT first_name, last_name FROM users WHERE id = ?", (current_user.id,)).fetchone()

        return redirect(url_for('profile'))
    
    else:
        return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], profile_error=error, addresses=addresses)

@app.route("/account/addresses", methods=["GET", "POST"])
@login_required
def addresses():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = db.execute("SELECT first_name, last_name FROM users WHERE id = ?", (current_user.id,)).fetchone()

    # Get user addresses
    addresses = db.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,)).fetchall()

    # List of errors
    add_error = {}

    if request.method == "POST":

        # Get data from address form
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
            addresses = db.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,)).fetchall()

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
            db.execute("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (current_user.id,))

        # Auto-set first address to default
        existing_addresses = db.execute("SELECT COUNT(*) FROM addresses WHERE user_id = ?", (current_user.id,)).fetchone()[0]

        if existing_addresses == 0:
            is_default = 1

        # Insert new address into database
        db.execute("""INSERT INTO addresses (user_id, full_name, address_line, postal_code, city, country, is_default) VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                   (current_user.id, full_name, address_line, postal_code, city, country, is_default))

        db.commit()

        flash("Address added successfully!", "success")
        return redirect(url_for('addresses'))

    else:     
        return render_template("account/profile.html", active_page="profile", first_name=user["first_name"], last_name=user["last_name"], addresses=addresses, add_error=add_error)

@app.route("/account/addresses/edit", methods=["POST"])
@login_required
def edit_address():

    # Connect to database
    db = get_db()

    # Get user current first and last names
    user = db.execute("SELECT first_name, last_name FROM users WHERE id = ?", (current_user.id,)).fetchone()

    # Get data from edit address form
    address_id = request.form.get("address_id")
    full_name = request.form.get("full_name", "").strip().title()
    address_line = request.form.get("address_line", "").strip().title()
    postal_code = request.form.get("postal_code", "").strip()
    city = request.form.get("city", "").strip().title()
    country = request.form.get("country", "").strip().title()

    # List of errors
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
        addresses = db.execute("SELECT * FROM addresses WHERE user_id = ?", (current_user.id,)).fetchall()

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
    db.execute("""UPDATE addresses SET full_name = ?, address_line = ?, postal_code = ?, city = ?, country = ? WHERE id = ? AND user_id = ?""", 
               (full_name, address_line, postal_code, city, country, address_id, current_user.id))

    db.commit()

    flash("Address updated!", "success")
    return redirect(url_for("addresses"))

@app.route("/account/addresses/delete", methods=["POST"])
@login_required
def delete_address():

    # Connect to database
    db = get_db()

    # Get user address id
    address_id = request.form.get("address_id")

    # Delete address from database
    db.execute("""DELETE FROM addresses WHERE id = ? AND user_id = ?""", (address_id, current_user.id))

    db.commit()

    flash("Address deleted!", "success")
    return redirect(url_for("addresses"))

@app.route("/account/orders")
@login_required
def orders():

    return render_template("account/orders.html", active_page="orders")

@app.route("/account/security", methods=["GET", "POST"])
@login_required
def change_password():

    # Connect to database
    db = get_db()

    if request.method == "POST":

        # Get data from form
        current_password = request.form.get("current_password", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # List of errors
        error = {}

        # Get current password
        user = db.execute("SELECT password_hash FROM users WHERE id = ?", (current_user.id,)).fetchone()

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
        db.execute("""UPDATE users SET password_hash = ? WHERE id = ?""", (password_hash, current_user.id))
        db.commit()

        flash("Password updated successfully!", "success")
        return redirect(url_for("change_password"))

    else:
        return render_template("account/security.html", active_page="security")