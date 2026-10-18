from flask import Flask
from models import db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-key-change-later"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///akuroute.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    @app.route("/")
    def home():
        return "<h1>Hello AkuRoute!</h1>"

    return app


if __name__ == "__main__":
    create_app().run(debug=True)