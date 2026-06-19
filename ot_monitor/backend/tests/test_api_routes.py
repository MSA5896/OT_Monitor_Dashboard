"""
Tests for API authorization behavior.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app_state
from config import AppConfig
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class FakeStorage:
    async def export_csv(self, ot_id, start_iso, end_iso):
        return "time,value\n2026-01-01T00:00:00,1\n"

    async def query_telemetry(self, *args, **kwargs):
        return []

    async def query_alarms(self, *args, **kwargs):
        return []

    async def acknowledge_alarm(self, alarm_id, ack_by):
        return True


@pytest.fixture(autouse=True)
def fake_backend_state(monkeypatch):
    cfg = AppConfig()
    storage = FakeStorage()
    monkeypatch.setattr(app_state, "config", cfg)
    monkeypatch.setattr(app_state, "storage", storage)
    monkeypatch.setattr(app_state, "latest_payload", None)


def test_auth_me_requires_session(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_login_sets_session_cookie(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "OTAdmin2024"},
    )
    assert response.status_code == 200
    assert response.cookies.get("ot_session")


def test_export_csv_requires_auth(client):
    response = client.get("/export/csv")
    assert response.status_code == 401


def test_acknowledge_alarm_requires_auth(client):
    response = client.post("/alarms/1/acknowledge")
    assert response.status_code == 401


def test_export_csv_with_auth_returns_csv(client):
    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "OTAdmin2024"},
    )
    assert login.status_code == 200

    response = client.get("/export/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
