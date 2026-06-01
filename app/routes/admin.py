import math
import os
import secrets

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from app.services.admin_service import get_admin_by_username

from app.services.order_service import (
    get_recent_orders,
    get_order_by_id,
    get_order_items,
    update_order_status,
    count_orders
)

from app.services.product_service import (
    get_brands,
    get_categories,
    get_subcategories,
    create_product,
    get_product_by_id,
    update_product,
    deactivate_product_by_id,
    activate_product_by_id,
    count_low_stock_products,
    count_out_of_stock_products,
    count_inactive_products,
    get_low_stock_products
)

from app.utils.db import get_db
from app.utils.decorators import admin_required
from app.utils.query_helpers import pagination
from app.utils.uploads import allowed_file

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/login", methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        # Get login form data
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Error dictionary
        error = {}

        # Input validation
        if not username:
            error["username"] = "Username is missing"

        if not password:
            error["password"] = "Password is missing"

        if error:
            return render_template("admin_login.html", error=error, username=username)
  
        # Connect to database
        db = get_db()

        # Get admin details
        admin = get_admin_by_username(db, username)

        # Check if email exists and password is correct
        if admin is None or not check_password_hash(admin["password_hash"], password):
            flash("Invalid username or password", "error")
            return redirect(url_for("admin.admin_login"))

        else:
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin.admin_home"))

    else:
        return render_template("admin_login.html")

@admin_bp.route("/logout", methods=["POST"])
def admin_logout():

    # Clear any open session
    session.pop("admin_id", None)
    session.pop("admin_username", None)

    return redirect(url_for("admin.admin_login"))

@admin_bp.route("/")
@admin_required
def admin_home():

    # Connect to database
    db = get_db()

    # Get total number of orders
    total_orders = count_orders(db)

    # Get total number of pending orders
    pending_orders = count_orders(db, status="pending")

    # Get total number of low stock products
    low_stock_count = count_low_stock_products(db)

    # Get recent orders
    recent_orders = get_recent_orders(db)

    # Get low stock products
    low_stock_products = get_low_stock_products(db, limit=10)

    return render_template("admin/dashboard.html", total_orders=total_orders, pending_orders=pending_orders, low_stock_count=low_stock_count, recent_orders=recent_orders,
                           low_stock_products=low_stock_products)

@admin_bp.route("/products")
@admin_required
def admin_products():

    # Connect to database
    db = get_db()

    # Get search query, sorting parameter and direction
    search_query = request.args.get("search_query", "").strip()
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "asc")

    # Sorting mapping
    allowed_sorts = {
        "id": "p.product_id",
        "name": "p.name",
        "brand": "b.name",
        "category": "COALESCE(parent.name, c.name)",
        "subcategory": "c.name",
        "price": "p.price",
        "stock": "p.stock"
    }

    # Get sorting column
    sort_column = allowed_sorts.get(sort, "p.product_id")

    # Sorting direction validation
    if direction not in ["asc", "desc"]:
        direction = "asc"

    query_params = []

    # Base query
    query = """
    FROM products p 
    JOIN brands b ON p.brand_id = b.brand_id 
    JOIN categories c ON p.category_id = c.category_id 
    LEFT JOIN categories parent ON c.parent_id = parent.category_id 
    WHERE is_active = 1
    """
    
    if search_query:
        query += """ AND (p.name LIKE ? OR b.name LIKE ? OR c.name LIKE ? OR parent.name LIKE ?)"""
        search_term = f"%{search_query}%"
        query_params = [search_term] * 4

    # Main query
    main_query = """SELECT p.product_id, p.name, p.pack_size, p.price, p.stock, b.name AS brand_name, c.name AS assigned_category, parent.name AS parent_category """ + query

    # Count products
    count_query = """SELECT COUNT(*) AS total """ + query
    total_products = db.execute(count_query, query_params).fetchone()["total"]

    # Calculate the total number of pages
    products_per_page = 10
    total_pages = math.ceil(total_products / products_per_page)

    # Add sorting 
    main_query += f" ORDER BY {sort_column} {direction.upper()}"

    # Add pagination
    main_query, query_params, page = pagination(request.args, main_query, query_params, products_per_page)

    # Get products
    products = db.execute(main_query, query_params).fetchall()

    # Preserve params in pagination and sorting 
    base_params = {
        "search_query": search_query,
        "sort": sort,
        "direction": direction
    }
    
    return render_template("admin/products.html", active_page="products", search_query=search_query, products=products, total_pages=total_pages, page=page, base_params=base_params,
                           sort=sort, direction=direction)

@admin_bp.route("/products/add", methods=['GET', 'POST'])
@admin_required
def add_product():

    # Connect to database
    db = get_db()

    # Get brands
    brands = get_brands(db)

    # Get categories
    categories = get_categories(db)

    # Get subcategories
    subcategories = get_subcategories(db)

    # Preserve params in pagination, sorting and filter links
    source = request.form if request.method == "POST" else request.args

    base_params = {
        "page": source.get("page", 1),
        "search_query": source.get("search_query", ""),
        "sort": source.get("sort", "id"),
        "direction": source.get("direction", "asc"),
    }

    # Error dictionary
    error = {}
    
    if request.method == 'POST':

        # Get form data
        product_name = request.form.get("product_name", "").strip()
        description = request.form.get("description", "").strip()
        brand = request.form.get("brand")
        category = request.form.get("category")
        subcategory = request.form.get("subcategory")
        price = request.form.get("price", "").strip()
        stock = request.form.get("stock", "").strip()
        pack_size = request.form.get("pack_size", "").strip()
        image = request.files.get("image")

        # Input validation
        if not product_name:
            error["product_name"] = "Product name is required"

        if not description:
            error["description"] = "A short product description is required"

        if not brand:
            error["brand"] = "Please select a brand"

        if not category:
            error["category"] = "Please select a category"

        subcat = db.execute(
            """SELECT category_id 
            FROM categories 
            WHERE parent_id = ?
            """, 
            (category,)
        ).fetchall()

        if subcat and not subcategory:
            error["subcategory"] = "Please select a subcategory"

        try:
            price = float(price)

            if price < 0:
                error["price"] = "Price cannot be negative"

        except ValueError:
            error["price"] = "Invalid price"
        
        try:
            stock = int(stock)

            if stock < 0:
                error["stock"] = "Stock cannot be negative"

        except ValueError:
            error["stock"] = "Invalid stock value"
        
        if not pack_size:
            error["pack_size"] = "Pack size is required"

        if image and image.filename:
            if not allowed_file(image.filename):
                error["image"] = "Invalid image format"

        if error:
            return render_template("admin/product_form.html", active_page="products", brands=brands, categories=categories, subcategories=subcategories, base_params=base_params, error=error,
                                   product_name=product_name, description=description, brand=brand, category=category, subcategory=subcategory, price=price, stock=stock, pack_size=pack_size)
        
        # Get product category
        final_category_id = subcategory if subcategory else category

        # Get product image
        image_url = "images/products/Default.png"

        if image and image.filename:
            filename = f"{secrets.token_hex(4)}_{secure_filename(image.filename)}"
            image_path = os.path.join(current_app.static_folder,"images/products", filename)
            image.save(image_path)
            image_url = f"images/products/{filename}"

        # Insert new product into database
        create_product(
            db=db, 
            product_name=product_name, 
            description=description, 
            final_category_id=final_category_id, 
            brand=brand, 
            pack_size=pack_size, 
            price=price, 
            stock=stock, 
            image_url=image_url
        )

        db.commit()

        flash("Product added successfully", "success")
        return redirect(url_for("admin.admin_products", **base_params))

    else:
        return render_template("admin/product_form.html", active_page="products", brands=brands, categories=categories, subcategories=subcategories, base_params=base_params, error=error)

@admin_bp.route("/products/<int:product_id>/edit", methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):

    # Connect to database
    db = get_db()

    # Set edit mode
    mode = "edit"

    # Get context and active page
    context = request.args.get("context", "")
    active_page = "inventory" if context == "inventory" else "products"

    if context not in ["catalog", "inventory"]:
        abort(400)

    # Get product
    product = get_product_by_id(db, product_id)

    if not product:
        abort(404)

    # Get brands
    brands = get_brands(db)

    # Get categories
    categories = get_categories(db)

    # Get subcategories
    subcategories = get_subcategories(db)

    # Preserve params in pagination, sorting and filter links
    source = request.form if request.method == "POST" else request.args

    base_params = {
        "page": source.get("page", 1),
        "search_query": source.get("search_query", ""),
        "sort": source.get("sort", "id"),
        "direction": source.get("direction", "asc"),
    }

    if context == "inventory":
        base_params["filter_option"] = source.get("filter_option", "all")

    # Error dictionary
    error = {}

    if request.method == "POST":

        # Get form data
        product_name = request.form.get("product_name", "").strip()
        description = request.form.get("description", "").strip()
        brand = request.form.get("brand")
        category = request.form.get("category")
        subcategory = request.form.get("subcategory")
        price = request.form.get("price", "").strip()
        stock = request.form.get("stock", "").strip()
        pack_size = request.form.get("pack_size", "").strip()
        image = request.files.get("image")

        # Catalog context
        if context == "catalog":
            stock = product["stock"]

            # Input validation
            if not product_name:
                error["product_name"] = "Product name is required"

            if not description:
                error["description"] = "A short product description is required"

            if not brand:
                error["brand"] = "Please select a brand"

            if not category:
                error["category"] = "Please select a category"

            subcat = db.execute(
                """
                SELECT category_id 
                FROM categories 
                WHERE parent_id = ?
                """, 
                (category,)
            ).fetchall()

            if subcat and not subcategory:
                error["subcategory"] = "Please select a subcategory"

            if not price:
                error["price"] = "Price is required"
            
            else:
                try:
                    price = float(price)

                    if price < 0:
                        error["price"] = "Price cannot be negative"

                except ValueError:
                    error["price"] = "Invalid price"
            
            
            if not pack_size:
                error["pack_size"] = "Pack size is required"

            if image and image.filename:
                if not allowed_file(image.filename):
                    error["image"] = "Invalid image format"

            if error:
                return render_template("admin/product_form.html", active_page=active_page, product=product, brands=brands, categories=categories, subcategories=subcategories, mode=mode, context=context, 
                                       base_params=base_params, error=error, product_name=product_name, description=description, brand=brand, category=category, subcategory=subcategory, price=price, stock=stock, 
                                       pack_size=pack_size)

            if image and image.filename:
                filename = f"{secrets.token_hex(4)}_{secure_filename(image.filename)}"
                image_path = os.path.join(current_app.static_folder,"images/products", filename)
                image.save(image_path)
                image_url = f"images/products/{filename}"

            else:
                image_url = product["image_url"]

        elif context == "inventory":
            product_name = product["name"]
            description = product["description"]
            brand = product["brand_id"]

            if product["parent_id"] == 0:
                category = product["category_id"]
                subcategory = None

            else:
                category = product["parent_id"]
                subcategory = product["category_id"]

            price = product["price"]
            pack_size = product["pack_size"]
            image_url = product["image_url"]

            # Input validation
            if not stock:
                error["stock"] = "Stock is required"
            
            else:
                try:
                    stock = int(stock)

                    if stock < 0:
                        error["stock"] = "Stock cannot be negative"

                except ValueError:
                    error["stock"] = "Invalid stock value"

            if error:
                return render_template("admin/product_form.html", active_page=active_page, product=product, brands=brands, categories=categories, subcategories=subcategories, mode=mode, context=context, 
                                       base_params=base_params, error=error, product_name=product_name, description=description, brand=brand, category=category, subcategory=subcategory, price=price, stock=stock, 
                                       pack_size=pack_size)

        # Get product category
        final_category_id = subcategory if subcategory else category

        # Update database
        update_product(
            db=db,
            product_name=product_name, 
            description=description, 
            brand=brand, 
            final_category_id=final_category_id, 
            pack_size=pack_size, 
            price=price, 
            stock=stock, 
            image_url=image_url, 
            product_id=product_id
        )

        db.commit()

        flash("Product updated successfully", "success")
        return redirect(url_for("admin.admin_inventory" if context == "inventory" else "admin.admin_products", **base_params))
    
    else:
        return render_template("admin/product_form.html", active_page=active_page, product=product, brands=brands, categories=categories, subcategories=subcategories, mode=mode, context=context, base_params=base_params, error=error)

@admin_bp.route("/products/<int:product_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_product(product_id):

    # Connect to database
    db = get_db()

    # Update active state
    deactivate_product_by_id(db=db, product_id=product_id)

    db.commit()

    flash("Product deactivated successfully", "success")
    return redirect(request.referrer)

@admin_bp.route("/orders")
@admin_required
def admin_orders():

    # Connect to database
    db = get_db()

    # Get total number of pending orders
    pending_orders_count = count_orders(db, status="pending")

    # Get total number of processing orders
    processing_orders_count = count_orders(db, status="processing")

    # Get total number of shipped orders
    shipped_orders_count = count_orders(db, status="shipped")

    # Get total number of delivered orders
    delivered_orders_count = count_orders(db, status="delivered")

    # Get total number of cancelled orders
    cancelled_orders_count = count_orders(db, status="cancelled")

    # Get sorting parameter and direction, and filter option
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "asc")
    filter_option = request.args.get("filter_option", "all")

    # Sorting mapping
    allowed_sorts = {
        "id": "id",
        "full_name": "full_name",
        "date": "created_at",
        "total": "total",
    }

    # Get sorting column
    sort_column = allowed_sorts.get(sort, "id")

    # Sorting direction validation
    if direction not in ["asc", "desc"]:
        direction = "asc"

    # FROM clause
    from_query = "FROM orders"

    # Main query
    query = """SELECT id, full_name, total, status, created_at """ + from_query

    conditions = []
    query_params = []

    # Filter
    if filter_option == "pending":
        conditions.append("status = 'pending'")

    elif filter_option == "processing":
        conditions.append("status = 'processing'")

    elif filter_option == "shipped":
        conditions.append("status = 'shipped'")

    elif filter_option == "delivered":
        conditions.append("status = 'delivered'")
    
    elif filter_option == "cancelled":
        conditions.append("status = 'cancelled'")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Count products
    count_query = """SELECT COUNT(*) AS total """ + from_query

    if conditions:
        count_query += " WHERE " + " AND ".join(conditions)

    total_orders = db.execute(count_query, query_params).fetchone()["total"]

    # Calculate the total number of pages
    orders_per_page = 10
    total_pages = math.ceil(total_orders / orders_per_page)

    # Add sorting 
    query += f" ORDER BY {sort_column} {direction.upper()}"

    # Add pagination
    query, query_params, page = pagination(request.args, query, query_params, orders_per_page)

    # Get products
    orders = db.execute(query, query_params).fetchall()

    # Preserve params in pagination, sorting and filter links
    base_params = {
        "filter_option": filter_option,
        "sort": sort,
        "direction": direction
    }
    
    return render_template("admin/orders.html", active_page="orders", pending_orders_count=pending_orders_count, processing_orders_count=processing_orders_count, shipped_orders_count=shipped_orders_count,
                           delivered_orders_count=delivered_orders_count, cancelled_orders_count=cancelled_orders_count, orders=orders, total_pages=total_pages, page=page, base_params=base_params,
                           sort=sort, direction=direction, filter_option=filter_option)

@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
@admin_required
def admin_order_details(order_id):

    # Connect to database
    db = get_db()

    # Get order
    order = get_order_by_id(db, order_id)

    if not order:
        abort(404)

    # Get order items
    order_items = get_order_items(db, order_id)

    # Preserve params in pagination, sorting and filter links
    source = request.form if request.method == "POST" else request.args

    base_params = {
        "page": source.get("page", 1),
        "sort": source.get("sort", "id"),
        "direction": source.get("direction", "asc"),
        "filter_option": source.get("filter_option", "all"),
    }

    if request.method == "POST":

        # Get status
        status = request.form.get("status")

        # Allowed statuses
        allowed_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]

        # Status validation
        if status not in allowed_statuses:
            flash("Invalid order status", "danger")
            return redirect(url_for("admin.admin_order_details", order_id=order_id, **base_params))

        # Update database
        update_order_status(
            db=db,
            status=status, 
            order_id=order_id
        )

        db.commit()

        flash("Order status updated successfully", "success")
        return redirect(url_for("admin.admin_orders", **base_params))

    else:
        return render_template("admin/order_details.html", order=order, order_items=order_items, base_params=base_params)

@admin_bp.route("/inventory")
@admin_required
def admin_inventory():

    # Connect to database
    db = get_db()

    # Get total number of low stock products
    low_stock_count = count_low_stock_products(db)

    # Get total number of out of stock products
    no_stock_count = count_out_of_stock_products(db)

    # Get total number of inactive products
    inactive_count = count_inactive_products(db)

    # Get search query, sorting parameter and direction, and filter option
    search_query = request.args.get("search_query", "").strip()
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "asc")
    filter_option = request.args.get("filter_option", "all")

    # Sorting mapping
    allowed_sorts = {
        "id": "p.product_id",
        "name": "p.name",
        "brand": "b.name",
        "category": "COALESCE(parent.name, c.name)",
        "subcategory": "c.name",
        "stock": "p.stock"
    }

    # Get sorting column
    sort_column = allowed_sorts.get(sort, "p.product_id")

    # Sorting direction validation
    if direction not in ["asc", "desc"]:
        direction = "asc"

    # Base query
    query = """
    FROM products p 
    JOIN brands b ON p.brand_id = b.brand_id 
    JOIN categories c ON p.category_id = c.category_id 
    LEFT JOIN categories parent ON c.parent_id = parent.category_id
    """

    conditions = []
    query_params = []

    # Filter
    if filter_option == "low_stock":
        conditions.append("p.stock BETWEEN 1 AND 10")
        conditions.append("p.is_active = 1")

    elif filter_option == "no_stock":
        conditions.append("p.stock = 0")
        conditions.append("p.is_active = 1")

    elif filter_option == "inactive":
        conditions.append("p.is_active = 0")
    
    else:
        conditions.append("p.is_active = 1")

    # Search
    if search_query:
        conditions.append("""(p.name LIKE ? OR b.name LIKE ? OR c.name LIKE ? OR parent.name LIKE ?)""")
        search_term = f"%{search_query}%"
        query_params = [search_term] * 4

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Count products
    count_query = """SELECT COUNT(*) AS total """ + query

    total_products = db.execute(count_query, query_params).fetchone()["total"]

    # Calculate the total number of pages
    products_per_page = 10
    total_pages = math.ceil(total_products / products_per_page)

    # Main query
    main_query = """SELECT p.product_id, p.name, p.pack_size, p.stock, p.is_active, b.name AS brand_name, c.name AS assigned_category, parent.name AS parent_category """ + query

    # Add sorting 
    main_query += f" ORDER BY {sort_column} {direction.upper()}"

    # Add pagination
    main_query, query_params, page = pagination(request.args, main_query, query_params, products_per_page)

    # Get products
    products = db.execute(main_query, query_params).fetchall()

    # Preserve params in pagination, sorting and filter links
    base_params = {
        "search_query": search_query,
        "filter_option": filter_option,
        "sort": sort,
        "direction": direction
    }

    return render_template("admin/inventory.html", active_page="inventory", low_stock_count=low_stock_count, no_stock_count=no_stock_count, inactive_count=inactive_count, sort=sort,
                           direction=direction, search_query=search_query, filter_option=filter_option, products=products, base_params=base_params, total_pages=total_pages, page=page)

@admin_bp.route("/products/<int:product_id>/activate", methods=["POST"])
@admin_required
def activate_product(product_id):

    # Connect to database
    db = get_db()

    # Update active state
    activate_product_by_id(db=db, product_id=product_id)

    db.commit()

    flash("Product activated successfully", "success")
    return redirect(request.referrer)