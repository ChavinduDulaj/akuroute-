import os
from datetime import timedelta

from flask import Flask, session, flash, redirect, url_for, render_template
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from models import db, Admin

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key-change-later"),
        # Switching to MySQL later = change this one setting (SRS 5.4.4)
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///akuroute.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),      # NFR-3.4
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,                    # 5 MB upload limit
        SESSION_COOKIE_HTTPONLY=True,                          # JavaScript can't read the cookie
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SECURE_COOKIES") == "1",   # set to 1 on HTTPS hosting
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "Please log in to access the admin area."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    from routes.public import bp as public_bp
    from routes.plan import bp as plan_bp
    from routes.admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_plan_count():
        return {"plan_count": len(session.get("plan", []))}

    # ------------------------------------------------------------ security headers
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        # Not "no-referrer": OpenStreetMap's tile servers expect a Referer header
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # ------------------------------------------------------------ error pages
    def show_error(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return show_error(400, "This form has expired",
                          "For your security the form could not be submitted. "
                          "Please go back, refresh the page and try again.")

    @app.errorhandler(403)
    def forbidden(e):
        return show_error(403, "Access denied", "You do not have permission to view this page.")

    @app.errorhandler(404)
    def not_found(e):
        return show_error(404, "Page not found",
                          "We couldn't find the page you were looking for. "
                          "It may have been moved or removed.")

    @app.errorhandler(413)
    def file_too_large(e):
        flash("That file is too large. The maximum size is 5 MB.", "danger")
        return redirect(url_for("admin.dashboard"))

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()          # leave the database in a clean state
        return show_error(500, "Something went wrong",
                          "An unexpected error occurred. Please try again in a moment.")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)