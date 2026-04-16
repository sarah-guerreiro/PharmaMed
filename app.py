import math, os, re, secrets, sqlite3

from datetime import datetime, timedelta, timezone
from flask import abort, flash, Flask, jsonify, render_template, redirect, request, session, url_for
from helpers import close_db, load_categories_menu, get_breadcrumb, price_filter, count_products, sorting, pagination, cart_count, add_to_session_cart, add_to_db_cart
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application
app = Flask(__name__)

# Close database after request
app.teardown_appcontext(close_db)

# Get secret key
app.secret_key = "S0j0P1g9A2a4O9u0"

# Password pattern
PASSWORD_PATTERN = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$')

# Email pattern
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# Make variables available in all templates
@app.context_processor
def inject_globals():
    return {
        "categories_menu": load_categories_menu(),
        "cart_count": cart_count()
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

    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get main categories name, id and image
    cursor.execute("""SELECT category_id, name, image_url FROM categories WHERE parent_id = 0""")
    main_categories = cursor.fetchall()

    return render_template("index.html", carousel_categories=carousel_categories, main_categories=main_categories, brands=brands)

@app.route("/products/<int:category_id>")
def display_category(category_id):
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get category/subcategory
    cursor.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,))
    category = cursor.fetchone()

    # Build breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], "url": url_for("display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(category["category_id"], conn)
    ]

    # Get all subcategories in current category
    cursor.execute("SELECT category_id, name FROM categories WHERE parent_id = ?", (category_id,))
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
    cursor.execute(f"""SELECT DISTINCT b.brand_id, b.name FROM brands b JOIN products p ON b.brand_id = p.brand_id """ + query.replace("FROM products p", "") 
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

    conn.close()

    return render_template("products.html", category=category, page_title=category["name"] if category else "Products", breadcrumb=breadcrumb, products=products, 
                           page=page, total_pages=total_pages, subcategories=subcategories, brands=brands, total_products=total_products,
                           active_filters_count=active_filters_count, route_name=route_name, base_params=base_params, page_type=page_type)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get product info
    cursor.execute("""
        SELECT p.product_id, p.name, p.price, p.image_url, p.description, p.pack_size, p.category_id, b.brand_id, b.name as brand 
        FROM products p
        JOIN brands b ON p.brand_id = b.brand_id
        WHERE p.product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    # Get breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], "url": url_for("display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(product["category_id"], conn)
    ]

    # Get page type
    page_type = "product"

    return render_template("product_detail.html", product=product, breadcrumb=breadcrumb, page_type=page_type)

@app.route("/brands/<int:brand_id>")
def display_brand(brand_id):
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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

    conn.close()

    return render_template("products.html", brand=brand, page_title=brand["name"], subcategories=subcategories, page=page, total_pages=total_pages, total_products=total_products,
                            products=products, active_filters_count=active_filters_count, breadcrumb=breadcrumb, route_name=route_name, base_params=base_params, page_type=page_type)

@app.route("/search")
def search():
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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

    conn.close()

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
            conn = sqlite3.connect("pharmamed.db")
            cursor = conn.cursor()

            # Insert user into database
            cursor.execute("""INSERT INTO users (first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?)""", (first_name, last_name, email, password_hash))

            user_id = cursor.lastrowid

            conn.commit()

        # Check if email already exists
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        finally:
            conn.close()

        # Auto login after register
        session["user_id"] = user_id
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
        
        # Clear any open session
        session.clear()
  
        # Connect to database
        conn = sqlite3.connect("pharmamed.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query database for user and password
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()


        # Close database
        conn.close()

        # Check if email exists and password is correct
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

        # Remember which user has logged in
        session["user_id"] = user["id"]

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
        conn = sqlite3.connect("pharmamed.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query database for user
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:

            # Generate token and expiry
            token = secrets.token_urlsafe(32)
            expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()

            # Update users table with generated token and expiry
            cursor.execute("""UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?""", (token, expiry, user["id"]))
            conn.commit()

            # Show reset link
            reset_link = url_for("reset_password", token=token, _external=True)

            flash(f'<a href="{reset_link}">Click here to reset password</a>', "persistent")

        else:
            # For security
            flash("If that email exists, a reset link was generated.", "info")

    
        # Close database
        conn.close()

        return redirect(url_for("login"))

    else:
        return render_template("forgot_password.html")
    
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    # Connect to database
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try: 
        # Query for user data
        cursor.execute("SELECT * FROM users WHERE reset_token = ?", (token,))
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
                error["confirm_password"] = "Passwords must match"
            
            if error:
                return render_template("reset_password.html", token=token, error=error, password=password, confirm_password=confirm_password)

            # Hash password
            password_hash = generate_password_hash(password)

            # Update user password
            cursor.execute("""UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?""", (password_hash, user["id"]))
            conn.commit()

            flash("Password reset successful! Please, login.", "success")
            return redirect(url_for("login"))

        else:
            return render_template("reset_password.html", token=token)

    finally:
        # Close database
        conn.close()

@app.route("/logout", methods=["POST"])
def logout():

    # Clear any open session
    session.clear()

    # Redirect user to index page
    return redirect(url_for("index"))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    user_id = session.get('user_id')

    if user_id:
        add_to_db_cart(user_id, product_id, quantity)
    else:
        add_to_session_cart(product_id, quantity)

    return jsonify({
        "cart_count": cart_count()
    })