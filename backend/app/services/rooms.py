import json
from typing import Optional, List
from ..db import get_conn
from ..schemas import Room


def list_rooms(
    campus: Optional[str] = None,
    floor: Optional[int] = None,
    category: Optional[str] = None,
    activity: Optional[str] = None,
) -> List[Room]:
    sql = "SELECT * FROM rooms WHERE is_active=1"
    params = []

    if campus:
        sql += " AND campus=?"
        params.append(campus)
    if floor is not None:
        sql += " AND floor=?"
        params.append(floor)
    if category:
        sql += " AND category=?"
        params.append(category)
    if activity:
        sql += " AND activity=?"
        params.append(activity)

    sql += " ORDER BY campus, building, floor, room_id"

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        rooms: List[Room] = []
        for r in rows:
            features = json.loads(r["features"] or "[]")
            rooms.append(
                Room(
                    room_id=r["room_id"],
                    campus=r["campus"],
                    building=r["building"],
                    floor=int(r["floor"]),
                    name=r["name"],
                    capacity=int(r["capacity"]),
                    min_attendance=int(r["min_attendance"]),
                    features=features,
                    is_active=bool(r["is_active"]),
                    category=r["category"],
                    activity=r["activity"],
                )
            )
        return rooms
    finally:
        conn.close()


def room_exists(room_id: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT room_id FROM rooms WHERE room_id=? AND is_active=1",
            (room_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
