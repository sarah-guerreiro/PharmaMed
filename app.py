import math, os, sqlite3

from flask import Flask, g, render_template, request

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
    return render_template("layout.html")

@app.route("/category/<int:category_id>")
def display_category(category_id):
    conn = sqlite3.connect("pharmamed.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get category/subcategory name for page title
    cursor.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,))
    category = cursor.fetchone()

    # Build breadcrumb list
    breadcrumb = []
    current = category

    while current:
        breadcrumb.insert(0, current)
        if current["parent_id"] == 0:
            break
        cursor.execute("SELECT * FROM categories WHERE category_id = ?", (current["parent_id"],))
        current = cursor.fetchone()

    # Set the number of products per page
    page = request.args.get("page", 1, type=int)
    products_per_page = 16
    offset = (page - 1) * products_per_page

    # Get all subcategories
    cursor.execute("SELECT category_id FROM categories WHERE parent_id = ?", (category_id,))
    subcategories = cursor.fetchall()
    category_ids = [category_id] + [subcategory["category_id"] for subcategory in subcategories]

    # Count products from each category
    cursor.execute(f"""SELECT COUNT(*) FROM products WHERE category_id IN ({','.join('?'*len(category_ids))})""", category_ids)
    total_products = cursor.fetchone()[0]

    # Calculate the total number of pages
    total_pages = math.ceil(total_products / products_per_page)

    # Get products for that category/subcategory
    cursor.execute(f"""SELECT name, price, image_url FROM products WHERE category_id IN ({','.join('?'*len(category_ids))}) LIMIT ? OFFSET ?""", category_ids + [products_per_page, offset])
    products = cursor.fetchall()

    conn.close()

    return render_template("category_products.html", category=category, category_name=category["name"] if category else "Products", breadcrumb=breadcrumb, products=products, page=page, total_pages=total_pages)