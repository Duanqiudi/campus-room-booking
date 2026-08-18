from __future__ import annotations

from typing import List
from ..db import get_conn
from ..schemas import Slot


WEEK_MS = 7 * 24 * 60 * 60 * 1000


def get_schedule(room_id: str, week_start_ms: int) -> tuple[int, int, List[Slot]]:
    week_end_ms = week_start_ms + WEEK_MS

    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT booking_id, start_ms, end_ms
            FROM bookings
            WHERE room_id=? AND status='active'
              AND NOT (? <= start_ms OR ? >= end_ms)
            ORDER BY start_ms ASC
            """,
            (room_id, week_end_ms, week_start_ms),
        ).fetchall()

        slots = [
            Slot(
                start_ms=int(r["start_ms"]),
                end_ms=int(r["end_ms"]),
                status="reserved",
                booking_id=r["booking_id"],
            )
            for r in rows
        ]
        return week_start_ms, week_end_ms, slots
    finally:
        conn.close()