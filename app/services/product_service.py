def get_brands(db):

    return db.execute(
        """
        SELECT brand_id, name 
        FROM brands 
        ORDER BY name ASC
        """
    ).fetchall()

def get_brand_by_id(db, brand_id):

    return db.execute(
        """
        SELECT brand_id, name 
        FROM brands 
        WHERE brand_id = ?
        """, 
        (brand_id,)
    ).fetchone()

def get_main_categories(db):
    
    return db.execute(
        """
        SELECT category_id, name, image_url
        FROM categories
        WHERE parent_id = 0
        """
    ).fetchall()

def get_categories(db):

    return db.execute(
        """
        SELECT category_id, name 
        FROM categories 
        WHERE parent_id = 0 
        ORDER BY name ASC
        """
    ).fetchall()

def get_category_by_id(db, category_id):

    return db.execute(
        """
        SELECT category_id, name 
        FROM categories 
        WHERE category_id = ?
        """, 
        (category_id,)
    ).fetchone()

def get_subcategories(db):

    return db.execute(
        """
        SELECT category_id, parent_id, name 
        FROM categories 
        WHERE parent_id != 0 
        ORDER BY name ASC
        """
    ).fetchall()

def get_category_children(db, category_id):

    return db.execute(
        """
        SELECT category_id, name 
        FROM categories 
        WHERE parent_id = ?
        """, 
        (category_id,)
    ).fetchall()

def create_product(db, product_name, description, final_category_id, brand, pack_size, price, stock, image_url):

    db.execute(
            """
            INSERT INTO products (name, description, category_id, brand_id, pack_size, price, stock, image_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, 
            (product_name, description, final_category_id, brand, pack_size, price, stock, image_url)
        )
    
def get_product_details(db, product_id):

    return db.execute(
        """
        SELECT p.product_id, p.name, p.price, p.stock, p.image_url, p.description, p.pack_size, p.category_id, b.brand_id, b.name as brand 
        FROM products p 
        JOIN brands b ON p.brand_id = b.brand_id 
        WHERE p.product_id = ?
        AND p.is_active = 1
        """
        , (product_id,)
    ).fetchone()
    
def get_product_by_id(db, product_id):

    return db.execute(
        """
        SELECT p.*, c.parent_id 
        FROM products p 
        JOIN categories c ON p.category_id = c.category_id 
        WHERE p.product_id = ?
        """, 
        (product_id,)
        ).fetchone()

def update_product(db, product_name, description, brand, final_category_id, pack_size, price, stock, image_url, product_id):

    db.execute(
        """
        UPDATE products 
        SET name = ?, description = ?, brand_id = ?, category_id = ?, pack_size = ?, price = ?, stock = ?, image_url = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?
        """, 
        (product_name, description, brand, final_category_id, pack_size, price, stock, image_url, product_id)
    )

def deactivate_product_by_id(db, product_id):

    db.execute(
        """
        UPDATE products 
        SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
        WHERE product_id = ?
        """, 
        (product_id,)
    )

def activate_product_by_id(db, product_id):

    db.execute(
        """
        UPDATE products 
        SET is_active = 1, updated_at = CURRENT_TIMESTAMP 
        WHERE product_id = ?
        """, 
        (product_id,)
    )

def count_low_stock_products(db):

    return db.execute(
        """
        SELECT COUNT(*) AS total 
        FROM products 
        WHERE is_active = 1 
        AND stock <= 10
        """
    ).fetchone()["total"]

def count_out_of_stock_products(db):

    return db.execute(
        """
        SELECT COUNT(*) AS total 
        FROM products 
        WHERE is_active = 1 
        AND stock = 0
        """
    ).fetchone()["total"]

def count_inactive_products(db):

    return db.execute(
        """
        SELECT COUNT(*) AS total 
        FROM products 
        WHERE is_active = 0
        """
    ).fetchone()["total"]

def get_low_stock_products(db, limit=None):

    query = """
        SELECT product_id, name, pack_size, stock 
        FROM products 
        WHERE is_active = 1 
        AND stock <= 10 
        ORDER BY stock ASC 
    """

    params = []

    # Add limit only if provided
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    return db.execute(query, tuple(params)).fetchall()
