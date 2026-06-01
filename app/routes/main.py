from flask import Blueprint, render_template

from app.services.product_service import get_main_categories

from app.utils.db import get_db

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
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
        {"file": "avene.png", "name": "Avène"},
        {"file": "a_derma.png", "name": "A-Derma"},
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

    # Connect to database
    db = get_db()

    # Get main categories name, ID and image
    main_categories = get_main_categories(db)

    return render_template("index.html", carousel_categories=carousel_categories, main_categories=main_categories, brands=brands)