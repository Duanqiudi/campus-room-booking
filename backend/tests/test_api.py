from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

os.environ["BOOKING_DB_PATH"] = str(Path(__file__).with_name("test_booking.db"))

from fastapi.testclient import TestClient

from app.main import app


def setup_module() -> None:
    db_path = Path(os.environ["BOOKING_DB_PATH"])
    db_path.unlink(missing_ok=True)


def teardown_module() -> None:
    Path(os.environ["BOOKING_DB_PATH"]).unlink(missing_ok=True)


def test_health_and_resources() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"ok": True}
        response = client.get("/rooms", params={"category": "sports"})
        assert response.status_code == 200
        assert {room["activity"] for room in response.json()["rooms"]} >= {
            "badminton",
            "tennis",
            "basketball",
        }


def test_agent_clarifies_confirms_and_books() -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with TestClient(app) as client:
        first = client.post(
            "/agent/chat",
            json={
                "session_id": "test-agent",
                "user_id": "agent_user",
                "message": f"Book BAD-01 on {tomorrow} 14:00-15:00",
            },
        ).json()
        assert first["status"] == "needs_clarification"

        second = client.post(
            "/agent/chat",
            json={
                "session_id": "test-agent",
                "user_id": "agent_user",
                "message": "2 people",
            },
        ).json()
        assert second["status"] == "needs_confirmation"

        third = client.post(
            "/agent/chat",
            json={"session_id": "test-agent", "user_id": "agent_user", "message": "yes"},
        ).json()
        assert third["status"] == "completed"
        assert third["data"]["booking"]["room_id"] == "BAD-01"


def test_backend_rejects_conflicts() -> None:
    tomorrow = date.today() + timedelta(days=1)
    start_ms = int(datetime.combine(tomorrow, time(16)).timestamp() * 1000)
    payload = {
        "role": "student",
        "room_id": "D-1012G",
        "start_ms": start_ms,
        "end_ms": start_ms + 30 * 60 * 1000,
        "purpose": "test",
        "members": ["partner"],
    }
    with TestClient(app) as client:
        first = client.post("/bookings", json={**payload, "user_id": "conflict_a"})
        second = client.post("/bookings", json={**payload, "user_id": "conflict_b"})
        assert first.status_code == 201
        assert second.status_code == 409
