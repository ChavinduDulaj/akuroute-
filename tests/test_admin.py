import io
import os
from datetime import timedelta

from models import db, Admin, Place
from tests.conftest import ADMIN_PASSWORD

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def valid_form(category_id, **overrides):
    data = {
        "name": "New Spot", "categories": [category_id("Nature")],
        "distance_km": "7", "latitude": "5.97", "longitude": "80.5",
        "visit_minutes": "45", "description": "A test place.",
    }
    data.update(overrides)
    return data


def place_count(app):
    with app.app_context():
        return Place.query.count()


# ---- FR-5 / NFR-3: authentication -------------------------------------------
def test_fr_5_1_admin_pages_need_login(client):
    for url in ("/admin/", "/admin/places/new", "/admin/places/1/edit"):
        r = client.get(url)
        assert r.status_code == 302 and "/admin/login" in r.headers["Location"]
    assert client.post("/admin/places/1/delete").status_code == 302


def test_fr_5_2_wrong_password_and_unknown_user_same_message(client):
    wrong_pw = client.post("/admin/login", data={"username": "admin", "password": "nope"})
    unknown = client.post("/admin/login", data={"username": "ghost", "password": "nope"})
    for r in (wrong_pw, unknown):
        assert r.status_code == 200
        assert "Invalid username or password." in r.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302          # still logged out


def test_login_success_reaches_dashboard(client):
    r = client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD},
                    follow_redirects=True)
    assert "Admin dashboard" in r.get_data(as_text=True)


def test_fr_5_3_password_is_stored_as_salted_hash(app):
    with app.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        assert admin.password_hash != ADMIN_PASSWORD
        assert ADMIN_PASSWORD not in admin.password_hash
        assert len(admin.password_hash) > 50
        assert admin.check_password(ADMIN_PASSWORD)
        assert not admin.check_password("wrong")


def test_fr_5_4_logout_ends_session(admin_client):
    assert admin_client.get("/admin/").status_code == 200
    admin_client.post("/admin/logout")
    assert admin_client.get("/admin/").status_code == 302


def test_nfr_3_4_session_expires_after_30_minutes(app, client):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)
    r = client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    cookies = r.headers.getlist("Set-Cookie")
    assert any("Expires=" in c for c in cookies)             # permanent session => timeout applies


def test_login_does_not_redirect_to_other_sites(client):
    r = client.post("/admin/login?next=https://evil.example",
                    data={"username": "admin", "password": ADMIN_PASSWORD})
    assert "evil.example" not in r.headers["Location"]


# ---- FR-6.1 / 6.4: add + validation ------------------------------------------
def test_fr_6_1_add_place(app, admin_client, category_id):
    r = admin_client.post("/admin/places/new", data=valid_form(category_id), follow_redirects=True)
    assert "was added" in r.get_data(as_text=True)
    assert place_count(app) == 4


def test_fr_6_4_empty_form_shows_errors_and_saves_nothing(app, admin_client):
    r = admin_client.post("/admin/places/new", data={})
    html = r.get_data(as_text=True)
    assert "Name is required." in html
    assert "Choose at least one category." in html
    assert "Enter a distance between 0 and 25 km." in html
    assert place_count(app) == 3


def test_fr_6_4_validation_keeps_typed_values(admin_client, category_id):
    r = admin_client.post("/admin/places/new",
                          data=valid_form(category_id, name="Keep Me", distance_km="99"))
    html = r.get_data(as_text=True)
    assert 'value="Keep Me"' in html
    assert "Enter a distance between 0 and 25 km." in html


def test_fr_6_4_swapped_coordinates_rejected(app, admin_client, category_id):
    r = admin_client.post("/admin/places/new",
                          data=valid_form(category_id, latitude="80.5", longitude="5.9"))
    assert "swap latitude and longitude" in r.get_data(as_text=True)
    assert place_count(app) == 3


def test_duplicate_name_rejected(app, admin_client, category_id):
    r = admin_client.post("/admin/places/new", data=valid_form(category_id, name="temple a"))
    assert "already exists" in r.get_data(as_text=True)
    assert place_count(app) == 3


# ---- FR-6.2 / 6.5: edit shows up immediately ---------------------------------
def test_fr_6_2_and_6_5_edit_appears_on_tourist_pages(admin_client, client, category_id):
    r = admin_client.post("/admin/places/1/edit",
                          data=valid_form(category_id, name="Renamed Temple"), follow_redirects=True)
    assert "was updated" in r.get_data(as_text=True)
    assert "Renamed Temple" in client.get("/places").get_data(as_text=True)
    assert "Renamed Temple" in client.get("/map").get_data(as_text=True)


# ---- FR-6.3: delete -----------------------------------------------------------
def test_fr_6_3_delete_place(app, admin_client, client):
    admin_client.post("/admin/places/1/delete")
    assert place_count(app) == 2
    assert "Temple A" not in client.get("/places").get_data(as_text=True)


def test_delete_requires_post(admin_client):
    assert admin_client.get("/admin/places/1/delete").status_code == 405


def test_edit_missing_place_is_404(admin_client):
    assert admin_client.get("/admin/places/999/edit").status_code == 404


# ---- NFR-3.3: injection and XSS ----------------------------------------------
def test_nfr_3_3_script_in_name_is_escaped(admin_client, client, category_id):
    evil = "<script>alert(1)</script>"
    admin_client.post("/admin/places/new", data=valid_form(category_id, name=evil))
    html = client.get("/places").get_data(as_text=True)
    assert evil not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_nfr_3_3_sql_injection_in_filter_is_harmless(client):
    r = client.get("/places?cat=' OR 1=1 --")
    assert r.status_code == 200
    assert "No places match your filter" in r.get_data(as_text=True)


def test_nfr_3_3_javascript_image_address_rejected(app, admin_client, category_id):
    r = admin_client.post("/admin/places/new",
                          data=valid_form(category_id, image_url="javascript:alert(1)"))
    assert "Image address must start with" in r.get_data(as_text=True)
    assert place_count(app) == 3


# ---- image upload --------------------------------------------------------------
def test_upload_valid_image_saves_file(app, admin_client, category_id, tmp_path):
    data = valid_form(category_id, name="With Image")
    data["image_file"] = (io.BytesIO(PNG_BYTES), "photo.png")
    admin_client.post("/admin/places/new", data=data, content_type="multipart/form-data")
    with app.app_context():
        place = Place.query.filter_by(name="With Image").first()
        assert place.image_url.startswith("uploads/")
    assert len(os.listdir(tmp_path / "uploads")) == 1


def test_upload_fake_image_rejected(app, admin_client, category_id):
    data = valid_form(category_id, name="Fake Image")
    data["image_file"] = (io.BytesIO(b"just some text"), "fake.jpg")
    r = admin_client.post("/admin/places/new", data=data, content_type="multipart/form-data")
    assert "Please upload a JPG, PNG or WebP image." in r.get_data(as_text=True)
    assert place_count(app) == 3


def test_deleting_place_removes_its_uploaded_file(admin_client, category_id, tmp_path, app):
    data = valid_form(category_id, name="Temp Image")
    data["image_file"] = (io.BytesIO(PNG_BYTES), "photo.png")
    admin_client.post("/admin/places/new", data=data, content_type="multipart/form-data")
    with app.app_context():
        pid = Place.query.filter_by(name="Temp Image").first().id
    admin_client.post(f"/admin/places/{pid}/delete")
    assert os.listdir(tmp_path / "uploads") == []