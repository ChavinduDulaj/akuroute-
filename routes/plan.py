from flask import Blueprint, render_template

bp = Blueprint("plan", __name__)


@bp.route("/plan")
def view():
    return render_template("coming_soon.html", title="My Visit Plan")