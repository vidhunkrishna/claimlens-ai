import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_frontend_index_html_serving():
    """
    Test GET / with accept: text/html returns 200 OK and serves index.html content.
    """
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ClaimLens AI" in response.text
    assert "<!DOCTYPE html>" in response.text

def test_static_assets_serving():
    """
    Test GET /static/styles.css and /static/app.js serve 200 OK with correct assets.
    """
    res_css = client.get("/static/styles.css")
    assert res_css.status_code == 200
    assert "var(--primary-indigo)" in res_css.text

    res_js = client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "analyzePreset" in res_js.text
