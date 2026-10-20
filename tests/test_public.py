import time

from models import db, Place, Category


# ---- FR-1: browse and filter -------------------------------------------------
def test_fr_1_1_list_shows_all_places_with_distance(client):
    html = client.get("/places").get_data(as_text=True)
    for name in ("Temple A", "Fort B", "Beach C"):
        assert name in html
    assert "10.0 km from Akuressa" in html


def test_fr_1_1_places_sorted_nearest_first(client):
    html = client.get("/places").get_data(as_text=True)
    assert html.index("Beach C") < html.index("Temple A") < html.index("Fort B")


def test_fr_1_2_filter_one_category(client):
    html = client.get("/places?cat=Nature").get_data(as_text=True)
    assert "Beach C" in html
    assert "Temple A" not in html and "Fort B" not in html


def test_fr_1_2_filter_two_categories(client):
    html = client.get("/places?cat=Religious&cat=Nature").get_data(as_text=True)
    assert "Temple A" in html and "Beach C" in html
    assert "Fort B" not in html


def test_fr_1_3_home_links_to_filtered_view(client):
    html = client.get("/").get_data(as_text=True)
    assert "/places?cat=Nature" in html            # one click from the home page


def test_fr_1_4_zero_results_message(client):
    html = client.get("/places?cat=Cultural").get_data(as_text=True)
    assert "No places match your filter" in html


# ---- FR-2: place detail ------------------------------------------------------
def test_fr_2_1_and_2_2_detail_shows_fields_and_category(client):
    html = client.get("/places/1").get_data(as_text=True)
    assert "Temple A" in html
    assert "Religious" in html
    assert "Distance from Akuressa" in html and "Opening times" in html
    assert "Travel tips" in html


def test_fr_2_3_detail_has_add_to_plan_button(client):
    html = client.get("/places/1").get_data(as_text=True)
    assert "Add to my visit plan" in html


def test_detail_of_missing_place_is_404(client):
    r = client.get("/places/999")
    assert r.status_code == 404
    assert "Page not found" in r.get_data(as_text=True)


# ---- FR-3: map ---------------------------------------------------------------
def test_fr_3_1_map_page_contains_every_place(client):
    html = client.get("/map").get_data(as_text=True)
    assert 'id="map"' in html
    for name in ("Temple A", "Fort B", "Beach C"):
        assert name in html


def test_fr_3_3_detail_page_has_map(client):
    assert 'id="map"' in client.get("/places/1").get_data(as_text=True)


# ---- NFR-1: performance (server time, 100 places) ---------------------------
def test_nfr_1_pages_are_fast_with_100_places(app, client):
    with app.app_context():
        cat = Category.query.filter_by(name="Nature").first()
        db.session.add_all([
            Place(name=f"Bulk {i}", distance_km=1 + i % 24, latitude=5.9, longitude=80.5,
                  categories=[cat]) for i in range(100)
        ])
        db.session.commit()
    for url, limit_seconds in [("/places", 3), ("/places?cat=Nature", 2), ("/map", 4)]:
        start = time.perf_counter()
        r = client.get(url)
        elapsed = time.perf_counter() - start
        assert r.status_code == 200
        assert elapsed < limit_seconds, f"{url} took {elapsed:.2f}s"


# ---- 5.2 safety notice -------------------------------------------------------
def test_5_2_estimates_notice_on_detail_and_plan(client):
    for url in ("/places/1", "/plan"):
        assert "estimates" in client.get(url).get_data(as_text=True)