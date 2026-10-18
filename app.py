import os
from datetime import timedelta

from flask import Flask, session
from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from models import db, Admin

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key-change-later"),
        SQLALCHEMY_DATABASE_URI="sqlite:///akuroute.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),   # admin timeout (NFR-3.4)
    )

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"     # where to send logged-out admins (Step 7)

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

    return app


if __name__ == "__main__":
    create_app().run(debug=True)