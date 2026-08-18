from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class Room(BaseModel):
    room_id: str
    campus: str
    building: str
    floor: int
    name: str
    capacity: int
    min_attendance: int
    features: List[str] = Field(default_factory=list)
    is_active: bool
    category: Literal["library", "sports"] = "library"
    activity: Optional[str] = None

class RoomsResponse(BaseModel):
    rooms: List[Room]


SlotStatus = Literal["reserved", "closed"]  # 先做这两个就够了；expired 可由前端用 now_ms 标灰


class Slot(BaseModel):
    start_ms: int
    end_ms: int
    status: SlotStatus
    booking_id: Optional[str] = None


class ScheduleResponse(BaseModel):
    room_id: str
    week_start_ms: int
    week_end_ms: int
    slots: List[Slot]


class CreateBookingRequest(BaseModel):
    user_id: str
    role: Optional[Literal["student", "staff"]] = "student"
    room_id: str
    start_ms: int
    end_ms: int
    purpose: Optional[str] = None
    members: List[str] = Field(default_factory=list)  # 组员（学号/ID/用户名都行）


class Booking(BaseModel):
    booking_id: str
    user_id: str
    room_id: str
    start_ms: int
    end_ms: int
    status: Literal["active", "cancelled"]
    created_at_ms: int
    purpose: Optional[str] = None
    members: List[str] = Field(default_factory=list)


class BookingResponse(BaseModel):
    booking: Booking


class MyBookingsResponse(BaseModel):
    bookings: List[Booking]


class OkResponse(BaseModel):
    ok: bool = True


class AgentChatRequest(BaseModel):
    session_id: str = "demo"
    user_id: str = "u_001"
    message: str = Field(min_length=1, max_length=1000)


class AgentChatResponse(BaseModel):
    session_id: str
    status: Literal["needs_clarification", "needs_confirmation", "completed", "failed"]
    message: str
    pending_action: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
