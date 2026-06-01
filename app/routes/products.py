import math

from flask import (
    abort, 
    Blueprint, 
    render_template, 
    redirect, 
    request, 
    url_for
)

from app.services.product_service import (
    get_category_by_id,
    get_category_children,
    get_brand_by_id,
    get_product_details
)

from app.utils.categories import get_breadcrumb
from app.utils.db import get_db
from app.utils.query_helpers import price_filter, count_products, apply_sorting, pagination

products_bp = Blueprint("products", __name__)

@products_bp.route("/products/<int:category_id>")
def display_category(category_id):
    
    # Connect to database
    db = get_db()

    # Get category/subcategory
    category = get_category_by_id(db, category_id)

    if not category:
        abort(404)

    # Build breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], 
            "url": url_for("products.display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(category["category_id"])
    ]

    # Get all subcategories in current category
    subcategories = get_category_children(db, category_id)

    category_ids = [category_id] + [subcategory["category_id"] for subcategory in subcategories]

    # Base query
    query = """
    FROM products p 
    WHERE p.is_active = 1 
    AND p.category_id IN ({})""".format(",".join("?" * len(category_ids)))

    query_params = category_ids.copy() 
    
    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    selected_brands = request.args.getlist('brand')
    
    # Apply subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?" * len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Apply brand filter
    if selected_brands:
        query += " AND p.brand_id IN ({})".format(",".join("?" * len(selected_brands)))
        query_params.extend([int(brand) for brand in selected_brands])

    # Get brands based on filtered subcategories and brands
    brands = db.execute(
        f"""
        SELECT DISTINCT b.brand_id, b.name 
        FROM brands b 
        JOIN products p ON b.brand_id = p.brand_id 
        """ 
        + query.replace("FROM products p", "") 
        + """ORDER BY b.name""", query_params
    ).fetchall()

    # Apply min price and max price filter if set
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)
    
    # Count products
    total_products = count_products(db, query, query_params)

    # Sort products based on selected sorting option
    query = apply_sorting(request.args, query)

    # Calculate the total number of pages
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    # Add pagination
    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Get products in current category/subcategory
    products_query = "SELECT p.name, p.price, p.stock, p.image_url, p.product_id " + query
    products = db.execute(products_query, query_params).fetchall()

    # Count the number of active filters
    active_filters_count = (len(selected_subcategories) + len(selected_brands) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Route for url_for
    route_name = "products.display_category"

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

@products_bp.route("/product/<int:product_id>")
def product_detail(product_id):

    # Connect to database
    db = get_db()

    # Get product details
    product = get_product_details(db, product_id)
    
    if not product:
        abort(404)

    # Get breadcrumb list
    breadcrumb = [
        {
            "name": category["name"], 
            "url": url_for("products.display_category", category_id=category["category_id"])
        }
        for category in get_breadcrumb(product["category_id"])
    ]

    # Get page type
    page_type = "product"

    return render_template("product_detail.html", product=product, breadcrumb=breadcrumb, page_type=page_type)

@products_bp.route("/brands/<int:brand_id>")
def display_brand(brand_id):

    # Connect to database
    db = get_db()

    # Get brand
    brand = get_brand_by_id(db, brand_id)

    if not brand:
        abort(404)

    # Base query
    query = """
    FROM products p 
    WHERE p.is_active = 1 
    AND p.brand_id = ?
    """

    query_params = [brand_id] 

    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    
    # Apply subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?" * len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Get subcategories based on selected brand
    subcategories = db.execute(
        f"""
        SELECT DISTINCT c.category_id, c.name """ 
        + query.replace("FROM products p", "FROM categories c JOIN products p ON p.category_id = c.category_id") 
        + """ORDER BY c.name""", query_params
    ).fetchall()

    # Apply min price and max price filter if set
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)
    
    # Count products
    total_products = count_products(db, query, query_params)

    # Sort products based on selected sorting option 
    query = apply_sorting(request.args, query)

    # Calculate the total number of pages
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    # Add pagination
    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Get products in current brand
    products_query = "SELECT p.name, p.price, p.stock, p.image_url, p.product_id " + query
    products = db.execute(products_query, query_params).fetchall()

    # Count the number of active filters
    active_filters_count = (len(selected_subcategories) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Get breadcrumb list
    breadcrumb = [
        {"name": brand["name"], "url": None}
    ]

    # Route for url_for
    route_name = "products.display_brand"

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

@products_bp.route("/search")
def search():

    # Connect to database
    db = get_db()

    # Get search query
    search_query = request.args.get("search_query", "").strip()

    if not search_query:
        return redirect(url_for("main.index"))

    # Base query (search in product name, category name or brand name)
    query = """FROM products p 
    JOIN categories c ON p.category_id = c.category_id 
    LEFT JOIN categories parent ON c.parent_id = parent.category_id 
    JOIN brands b ON p.brand_id = b.brand_id 
    WHERE p.is_active = 1 
    AND (p.name LIKE ? OR b.name LIKE ? OR c.name LIKE ? OR parent.name LIKE ?)
    """

    query_params = [f"%{search_query}%"] * 4

    # Get selected filters from the URL query parameters
    selected_subcategories = request.args.getlist('subcategory')
    selected_brands = request.args.getlist('brand')
    
    # Apply subcategory filter
    if selected_subcategories:
        query += " AND p.category_id IN ({})".format(",".join("?" * len(selected_subcategories)))
        query_params.extend([int(subcategory) for subcategory in selected_subcategories])

    # Apply brand filter
    if selected_brands:
        query += " AND p.brand_id IN ({})".format(",".join("?" * len(selected_brands)))
        query_params.extend([int(b) for b in selected_brands])

    # Apply min price and max price filter if set
    min_price, max_price, query, query_params = price_filter(request.args, query, query_params)

    # Get brands based on search query
    brands = db.execute(
        f"""
        SELECT DISTINCT b.brand_id, b.name {query} 
        ORDER BY b.name
        """
        , query_params
    ).fetchall()

    # Get subcategories based on search query
    subcategories = db.execute(
        f"""
        SELECT DISTINCT c.category_id, c.name {query} 
        ORDER BY c.name
        """
        , query_params
    ).fetchall()

    # Count products
    total_products = count_products(db, query, query_params)

    # Apply sorting
    query = apply_sorting(request.args, query)

    # Add pagination
    products_per_page = 16
    total_pages = math.ceil(total_products / products_per_page)

    query, query_params, page = pagination(request.args, query, query_params, products_per_page)

    # Get products
    products_query = "SELECT p.name, p.price, p.stock, p.image_url, p.product_id " + query
    products = db.execute(products_query, query_params).fetchall()

    # Active filters count
    active_filters_count = (len(selected_subcategories) + len(selected_brands) + (1 if min_price is not None else 0) + (1 if max_price is not None else 0))

    # Route for url_for
    route_name = "products.search"

    # Parameters for url_for
    base_params = {
        "search_query": search_query,
        "subcategory": request.args.getlist('subcategory'),
        "brand": request.args.getlist('brand'),
        "min_price": request.args.get('min_price'),
        "max_price": request.args.get('max_price'),
        "sort": request.args.get('sort'),
    }

    # Get page type
    page_type = "search"

    return render_template("products.html", page_title=f"Search results for '{search_query}'", products=products, page=page, total_pages=total_pages, subcategories=subcategories,
                            brands=brands, total_products=total_products, active_filters_count=active_filters_count, route_name=route_name, base_params=base_params,
                            page_type=page_type)