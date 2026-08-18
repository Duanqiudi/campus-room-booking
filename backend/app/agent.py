"""Deterministic booking agent used as the offline-safe orchestration layer."""

from __future__ import annotations

import re
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any

from .mcp_tools import (
    cancel_reservation,
    check_availability,
    create_reservation,
    get_my_reservations,
    list_resources,
)
from .services.rooms import list_rooms

YES = {"yes", "y", "confirm", "ok", "确认", "确定", "是", "提交"}
NO = {"no", "n", "cancel", "取消", "不要", "否"}
ACTIVITY_WORDS = {
    "badminton": ("badminton", "羽毛球"),
    "tennis": ("tennis", "网球"),
    "basketball": ("basketball", "篮球"),
}


def _local_midnight_ms(day: date) -> int:
    return int(datetime.combine(day, dt_time.min).timestamp() * 1000)


def _parse_day(text: str) -> date | None:
    today = date.today()
    lowered = text.lower()
    if "后天" in text or "day after tomorrow" in lowered:
        return today + timedelta(days=2)
    if "明天" in text or "tomorrow" in lowered:
        return today + timedelta(days=1)
    if "今天" in text or "today" in lowered:
        return today
    match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        try:
            return date(*(int(value) for value in match.groups()))
        except ValueError:
            return None
    return None


def _parse_time_range(text: str, day: date | None) -> tuple[int, int] | None:
    if day is None:
        return None
    time_text = re.sub(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", "", text)
    match = re.search(
        r"(?<!\d)(\d{1,2})(?:[:：](\d{2}))?\s*(?:-|~|—|–|到|至|to)\s*"
        r"(\d{1,2})(?:[:：](\d{2}))?(?!\d)",
        time_text,
        re.IGNORECASE,
    )
    if not match:
        return None
    start_h, start_m, end_h, end_m = match.groups()
    try:
        start = datetime.combine(day, dt_time(int(start_h), int(start_m or 0)))
        end = datetime.combine(day, dt_time(int(end_h), int(end_m or 0)))
    except ValueError:
        return None
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _find_resource(text: str) -> str | None:
    lowered = text.lower()
    rooms = list_rooms()
    for room in rooms:
        if room.room_id.lower() in lowered or room.name.lower() in lowered:
            return room.room_id
    for activity, words in ACTIVITY_WORDS.items():
        if any(word in lowered for word in words):
            matches = list_rooms(category="sports", activity=activity)
            if matches:
                return matches[0].room_id
    return None


def _parse_members(text: str, user_id: str) -> list[str]:
    ids = [value for value in re.findall(r"\bu_[a-zA-Z0-9_-]+\b", text) if value != user_id]
    count_match = re.search(r"(\d+)\s*(?:people|persons|人)", text, re.IGNORECASE)
    if count_match and not ids:
        total = max(1, int(count_match.group(1)))
        ids = [f"guest_{index}" for index in range(1, total)]
    return list(dict.fromkeys(ids))


def _format_time(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


class BookingAgent:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}

    def _response(
        self,
        session_id: str,
        status: str,
        message: str,
        pending_action: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "status": status,
            "message": message,
            "pending_action": pending_action,
            "data": data,
        }

    def _execute(self, session_id: str, action: dict[str, Any]) -> dict[str, Any]:
        try:
            intent = action["intent"]
            if intent == "book":
                result = create_reservation(**action["arguments"])
                booking = result["booking"]
                message = (
                    f"Booking completed: {booking['room_id']}, "
                    f"{_format_time(booking['start_ms'])}-{_format_time(booking['end_ms'])[-5:]}. "
                    f"Reference: {booking['booking_id']}."
                )
            elif intent == "cancel":
                result = cancel_reservation(**action["arguments"])
                message = f"Booking {result['booking_id']} has been cancelled."
            elif intent == "list":
                result = get_my_reservations(**action["arguments"])
                count = len(result["bookings"])
                message = f"You have {count} booking{'s' if count != 1 else ''}."
            elif intent == "availability":
                result = check_availability(**action["arguments"])
                count = len(result["reserved_slots"])
                message = f"{result['room_id']} has {count} reserved slot{'s' if count != 1 else ''} that day."
            else:
                result = list_resources()
                message = f"Found {len(result['resources'])} campus resources."
            self.sessions.pop(session_id, None)
            return self._response(session_id, "completed", message, data=result)
        except (ValueError, RuntimeError, LookupError, PermissionError) as exc:
            self.sessions.pop(session_id, None)
            return self._response(session_id, "failed", str(exc))

    def handle(self, session_id: str, user_id: str, message: str) -> dict[str, Any]:
        cleaned = message.strip()
        lowered = cleaned.lower()
        existing = self.sessions.get(session_id)

        if existing and existing.get("stage") == "confirmation":
            if lowered in YES:
                return self._execute(session_id, existing["action"])
            if lowered in NO:
                self.sessions.pop(session_id, None)
                return self._response(session_id, "completed", "The pending action was cancelled.")
            return self._response(
                session_id,
                "needs_confirmation",
                "Please reply yes/确认 to continue, or no/取消 to stop.",
                pending_action=existing["action"],
            )

        if existing and existing.get("stage") == "clarification":
            cleaned = f"{existing['original']} {cleaned}"
            lowered = cleaned.lower()

        if any(word in lowered for word in ("my booking", "my reservation", "我的预约", "我的预订")):
            return self._execute(
                session_id,
                {"intent": "list", "arguments": {"user_id": user_id}},
            )

        if any(word in lowered for word in ("cancel", "delete booking", "取消预约", "取消预订")):
            booking_match = re.search(r"\bbkg_[a-zA-Z0-9]+\b", cleaned)
            if not booking_match:
                self.sessions[session_id] = {"stage": "clarification", "original": cleaned}
                return self._response(session_id, "needs_clarification", "Which booking reference should I cancel?")
            action = {
                "intent": "cancel",
                "arguments": {"user_id": user_id, "booking_id": booking_match.group(0)},
            }
            self.sessions[session_id] = {"stage": "confirmation", "action": action}
            return self._response(
                session_id,
                "needs_confirmation",
                f"Confirm cancellation of {booking_match.group(0)}?",
                pending_action=action,
            )

        resource_id = _find_resource(cleaned)
        day = _parse_day(cleaned)
        time_range = _parse_time_range(cleaned, day)

        is_availability = any(
            word in lowered for word in ("available", "availability", "free slot", "空闲", "可用", "查时间")
        )
        if is_availability:
            missing = []
            if not resource_id:
                missing.append("resource")
            if not day:
                missing.append("date")
            if missing:
                self.sessions[session_id] = {"stage": "clarification", "original": cleaned}
                return self._response(
                    session_id,
                    "needs_clarification",
                    "Please provide " + " and ".join(missing) + ".",
                )
            return self._execute(
                session_id,
                {
                    "intent": "availability",
                    "arguments": {"room_id": resource_id, "day_start_ms": _local_midnight_ms(day)},
                },
            )

        is_booking = any(
            word in lowered for word in ("book", "reserve", "预约", "预订", "羽毛球", "网球", "篮球")
        )
        if is_booking:
            missing = []
            if not resource_id:
                missing.append("room or facility")
            if not day:
                missing.append("date")
            if not time_range:
                missing.append("time range")
            if missing:
                self.sessions[session_id] = {"stage": "clarification", "original": cleaned}
                return self._response(
                    session_id,
                    "needs_clarification",
                    "Please provide " + ", ".join(missing) + ".",
                )

            members = _parse_members(cleaned, user_id)
            room = next(room for room in list_rooms() if room.room_id == resource_id)
            if 1 + len(members) < room.min_attendance:
                self.sessions[session_id] = {"stage": "clarification", "original": cleaned}
                return self._response(
                    session_id,
                    "needs_clarification",
                    f"{resource_id} requires at least {room.min_attendance} attendees. Add member IDs or a people count.",
                )

            start_ms, end_ms = time_range
            arguments = {
                "user_id": user_id,
                "room_id": resource_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "purpose": "sports" if room.category == "sports" else "group study",
                "role": "staff" if "staff" in lowered or "教职工" in cleaned else "student",
                "members": members,
            }
            action = {"intent": "book", "arguments": arguments}
            self.sessions[session_id] = {"stage": "confirmation", "action": action}
            summary = f"{resource_id}, {_format_time(start_ms)}-{_format_time(end_ms)[-5:]}, {1 + len(members)} attendee(s)"
            return self._response(
                session_id,
                "needs_confirmation",
                f"Please confirm this booking: {summary}.",
                pending_action=action,
            )

        resources = list_resources()
        return self._response(
            session_id,
            "completed",
            "I can check availability, create or cancel a booking, and list your bookings.",
            data={"examples": [
                "Book D-1012G tomorrow 14:00-15:00 for 2 people",
                "明天 18:00-19:00 预约羽毛球，2人",
                "Show my bookings",
            ], "resource_count": len(resources["resources"])},
        )


agent = BookingAgent()
