import math
import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

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
    places = (Place.query.options(selectinload(Place.categories))
              .order_by(Place.name).all())
    return render_template("admin/dashboard.html", places=places)


# ---------------------------------------------------------------- image helpers
def _detect_image_type(head):
    """Identify the real file type from its first bytes (ignores the file name)."""
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def _uploads_folder():
    folder = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(folder, exist_ok=True)
    return folder


def save_uploaded_image(file_storage):
    """Save a validated upload under a random name. Returns e.g. 'uploads/ab12....jpg'."""
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    ext = _detect_image_type(head)
    name = uuid.uuid4().hex + ext
    file_storage.save(os.path.join(_uploads_folder(), name))
    return f"uploads/{name}"


def delete_local_image(image_url):
    """Remove a previously uploaded file from disk (external links are ignored)."""
    if image_url and image_url.startswith("uploads/"):
        path = os.path.join(_uploads_folder(), os.path.basename(image_url))
        if os.path.isfile(path):
            os.remove(path)


def apply_image(place, data, form, files):
    """Decide the new image value. Files are only cleaned up after a successful save."""
    old = place.image_url if place else None
    upload = files.get("image_file")

    if upload and upload.filename:
        return save_uploaded_image(upload)       # a new upload wins
    if data["image_url"]:
        return data["image_url"]                 # an external link
    if form.get("remove_image") == "1":
        return None                              # "remove image" was ticked
    return old                                   # keep what is there


# ---------------------------------------------------------------- validation
def _to_float(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def validate_place_form(form, files, place_id=None):
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

    upload = files.get("image_file")
    if upload and upload.filename:
        head = upload.stream.read(16)
        upload.stream.seek(0)
        if not _detect_image_type(head):
            errors["image_file"] = "Please upload a JPG, PNG or WebP image."

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
        # uploaded files are shown as a preview, not in the address box
        "image_url": p.image_url if p.image_url and p.image_url.startswith("http") else "",
        "visit_minutes": s(p.visit_minutes),
    }


def _selected_ids(form):
    return [int(c) for c in form.getlist("categories") if c.isdigit()]


def _commit():
    """Save changes. Returns True on success, False (after rolling back) on failure."""
    try:
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database save failed")
        return False


# ---------------------------------------------------------------- add
@bp.route("/places/new", methods=["GET", "POST"])
@login_required
def place_new():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        data, cats, errors = validate_place_form(request.form, request.files)
        if not errors:
            new_image = apply_image(None, data, request.form, request.files)
            data["image_url"] = new_image
            place = Place(**data, categories=cats)
            db.session.add(place)
            if _commit():
                flash(f"\"{place.name}\" was added.", "success")
                return redirect(url_for("admin.dashboard"))
            delete_local_image(new_image)                 # undo the file we just saved
            flash("Could not save the place. Please try again.", "danger")
        else:
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
        data, cats, errors = validate_place_form(request.form, request.files, place_id=place.id)
        if not errors:
            old_image = place.image_url
            new_image = apply_image(place, data, request.form, request.files)
            data["image_url"] = new_image
            for field, value in data.items():
                setattr(place, field, value)
            place.categories = cats
            if _commit():
                if new_image != old_image:
                    delete_local_image(old_image)         # safe now that the save worked
                flash(f"\"{place.name}\" was updated.", "success")
                return redirect(url_for("admin.dashboard"))
            if new_image != old_image:
                delete_local_image(new_image)             # undo the new file
            flash("Could not save the changes. Please try again.", "danger")
        else:
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
    name, image = place.name, place.image_url
    db.session.delete(place)
    if _commit():
        delete_local_image(image)
        flash(f"\"{name}\" was deleted.", "info")
    else:
        flash("Could not delete the place. Please try again.", "danger")
    return redirect(url_for("admin.dashboard"))