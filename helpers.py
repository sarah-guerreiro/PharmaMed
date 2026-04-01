from flask import url_for

def get_breadcrumb(category_id, db):
    
    # Build breadcrumb list
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