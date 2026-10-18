from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Helper table: links places and categories (many-to-many)
place_categories = db.Table(
    "place_categories",
    db.Column("place_id", db.Integer, db.ForeignKey("place.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"), primary_key=True),
)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)

    def __repr__(self):
        return f"<Category {self.name}>"


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    distance_km = db.Column(db.Float, nullable=False)      # distance from Akuressa
    description = db.Column(db.Text)
    opening_times = db.Column(db.String(200))
    travel_tips = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300))                   # optional (FR-2.4)
    visit_minutes = db.Column(db.Integer, default=60)       # suggested time to spend there

    categories = db.relationship("Category", secondary=place_categories, backref="places")

    def __repr__(self):
        return f"<Place {self.name}>"


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)   # salted hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)