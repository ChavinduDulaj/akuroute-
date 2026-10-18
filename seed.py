from getpass import getpass
from app import create_app
from models import db, Category, Place, Admin

# Placeholder coordinates (roughly central Akuressa). REPLACE each pair with the
# real latitude/longitude copied from Google Maps before you demo!
PLACEHOLDER = (5.9344, 80.4705)

PLACES = [
    {
        "name": "Weherahena Buddhist Temple",
        "distance_km": 13, "categories": ["Religious"],
        "description": "Underground temple complex near Matara, notable for its large seated Buddha statue and painted tunnel depicting the Buddha's life.",
        "opening_times": "Daily, approx. 8:00 AM - 5:00 PM (verify)",
        "travel_tips": "Dress modestly and remove shoes. Allow time for the tunnel walk.",
        "coords": (5.952974853776219, 80.57537431447317), "visit_minutes": 60,
    },
    {
        "name": "Matara Star Fort",
        "distance_km": 15, "categories": ["Heritage"],
        "description": "Small Dutch-era fort in Matara town, a compact colonial heritage landmark with historical exhibits.",
        "opening_times": "Daily, approx. 8:30 AM - 5:00 PM (verify)",
        "travel_tips": "Short visit; combine with other Matara town stops.",
        "coords": (5.948528659006749, 80.54838555270216), "visit_minutes": 45,
    },
    {
        "name": "Dondra Head Lighthouse",
        "distance_km": 21, "categories": ["Heritage", "Nature"],
        "description": "Sri Lanka's tallest lighthouse, marking the island's southernmost point with coastal views.",
        "opening_times": "Daily, approx. 8:00 AM - 5:00 PM (verify)",
        "travel_tips": "Best in the morning or late afternoon. Bring water and sun protection.",
        "coords": (5.921390963862682, 80.59402252078384), "visit_minutes": 60,
    },
    {
        "name": "Polhena Beach",
        "distance_km": 16, "categories": ["Nature"],
        "description": "A calm, shallow reef beach near Matara popular for swimming and snorkelling.",
        "opening_times": "Open all day",
        "travel_tips": "Calmest in the morning. Bring a towel and sunscreen.",
        "coords": (5.936402184022565, 80.52629912174365), "visit_minutes": 90,
    },
    {
        "name": "Martin Wickramasinghe Folk Museum",
        "distance_km": 20, "categories": ["Heritage"],
        "description": "A cultural museum in Koggala showcasing the life, works, traditional lifestyle and folk heritage of writer Martin Wickramasinghe.",
        "opening_times": "Daily, approx. 8:00 AM - 5:00 PM (verify)",
        "travel_tips": "Entrance fee applies. Allow about an hour to see the exhibits.",
        "coords": (5.990239787974267, 80.32797356777161), "visit_minutes": 60,
    },
    {
        "name": "Kekanadura Sri Muthumariamman Kovil",
        "distance_km": 10, "categories": ["Religious", "Cultural"],
        "description": "Active Hindu kovil known for its colourful gopuram and annual festival processions.",
        "opening_times": "Daily, approx. 6:00 AM - 7:00 PM (verify)",
        "travel_tips": "Dress modestly and remove footwear before entering.",
        "coords": (5.9508677997056205, 80.54342133564782), "visit_minutes": 30,
    },
    {
        "name": "Thalahagama Diya Bubula (Natural Spring)",
        "distance_km": 8, "categories": ["Nature"],
        "description": "A natural freshwater spring beside paddy fields with local folklore attached to its origin.",
        "opening_times": "Open all day",
        "travel_tips": "Wear sandals; the area around the spring can be muddy.",
        "coords": (6.130376819876642, 80.5271650067583), "visit_minutes": 30,
    },
    {
        "name": "Gunawardana Tea Factory, Akuressa",
        "distance_km": 2, "categories": ["Cultural"],
        "description": "Working low-country tea factory offering a look at withering, rolling and firing of tea leaves.",
        "opening_times": "Weekdays, approx. 8:00 AM - 4:00 PM (verify)",
        "travel_tips": "Call ahead to confirm tours. Closed machinery days may vary.",
        "coords": (6.130653608488874, 80.50485089503178), "visit_minutes": 45,
    },
    {
        "name": "Kirala Kele Wetland Sanctuary",
        "distance_km": 18, "categories": ["Nature"],
        "description": "Freshwater marsh and mangrove sanctuary near Matara, home to varied birdlife.",
        "opening_times": "Daily, early morning to evening (verify)",
        "travel_tips": "Best for birdwatching early in the morning. Bring binoculars and insect repellent.",
        "coords": (5.976253569538634, 80.52710294648628), "visit_minutes": 90,
    },
    {
        "name": "Kamburupitiya Town & Nilwala Riverside",
        "distance_km": 9, "categories": ["Cultural", "Nature"],
        "description": "Small riverside town on the Nilwala River, a gateway to the surrounding tea and rubber estates.",
        "opening_times": "Open all day",
        "travel_tips": "Good for a relaxed stop and local snacks on the way to other places.",
        "coords": (6.080108851137117, 80.5662347428082), "visit_minutes": 45,
    },
]

CATEGORY_NAMES = ["Religious", "Heritage", "Nature", "Cultural"]

app = create_app()

with app.app_context():
    db.create_all()

    # Categories (skip any that already exist, so the script is safe to re-run)
    cats = {}
    for name in CATEGORY_NAMES:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name)
            db.session.add(cat)
        cats[name] = cat

    # Places
    added = 0
    for p in PLACES:
        if Place.query.filter_by(name=p["name"]).first():
            continue
        lat, lng = p["coords"]
        db.session.add(Place(
            name=p["name"], distance_km=p["distance_km"],
            description=p["description"], opening_times=p["opening_times"],
            travel_tips=p["travel_tips"], latitude=lat, longitude=lng,
            visit_minutes=p["visit_minutes"],
            categories=[cats[c] for c in p["categories"]],
        ))
        added += 1

    # Admin account (password is typed in, never stored in code)
    if not Admin.query.filter_by(username="admin").first():
        pw = getpass("Choose an admin password: ")
        admin = Admin(username="admin")
        admin.set_password(pw)
        db.session.add(admin)
        print("Admin account created.")

    db.session.commit()
    print(f"Done. {added} places added. Total places: {Place.query.count()}")