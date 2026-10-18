from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Admin login and CRUD routes arrive in Steps 7 and 8.