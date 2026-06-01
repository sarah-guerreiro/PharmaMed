def get_user_addresses(db, user_id):

    return db.execute(
        """
        SELECT *
        FROM addresses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()

def reset_existing_addresses(db, user_id):

    db.execute(
        """
        UPDATE addresses 
        SET is_default = 0 
        WHERE user_id = ?
        """, 
        (user_id,)
    )

def count_existing_addresses(db, user_id):

    return db.execute(
        """
        SELECT COUNT(*) 
        FROM addresses 
        WHERE user_id = ?
        """, 
        (user_id,)
    ).fetchone()[0]

def create_user_address(db, user_id, full_name, address_line, postal_code, city, country, is_default):

    db.execute(
        """
        INSERT INTO addresses (user_id, full_name, address_line, postal_code, city, country, is_default) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, 
        (user_id, full_name, address_line, postal_code, city, country, is_default)
    )

def update_user_address (db, full_name, address_line, postal_code, city, country, address_id, user_id):

    db.execute(
        """
        UPDATE addresses 
        SET full_name = ?, address_line = ?, postal_code = ?, city = ?, country = ? 
        WHERE id = ? 
        AND user_id = ?
        """, 
        (full_name, address_line, postal_code, city, country, address_id, user_id)
    )

def delete_user_address(db, address_id, user_id):

    db.execute(
        """
        DELETE FROM addresses 
        WHERE id = ? 
        AND user_id = ?
        """, 
        (address_id, user_id)
    )