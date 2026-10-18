import math
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, flash)
from models import db, Place

bp = Blueprint("plan", __name__)

# Planning assumptions (estimates only, see SRS 5.2)
AVG_SPEED_KMH = 30        # average travel speed on local roads
ROAD_FACTOR = 1.3         # straight-line distance -> approximate road distance
BUFFER_MIN = 15           # extra time allowed after each stop
LATEST_END = "18:00"      # warn if the day finishes later than this


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance in km between two coordinates."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fmt_duration(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def build_itinerary(places, start_text):
    """Turn an ordered list of places into a timed one-day itinerary."""
    try:
        clock = datetime.strptime(start_text, "%H:%M")
    except (TypeError, ValueError):
        clock = datetime.strptime("09:00", "%H:%M")
    start_time = clock
    stops = []
    total_km = 0.0
    prev = None

    for i, p in enumerate(places, start=1):
        if prev is None:
            leg_km = p.distance_km                       # from Akuressa
        else:
            leg_km = haversine_km(prev.latitude, prev.longitude,
                                  p.latitude, p.longitude) * ROAD_FACTOR
        travel_min = round(leg_km / AVG_SPEED_KMH * 60)
        clock += timedelta(minutes=travel_min)
        arrive = clock
        clock += timedelta(minutes=p.visit_minutes or 60)
        leave = clock
        clock += timedelta(minutes=BUFFER_MIN)           # buffer before moving on
        total_km += leg_km
        stops.append({
            "index": i, "place": p,
            "leg_km": round(leg_km, 1), "travel_min": travel_min,
            "arrive": arrive.strftime("%H:%M"), "leave": leave.strftime("%H:%M"),
        })
        prev = p

    return_km = 0.0
    end_time = start_time
    if places:
        return_km = places[-1].distance_km               # back to Akuressa
        clock += timedelta(minutes=round(return_km / AVG_SPEED_KMH * 60))
        end_time = clock
        total_km += return_km

    total_minutes = (end_time - start_time).total_seconds() / 60
    return {
        "stops": stops,
        "start": start_time.strftime("%H:%M"),
        "end": end_time.strftime("%H:%M"),
        "return_km": round(return_km, 1),
        "total_km": round(total_km, 1),
        "duration": fmt_duration(total_minutes),
        "late": end_time.strftime("%H:%M") > LATEST_END,
        "latest_end": LATEST_END,
    }


def _ids():
    return list(session.get("plan", []))


@bp.route("/plan")
def view():
    ids = _ids()
    found = {}
    if ids:
        found = {p.id: p for p in Place.query.filter(Place.id.in_(ids)).all()}
    ordered = [found[i] for i in ids if i in found]
    session["plan"] = [p.id for p in ordered]            # drop places deleted by the admin
    itinerary = build_itinerary(ordered, request.args.get("start", "09:00"))
    return render_template("plan.html", itinerary=itinerary)


@bp.route("/plan/add/<int:pid>", methods=["POST"])
def add(pid):
    place = db.get_or_404(Place, pid)
    ids = _ids()
    if pid in ids:
        flash(f"{place.name} is already in your plan.", "info")
    else:
        ids.append(pid)
        session["plan"] = ids
        flash(f"{place.name} was added to your plan.", "success")
    return redirect(url_for("public.place_detail", place_id=pid))


@bp.route("/plan/remove/<int:pid>", methods=["POST"])
def remove(pid):
    session["plan"] = [i for i in _ids() if i != pid]
    flash("Place removed from your plan.", "info")
    return redirect(url_for("plan.view"))


@bp.route("/plan/move/<int:pid>/<direction>", methods=["POST"])
def move(pid, direction):
    ids = _ids()
    if pid in ids and direction in ("up", "down"):
        i = ids.index(pid)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
            session["plan"] = ids
    return redirect(url_for("plan.view"))


@bp.route("/plan/clear", methods=["POST"])
def clear():
    session.pop("plan", None)
    flash("Your plan has been cleared.", "info")
    return redirect(url_for("plan.view"))