import time
from app import create_app
from models import db, Place, Category


def make_app():
    return create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })


# ---------------------------------------------------------------- 1. empty database
app = make_app()
with app.app_context():
    db.create_all()
client = app.test_client()

print("\n1) Empty database (SRS 5.4.2): every page must load without a server error")
for url in ["/", "/places", "/places?cat=Nature", "/map", "/plan", "/admin/login"]:
    code = client.get(url).status_code
    print(f"   {url:22} {code}  {'OK' if code == 200 else '<-- CHECK'}")
code = client.get("/places/1").status_code
print(f"   {'/places/1 (missing)':22} {code}  {'OK' if code == 404 else '<-- CHECK'}")
code = client.get("/admin/").status_code
print(f"   {'/admin/ (logged out)':22} {code}  {'OK' if code == 302 else '<-- CHECK'}")


# ---------------------------------------------------------------- 2. 100 places, timing
app = make_app()
with app.app_context():
    db.create_all()
    cats = [Category(name=n) for n in ["Religious", "Heritage", "Nature", "Cultural"]]
    db.session.add_all(cats)
    for i in range(100):
        db.session.add(Place(name=f"Test place {i}", distance_km=1 + i % 24,
                             latitude=5.9 + (i % 10) * 0.02, longitude=80.4 + (i % 10) * 0.02,
                             categories=[cats[i % 4], cats[(i + 1) % 4]]))
    db.session.commit()
client = app.test_client()
with client.session_transaction() as s:
    s["plan"] = [1, 2, 3, 4, 5]

print("\n2) 100 places: server response time vs. targets (NFR-1.1 to 1.3)")
for url, limit in [("/places", 3.0), ("/places?cat=Nature", 2.0), ("/map", 4.0),
                   ("/places/1", 3.0), ("/plan", 3.0)]:
    start = time.perf_counter()
    response = client.get(url)
    seconds = time.perf_counter() - start
    status = "OK" if response.status_code == 200 and seconds < limit else "<-- CHECK"
    print(f"   {url:22} {response.status_code}  {seconds * 1000:7.1f} ms  (target < {limit * 1000:.0f} ms)  {status}")

print("\nNote: this measures server time only. Map tiles load from OpenStreetMap in the browser.\n")