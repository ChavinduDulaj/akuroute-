from getpass import getpass
from app import create_app
from models import db, Admin

app = create_app()
with app.app_context():
    user = Admin.query.filter_by(username="admin").first()
    if not user:
        print("No admin account found. Run seed.py first.")
    else:
        pw1 = getpass("New password: ")
        pw2 = getpass("Repeat password: ")
        if pw1 != pw2 or len(pw1) < 8:
            print("Passwords must match and be at least 8 characters.")
        else:
            user.set_password(pw1)
            db.session.commit()
            print("Password updated.")