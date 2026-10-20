from models import Place
from routes.plan import build_itinerary


def _place(name, km, lat=5.95, lng=80.5, minutes=60):
    return Place(name=name, distance_km=km, latitude=lat, longitude=lng, visit_minutes=minutes)


# ---- FR-4.1 / 4.2: add, remove, list ----------------------------------------
def test_fr_4_1_add_place_and_see_it_in_plan(client):
    client.post("/plan/add/1")
    client.post("/plan/add/2")
    html = client.get("/plan").get_data(as_text=True)
    assert "Temple A" in html and "Fort B" in html


def test_fr_4_1_same_place_is_not_added_twice(client):
    client.post("/plan/add/1")
    client.post("/plan/add/1")
    with client.session_transaction() as s:
        assert s["plan"] == [1]


def test_fr_4_1_remove_place(client):
    client.post("/plan/add/1")
    client.post("/plan/add/2")
    client.post("/plan/remove/1")
    with client.session_transaction() as s:
        assert s["plan"] == [2]


def test_fr_4_4_reorder_places(client):
    client.post("/plan/add/1")
    client.post("/plan/add/2")
    client.post("/plan/move/1/down")
    with client.session_transaction() as s:
        assert s["plan"] == [2, 1]


def test_empty_plan_shows_helpful_message(client):
    assert "Your plan is empty" in client.get("/plan").get_data(as_text=True)


def test_deleted_place_is_dropped_from_plan(client):
    with client.session_transaction() as s:
        s["plan"] = [999]
    r = client.get("/plan")
    assert r.status_code == 200
    assert "Your plan is empty" in r.get_data(as_text=True)


# ---- FR-4.3: totals ----------------------------------------------------------
def test_fr_4_3_total_distance_and_count():
    # same coordinates => the leg between the two places is 0 km
    result = build_itinerary([_place("A", 10), _place("B", 15)], "09:00")
    assert len(result["stops"]) == 2
    assert result["total_km"] == 25.0          # 10 out + 0 between + 15 back


def test_planner_timing_uses_travel_stay_and_buffer():
    result = build_itinerary([_place("A", 10), _place("B", 15)], "09:00")
    first, second = result["stops"]
    assert first["arrive"] == "09:20" and first["leave"] == "10:20"   # 20 min travel, 60 min stay
    assert second["arrive"] == "10:35"                                 # +15 min buffer
    assert result["end"] == "12:20"                                    # 30 min drive home


def test_planner_warns_when_day_finishes_late():
    assert build_itinerary([_place("A", 10)], "17:00")["late"] is True
    assert build_itinerary([_place("A", 10)], "09:00")["late"] is False


def test_planner_bad_start_time_falls_back_to_0900():
    assert build_itinerary([_place("A", 10)], "not-a-time")["start"] == "09:00"


def test_empty_plan_itinerary():
    result = build_itinerary([], "09:00")
    assert result["stops"] == [] and result["total_km"] == 0


# ---- FR-4.5: single day only -------------------------------------------------
def test_fr_4_5_no_multi_day_option(client):
    client.post("/plan/add/1")
    html = client.get("/plan").get_data(as_text=True).lower()
    assert "day 2" not in html and "multi-day" not in html and "number of days" not in html