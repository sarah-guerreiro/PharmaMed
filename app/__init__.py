# AI assistance: ChatGPT was consulted on refactoring the initial app.py
# file and implementing Flask blueprints to separate application routes
# into dedicated modules.

import os

from flask import Flask

from app.extensions import login_manager

from app.routes.account import account_bp
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.cart import cart_bp
from app.routes.main import main_bp
from app.routes.orders import orders_bp
from app.routes.products import products_bp

from app.services.cart_service import get_cart_count

from app.utils.categories import load_categories_menu
from app.utils.db import close_db

from app.utils.formatting import format_date 

# Configure application
app = Flask(__name__)

# Get secret key
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Close database after request
app.teardown_appcontext(close_db)

# Register date format filter
app.jinja_env.filters["format_date"] = format_date

# Register blueprints
app.register_blueprint(account_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(main_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(products_bp)

# Make variables available in all templates
@app.context_processor
def inject_globals():
    return {
        "categories_menu": load_categories_menu(),
        "cart_count": get_cart_count()
    }








