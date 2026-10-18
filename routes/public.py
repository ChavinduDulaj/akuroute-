from flask import Blueprint, render_template, request
from models import db, Category, Place

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    categories = Category.query.order_by(Category.name).all()
    nearest = Place.query.order_by(Place.distance_km).limit(3).all()
    return render_template("index.html", categories=categories, nearest=nearest)


@bp.route("/places")
def places():
    selected = request.args.getlist("cat")            # e.g. ?cat=Nature&cat=Heritage
    query = Place.query
    if selected:
        query = query.filter(Place.categories.any(Category.name.in_(selected)))
    results = query.order_by(Place.distance_km).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template("places.html", places=results,
                           categories=categories, selected=selected)


@bp.route("/places/<int:place_id>")
def place_detail(place_id):
    place = db.get_or_404(Place, place_id)            # shows a 404 page if the ID doesn't exist
    return render_template("place_detail.html", place=place)


@bp.route("/map")
def map_view():
    data = [
        {
            "id": p.id,
            "name": p.name,
            "cats": ", ".join(c.name for c in p.categories),
            "lat": p.latitude,
            "lng": p.longitude,
        }
        for p in Place.query.all()
    ]
    return render_template("map.html", places_json=data)