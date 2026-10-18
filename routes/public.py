from flask import Blueprint, render_template
from models import Category, Place

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    categories = Category.query.order_by(Category.name).all()
    nearest = Place.query.order_by(Place.distance_km).limit(3).all()
    return render_template("index.html", categories=categories, nearest=nearest)


# Temporary pages so the navbar links work. We build these properly in Step 5.
@bp.route("/places")
def places():
    return render_template("coming_soon.html", title="Places")


@bp.route("/map")
def map_view():
    return render_template("coming_soon.html", title="Map")