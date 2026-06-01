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

def count_products(db, query, query_params):
    
    count_query = f"SELECT COUNT(*) {query}"
    
    return db.execute(count_query, query_params).fetchone()[0]

def apply_sorting(args, query):
    
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