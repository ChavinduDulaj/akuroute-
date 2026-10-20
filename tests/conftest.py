import pytest

from app import create_app
from models import db, Admin, Place, Category

ADMIN_PASSWORD = "correct-horse-1"


def build_app(tmp_path, csrf=False, seed=True):
    app = create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "WTF_CSRF_ENABLED": csrf,
        "SECRET_KEY": "test-secret",
    })
    app.static_folder = str(tmp_path)        # uploads go to a temp folder, not your project
    with app.app_context():
        db.create_all()
        if seed:
            cats = {n: Category(name=n) for n in ["Religious", "Heritage", "Nature", "Cultural"]}
            db.session.add_all(cats.values())
            db.session.add_all([
                Place(name="Temple A", distance_km=10, latitude=5.95, longitude=80.50,
                      categories=[cats["Religious"]]),
                Place(name="Fort B", distance_km=15, latitude=5.96, longitude=80.55,
                      categories=[cats["Heritage"]]),
                Place(name="Beach C", distance_km=5, latitude=5.94, longitude=80.52,
                      categories=[cats["Nature"], cats["Heritage"]]),
            ])
            admin = Admin(username="admin")
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
    return app


@pytest.fixture()
def app(tmp_path):
    return build_app(tmp_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    c = app.test_client()
    c.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    return c


@pytest.fixture()
def empty_client(tmp_path):
    return build_app(tmp_path, seed=False).test_client()


@pytest.fixture()
def csrf_client(tmp_path):
    return build_app(tmp_path, csrf=True).test_client()


@pytest.fixture()
def category_id(app):
    def lookup(name):
        with app.app_context():
            return Category.query.filter_by(name=name).first().id
    return lookup