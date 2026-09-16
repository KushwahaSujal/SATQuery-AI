"""Q-021: API keys for the cloud backend."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MISSING = "/api/results/q020-no-such-job"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_no_keys_configured_leaves_api_open(client, monkeypatch):
    monkeypatch.delenv("SATQUERY_API_KEYS", raising=False)
    assert client.get(MISSING).status_code == 404


@pytest.mark.parametrize("how", ["bearer", "header", "query"])
def test_valid_key_in_any_accepted_form_passes(client, monkeypatch, how):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one, k-two")
    if how == "bearer":
        r = client.get(MISSING, headers={"Authorization": "Bearer k-two"})
    elif how == "header":
        r = client.get(MISSING, headers={"X-API-Key": "k-one"})
    else:
        r = client.get(f"{MISSING}?key=k-one")
    assert r.status_code == 404


def test_missing_or_wrong_key_is_401_with_cors_header(client, monkeypatch):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one")
    origin = {"Origin": "http://localhost:3000"}
    for headers in (origin, {**origin, "Authorization": "Bearer nope"}):
        r = client.get(MISSING, headers=headers)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_health_stays_open_with_keys(client, monkeypatch):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one")
    assert client.get("/api/health").status_code == 200


def test_non_ascii_key_is_401_not_500(client, monkeypatch):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one")
    r = client.get(f"{MISSING}?key=é")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
