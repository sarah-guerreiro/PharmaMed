from app.utils.db import get_db

def load_categories_menu():
    
    db = get_db()
    
    rows = db.execute(
        """
        SELECT category_id, name, parent_id, icon
        FROM categories
        ORDER BY category_id
        """
    ).fetchall()

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

        parent_id = row["parent_id"]

        if parent_id != 0 and parent_id in categories_menu:

            categories_menu[parent_id]["subcategories"].append(row)

    return categories_menu

def get_breadcrumb(category_id):

    db = get_db()
    
    breadcrumb = []
    
    current = db.execute(
        """
        SELECT category_id, name, parent_id 
        FROM categories 
        WHERE category_id = ?
        """, 
        (category_id,)
    ).fetchone()
    
    while current:

        breadcrumb.insert(0, current) 

        parent_id = current["parent_id"]

        if parent_id == 0:
            break

        current = db.execute(
            """
            SELECT category_id, name, parent_id 
            FROM categories 
            WHERE category_id = ?
            """, 
            (parent_id,)
        ).fetchone()
    
    return breadcrumb