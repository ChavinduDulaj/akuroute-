from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import Admin, Place

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Used to keep login timing similar whether or not the username exists
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _is_safe_next(target):
    """Only allow redirects to pages on this same site."""
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
            check_password_hash(_DUMMY_HASH, password)     # same work, result ignored
            ok = False

        if ok:
            login_user(user)                # no "remember me" cookie
            session.permanent = True        # activates the 30-minute timeout
            nxt = request.args.get("next")
            return redirect(nxt if _is_safe_next(nxt) else url_for("admin.dashboard"))

        flash("Invalid username or password.", "danger")   # generic message (FR-5.2)

    return render_template("admin/login.html", username=username)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.home"))


@bp.route("/")
@login_required
def dashboard():
    places = Place.query.order_by(Place.name).all()
    return render_template("admin/dashboard.html", places=places)