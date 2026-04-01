import math, os, sqlite3

from flask import Flask, g, render_template, request, url_for
from helpers import get_breadcrumb

# Configure application
app = Flask(__name__)

# Database connection
DATABASE = "pharmamed.db"

# Open database upon request
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
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
@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# Make categories menu available in all templates
@app.context_processor
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

    return dict(categories_menu=categories_menu)

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

    # Get breadcrumb list
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

    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    selected_brands = request.args.getlist('brand')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    # Base query
    query = "FROM products p WHERE p.category_id IN ({})".format(",".join("?"*len(category_ids)))
    query_params = category_ids.copy() 

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
    if min_price is not None:
        query += " AND p.price >= ?"
        query_params.append(min_price)

    if max_price is not None:
        query += " AND p.price <= ?"
        query_params.append(max_price)
    
    # Count products
    count_query = "SELECT COUNT(*) " + query
    cursor.execute(count_query, query_params)
    total_products = cursor.fetchone()[0]

    # Get selected sorting option
    sort_option = request.args.get('sort', 'name_asc')

    # Sort products based on selected sorting option
    if sort_option == 'name_desc':
        query += " ORDER BY p.name DESC"
    elif sort_option == 'price_asc':
        query += " ORDER BY p.price ASC"
    elif sort_option == 'price_desc':
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.name ASC" 

    # Set the number of products per page
    page = request.args.get("page", 1, type=int)
    products_per_page = 16
    offset = (page - 1) * products_per_page

    # Calculate the total number of pages
    total_pages = math.ceil(total_products / products_per_page)

    # Add LIMIT and OFFSET for pagination
    query += " LIMIT ? OFFSET ?"
    query_params.extend([products_per_page, offset])

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
        "max_price": request.args.get('max_price')
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

    return render_template("product_detail.html", product=product, breadcrumb=breadcrumb)

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

    # Get selected filters from the URL query parameters
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    # Base query
    query = "FROM products p WHERE p.brand_id = ?"
    query_params = [brand_id] 

    # Apply min price and max price filter if set
    if min_price is not None:
        query += " AND p.price >= ?"
        query_params.append(min_price)

    if max_price is not None:
        query += " AND p.price <= ?"
        query_params.append(max_price)
    
    # Count products
    count_query = "SELECT COUNT(*) " + query
    cursor.execute(count_query, query_params)
    total_products = cursor.fetchone()[0]

    # Get selected sorting option
    sort_option = request.args.get('sort', 'name_asc')

    # Sort products based on selected sorting option 
    if sort_option == 'name_desc':
        query += " ORDER BY p.name DESC"
    elif sort_option == 'price_asc':
        query += " ORDER BY p.price ASC"
    elif sort_option == 'price_desc':
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.name ASC"

    # Set the number of products per page
    page = request.args.get("page", 1, type=int)
    products_per_page = 16
    offset = (page - 1) * products_per_page

    # Calculate the total number of pages
    total_pages = math.ceil(total_products / products_per_page)

    # Add LIMIT and OFFSET for pagination
    query += " LIMIT ? OFFSET ?"
    query_params.extend([products_per_page, offset])

    # Get products in current category/subcategory
    products_query = "SELECT p.name, p.price, p.image_url, p.product_id " + query
    cursor.execute(products_query, query_params)
    products = cursor.fetchall()

    # Count the number of active filters
    active_filters_count = ((1 if min_price is not None else 0) + (1 if max_price is not None else 0))

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
        "max_price": request.args.get('max_price')
    }

    # Get page type
    page_type = "brand"

    conn.close()

    return render_template("products.html", brand=brand, page_title=brand["name"], products=products, page=page, total_pages=total_pages, total_products=total_products, 
                           active_filters_count=active_filters_count, breadcrumb=breadcrumb, route_name=route_name, base_params=base_params, page_type=page_type)