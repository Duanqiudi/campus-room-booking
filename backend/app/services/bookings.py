from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional, Literal

from ..db import get_conn
from ..schemas import Booking

# ---------- Policy (P0) ----------
OPEN_HOUR = 9
CLOSE_HOUR = 21

MIN_MINUTES = 30
STUDENT_MAX_MINUTES = 180
STAFF_MAX_MINUTES = 360

ADVANCE_DAYS = 3  # can book up to 3 days in advance
CELL_MINUTES = 30
CELL_MS = CELL_MINUTES * 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000

Role = Literal["student", "staff"]


# ---------- time helpers ----------
def _now_ms() -> int:
    return int(time.time() * 1000)


def _duration_minutes(start_ms: int, end_ms: int) -> int:
    return int((end_ms - start_ms) / 60000)


def _ms_to_local_struct(ms: int) -> time.struct_time:
    return time.localtime(ms / 1000)


def _ms_to_local_hm(ms: int) -> tuple[int, int]:
    t = _ms_to_local_struct(ms)
    return t.tm_hour, t.tm_min


def _local_day_start_ms(ms: int) -> int:
    """Return local date's 00:00:00 (ms) for the given ms."""
    t = _ms_to_local_struct(ms)
    # local midnight
    dt = (t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1)
    return int(time.mktime(dt) * 1000)


# ---------- validation ----------
def validate_booking_time(start_ms: int, end_ms: int, role: Role = "student") -> None:
    if start_ms >= end_ms:
        raise ValueError("start_ms must be < end_ms")

    # 30min alignment
    if (start_ms % CELL_MS) != 0 or (end_ms % CELL_MS) != 0:
        raise ValueError("start_ms/end_ms must align to 30-minute boundaries")

    # no cross-day
    start_day = _ms_to_local_struct(start_ms).tm_yday
    end_day = _ms_to_local_struct(end_ms).tm_yday
    if start_day != end_day:
        raise ValueError("booking must not跨天 (same day only)")

    # within opening hours
    sh, sm = _ms_to_local_hm(start_ms)
    eh, em = _ms_to_local_hm(end_ms)
    if (sh < OPEN_HOUR) or (eh > CLOSE_HOUR) or (eh == CLOSE_HOUR and em > 0):
        raise ValueError(f"booking must be within {OPEN_HOUR:02d}:00-{CLOSE_HOUR:02d}:00")

    # duration rules
    dur = _duration_minutes(start_ms, end_ms)
    if dur < MIN_MINUTES:
        raise ValueError(f"duration must be >= {MIN_MINUTES} minutes")

    max_minutes = STUDENT_MAX_MINUTES if role == "student" else STAFF_MAX_MINUTES
    if dur > max_minutes:
        raise ValueError(f"duration must be <= {max_minutes} minutes for role={role}")


def _normalize_members(user_id: str, members: Optional[List[str]]) -> List[str]:
    raw = members or []
    # strip + drop empties
    cleaned = []
    for x in raw:
        s = str(x).strip()
        if s:
            cleaned.append(s)

    # ensure primary booker included
    cleaned = [user_id] + cleaned

    # de-dup keep order
    seen = set()
    uniq = []
    for m in cleaned:
        if m in seen:
            continue
        seen.add(m)
        uniq.append(m)
    return uniq


# ---------- queries ----------
def _has_conflict(conn, room_id: str, start_ms: int, end_ms: int) -> bool:
    # overlap: NOT (end<=other.start OR start>=other.end)
    row = conn.execute(
        """
        SELECT 1 FROM bookings
        WHERE room_id=? AND status='active'
          AND NOT (? <= start_ms OR ? >= end_ms)
        LIMIT 1
        """,
        (room_id, end_ms, start_ms),
    ).fetchone()
    return row is not None


def _user_has_booking_that_day(conn, user_id: str, day_start_ms: int) -> bool:
    day_end_ms = day_start_ms + DAY_MS
    row = conn.execute(
        """
        SELECT 1 FROM bookings
        WHERE user_id=? AND status='active'
          AND start_ms >= ? AND start_ms < ?
        LIMIT 1
        """,
        (user_id, day_start_ms, day_end_ms),
    ).fetchone()
    return row is not None


def _get_room_min_attendance(conn, room_id: str) -> int:
    row = conn.execute(
        "SELECT min_attendance FROM rooms WHERE room_id=? AND is_active=1",
        (room_id,),
    ).fetchone()
    if not row:
        raise ValueError("room_not_found")
    return int(row["min_attendance"])


# ---------- public APIs ----------
def create_booking(
    user_id: str,
    room_id: str,
    start_ms: int,
    end_ms: int,
    purpose: Optional[str],
    role: Role = "student",
    members: Optional[List[str]] = None,
) -> Booking:
    # base validation
    validate_booking_time(start_ms, end_ms, role=role)

    now = _now_ms()

    # cannot book in the past (allow tiny clock skew)
    if start_ms < now - 60_000:
        raise ValueError("cannot book a past timeslot")

    # can book up to ADVANCE_DAYS in advance
    if start_ms > now + ADVANCE_DAYS * DAY_MS:
        raise ValueError(f"can only book up to {ADVANCE_DAYS} days in advance")

    members_list = _normalize_members(user_id, members)

    booking_id = "bkg_" + uuid.uuid4().hex[:12]
    created_at = now

    conn = get_conn()
    try:
        # Stronger consistency: lock write transaction
        conn.execute("BEGIN IMMEDIATE;")

        # room rule: min attendance
        min_att = _get_room_min_attendance(conn, room_id)
        if len(members_list) < min_att:
            conn.rollback()
            raise ValueError(f"need at least {min_att} members for this room")

        # one booking per day
        day_start_ms = _local_day_start_ms(start_ms)
        if _user_has_booking_that_day(conn, user_id, day_start_ms):
            conn.rollback()
            raise ValueError("only one booking per day")

        # conflict check
        if _has_conflict(conn, room_id, start_ms, end_ms):
            conn.rollback()
            raise RuntimeError("conflict")

        conn.execute(
            """
            INSERT INTO bookings(
              booking_id, user_id, role, room_id,
              start_ms, end_ms, status, purpose, members_json,
              created_at_ms, updated_at_ms
            )
            VALUES(?,?,?,?,?,?,'active',?,?,?,?)
            """,
            (
                booking_id,
                user_id,
                role,
                room_id,
                start_ms,
                end_ms,
                purpose,
                json.dumps(members_list, ensure_ascii=False),
                created_at,
                created_at,
            ),
        )
        conn.commit()

        return Booking(
            booking_id=booking_id,
            user_id=user_id,
            room_id=room_id,
            start_ms=start_ms,
            end_ms=end_ms,
            status="active",
            created_at_ms=created_at,
            purpose=purpose,
            members=members_list,
        )
    finally:
        conn.close()


def list_my_bookings(user_id: str) -> List[Booking]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT booking_id, user_id, room_id, start_ms, end_ms, status,
                   created_at_ms, purpose, members_json
            FROM bookings
            WHERE user_id=?
            ORDER BY start_ms ASC
            """,
            (user_id,),
        ).fetchall()

        return [
            Booking(
                booking_id=r["booking_id"],
                user_id=r["user_id"],
                room_id=r["room_id"],
                start_ms=int(r["start_ms"]),
                end_ms=int(r["end_ms"]),
                status=r["status"],
                created_at_ms=int(r["created_at_ms"]),
                purpose=r["purpose"],
                members=json.loads(r["members_json"] or "[]"),
            )
            for r in rows
        ]
    finally:
        conn.close()


def cancel_booking(user_id: str, booking_id: str) -> None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id, status, start_ms FROM bookings WHERE booking_id=?",
            (booking_id,),
        ).fetchone()

        if row is None:
            raise LookupError("not_found")
        if row["user_id"] != user_id:
            raise PermissionError("forbidden")
        if row["status"] != "active":
            return  # already cancelled -> ok

        now = _now_ms()
        if now >= int(row["start_ms"]):
            raise ValueError("cannot cancel after start time")

        conn.execute(
            "UPDATE bookings SET status='cancelled', updated_at_ms=? WHERE booking_id=?",
            (now, booking_id),
        )
        conn.commit()
    finally:
        conn.close()
