PUBLIC_URLS = ["/", "/places", "/places?cat=Nature", "/map", "/plan", "/admin/login"]


def test_5_4_2_empty_database_never_crashes(empty_client):
    for url in PUBLIC_URLS:
        assert empty_client.get(url).status_code == 200, url


def test_empty_database_shows_friendly_messages(empty_client):
    assert "No places have been added yet" in empty_client.get("/").get_data(as_text=True)
    assert "No places match your filter" in empty_client.get("/places").get_data(as_text=True)


def test_custom_404_page(client):
    r = client.get("/this-page-does-not-exist")
    assert r.status_code == 404
    html = r.get_data(as_text=True)
    assert "Page not found" in html and "Back to home" in html


def test_expired_or_missing_csrf_token_gives_friendly_page(csrf_client):
    r = csrf_client.post("/admin/login", data={"username": "admin", "password": "x"})
    assert r.status_code == 400
    assert "This form has expired" in r.get_data(as_text=True)


def test_security_headers_present(client):
    h = client.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "SAMEORIGIN"
    assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_session_cookie_is_httponly(client):
    r = client.post("/plan/add/1")
    cookies = " ".join(r.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookies and "SameSite=Lax" in cookies


def test_navigation_present_on_every_public_page(client):
    for url in ["/", "/places", "/places/1", "/map", "/plan"]:
        html = client.get(url).get_data(as_text=True)
        for link in ("/places", "/map", "/plan"):
            assert f'href="{link}"' in html, f"{url} missing nav link {link}"