import math

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Admin, Place, Category

bp = Blueprint("admin", __name__, url_prefix="/admin")

_DUMMY_HASH = generate_password_hash("not-a-real-password")

# Sri Lanka bounding box, used to catch swapped or mistyped coordinates
LAT_MIN, LAT_MAX = 5.5, 10.0
LNG_MIN, LNG_MAX = 79.4, 82.0
MAX_DISTANCE_KM = 25      # AkuRoute covers a 25 km radius (SRS 2.5)


# ---------------------------------------------------------------- login / logout
def _is_safe_next(target):
    return bool(target) and target.startswith("/") \
        and not target.startswith("//") and "\\" not in target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = Admin.query.filter_by(username=username).first()
        if user:
            ok = user.check_password(password)
        else:
            check_password_hash(_DUMMY_HASH, password)
            ok = False

        if ok:
            login_user(user)
            session.permanent = True
            nxt = request.args.get("next")
            return redirect(nxt if _is_safe_next(nxt) else url_for("admin.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("admin/login.html", username=username)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.home"))


# ---------------------------------------------------------------- dashboard
@bp.route("/")
@login_required
def dashboard():
    places = Place.query.order_by(Place.name).all()
    return render_template("admin/dashboard.html", places=places)


# ---------------------------------------------------------------- validation
def _to_float(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def validate_place_form(form, place_id=None):
    """Check the submitted form. Returns (clean_data, chosen_categories, errors)."""
    errors = {}

    name = form.get("name", "").strip()
    if not name:
        errors["name"] = "Name is required."
    elif len(name) > 120:
        errors["name"] = "Name must be 120 characters or fewer."
    else:
        dup = Place.query.filter(db.func.lower(Place.name) == name.lower())
        if place_id:
            dup = dup.filter(Place.id != place_id)
        if dup.first():
            errors["name"] = "A place with this name already exists."

    chosen_ids = [int(c) for c in form.getlist("categories") if c.isdigit()]
    cats = Category.query.filter(Category.id.in_(chosen_ids)).all() if chosen_ids else []
    if not cats:
        errors["categories"] = "Choose at least one category."

    distance = _to_float(form.get("distance_km"))
    if distance is None or not (0 < distance <= MAX_DISTANCE_KM):
        errors["distance_km"] = f"Enter a distance between 0 and {MAX_DISTANCE_KM} km."

    lat = _to_float(form.get("latitude"))
    if lat is None or not (LAT_MIN <= lat <= LAT_MAX):
        errors["latitude"] = (f"Latitude should be between {LAT_MIN} and {LAT_MAX} (Sri Lanka). "
                              "Did you swap latitude and longitude?")

    lng = _to_float(form.get("longitude"))
    if lng is None or not (LNG_MIN <= lng <= LNG_MAX):
        errors["longitude"] = f"Longitude should be between {LNG_MIN} and {LNG_MAX} (Sri Lanka)."

    minutes_text = form.get("visit_minutes", "").strip() or "60"
    if minutes_text.isdigit() and 5 <= int(minutes_text) <= 600:
        minutes = int(minutes_text)
    else:
        minutes = None
        errors["visit_minutes"] = "Enter a whole number of minutes between 5 and 600."

    opening = form.get("opening_times", "").strip()
    if len(opening) > 200:
        errors["opening_times"] = "Opening times must be 200 characters or fewer."

    image_url = form.get("image_url", "").strip()
    if image_url and (len(image_url) > 300 or not image_url.lower().startswith(("http://", "https://"))):
        errors["image_url"] = "Image address must start with http:// or https:// (max 300 characters)."

    data = {
        "name": name,
        "distance_km": distance,
        "description": form.get("description", "").strip() or None,
        "opening_times": opening or None,
        "travel_tips": form.get("travel_tips", "").strip() or None,
        "latitude": lat,
        "longitude": lng,
        "image_url": image_url or None,
        "visit_minutes": minutes,
    }
    return data, cats, errors


def _values_from_place(p):
    def s(v):
        return "" if v is None else v
    return {
        "name": s(p.name), "distance_km": s(p.distance_km), "description": s(p.description),
        "opening_times": s(p.opening_times), "travel_tips": s(p.travel_tips),
        "latitude": s(p.latitude), "longitude": s(p.longitude),
        "image_url": s(p.image_url), "visit_minutes": s(p.visit_minutes),
    }


def _selected_ids(form):
    return [int(c) for c in form.getlist("categories") if c.isdigit()]


# ---------------------------------------------------------------- add
@bp.route("/places/new", methods=["GET", "POST"])
@login_required
def place_new():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        data, cats, errors = validate_place_form(request.form)
        if not errors:
            place = Place(**data, categories=cats)
            db.session.add(place)
            db.session.commit()
            flash(f"\"{place.name}\" was added.", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Please fix the errors below.", "danger")
        return render_template("admin/place_form.html", mode="new", categories=categories,
                               values=request.form, selected=_selected_ids(request.form), errors=errors)

    return render_template("admin/place_form.html", mode="new", categories=categories,
                           values={"visit_minutes": "60"}, selected=[], errors={})


# ---------------------------------------------------------------- edit
@bp.route("/places/<int:place_id>/edit", methods=["GET", "POST"])
@login_required
def place_edit(place_id):
    place = db.get_or_404(Place, place_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        data, cats, errors = validate_place_form(request.form, place_id=place.id)
        if not errors:
            for field, value in data.items():
                setattr(place, field, value)
            place.categories = cats
            db.session.commit()
            flash(f"\"{place.name}\" was updated.", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Please fix the errors below.", "danger")
        return render_template("admin/place_form.html", mode="edit", place=place, categories=categories,
                               values=request.form, selected=_selected_ids(request.form), errors=errors)

    return render_template("admin/place_form.html", mode="edit", place=place, categories=categories,
                           values=_values_from_place(place),
                           selected=[c.id for c in place.categories], errors={})


# ---------------------------------------------------------------- delete
@bp.route("/places/<int:place_id>/delete", methods=["POST"])
@login_required
def place_delete(place_id):
    place = db.get_or_404(Place, place_id)
    name = place.name
    db.session.delete(place)
    db.session.commit()
    flash(f"\"{name}\" was deleted.", "info")
    return redirect(url_for("admin.dashboard"))