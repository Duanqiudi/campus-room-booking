"""Tool boundary shared by the HTTP agent and the optional MCP server."""

from __future__ import annotations

from typing import Any

from .services.bookings import cancel_booking, create_booking, list_my_bookings
from .services.rooms import list_rooms
from .services.schedule import get_schedule


def list_resources(
    campus: str | None = None,
    category: str | None = None,
    activity: str | None = None,
) -> dict[str, Any]:
    rooms = list_rooms(campus=campus, category=category, activity=activity)
    return {"resources": [room.model_dump() for room in rooms]}


def check_availability(room_id: str, day_start_ms: int) -> dict[str, Any]:
    day_end_ms = day_start_ms + 24 * 60 * 60 * 1000
    _, _, slots = get_schedule(room_id, day_start_ms)
    relevant = [
        slot.model_dump()
        for slot in slots
        if slot.start_ms < day_end_ms and slot.end_ms > day_start_ms
    ]
    return {
        "room_id": room_id,
        "day_start_ms": day_start_ms,
        "day_end_ms": day_end_ms,
        "reserved_slots": relevant,
    }


def create_reservation(**kwargs: Any) -> dict[str, Any]:
    booking = create_booking(**kwargs)
    return {"booking": booking.model_dump()}


def get_my_reservations(user_id: str) -> dict[str, Any]:
    bookings = list_my_bookings(user_id)
    return {"bookings": [booking.model_dump() for booking in bookings]}


def cancel_reservation(user_id: str, booking_id: str) -> dict[str, Any]:
    cancel_booking(user_id=user_id, booking_id=booking_id)
    return {"ok": True, "booking_id": booking_id}
