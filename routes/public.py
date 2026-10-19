from flask import Blueprint, render_template, request, session
from models import db, Category, Place
from sqlalchemy.orm import selectinload

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    categories = Category.query.order_by(Category.name).all()
    nearest = (Place.query.options(selectinload(Place.categories)).order_by(Place.distance_km).limit(3).all())
    return render_template("index.html", categories=categories, nearest=nearest)


@bp.route("/places")
def places():
    selected = request.args.getlist("cat")            # e.g. ?cat=Nature&cat=Heritage
    query = Place.query.options(selectinload(Place.categories))
    if selected:
        query = query.filter(Place.categories.any(Category.name.in_(selected)))
    results = query.order_by(Place.distance_km).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template("places.html", places=results,
                           categories=categories, selected=selected)


@bp.route("/places/<int:place_id>")
def place_detail(place_id):
    place = db.get_or_404(Place, place_id)
    in_plan = place.id in session.get("plan", [])
    return render_template("place_detail.html", place=place, in_plan=in_plan)


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
        for p in Place.query.options(selectinload(Place.categories)).all()
    ]
    return render_template("map.html", places_json=data)