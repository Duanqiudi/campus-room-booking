from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .schemas import (
    RoomsResponse,
    ScheduleResponse,
    CreateBookingRequest,
    BookingResponse,
    MyBookingsResponse,
    OkResponse,
    AgentChatRequest,
    AgentChatResponse,
)
from .agent_graph import run_agent
from .services.rooms import list_rooms, room_exists
from .services.schedule import get_schedule
from .services.bookings import create_booking, list_my_bookings, cancel_booking


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Unified Campus Booking Service",
    version="1.0.0",
    lifespan=lifespan,
)


allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/rooms", response_model=RoomsResponse)
def api_rooms(
    campus: str | None = Query(default=None),
    floor: int | None = Query(default=None),
    category: str | None = Query(default=None, pattern="^(library|sports)$"),
    activity: str | None = Query(default=None),
):
    rooms = list_rooms(campus=campus, floor=floor, category=category, activity=activity)
    return {"rooms": rooms}


@app.get("/schedule", response_model=ScheduleResponse)
def api_schedule(
    room_id: str = Query(...),
    week_start_ms: int = Query(..., ge=0),
):
    if not room_exists(room_id):
        raise HTTPException(status_code=404, detail="room_not_found")

    ws, we, slots = get_schedule(room_id, week_start_ms)
    return {
        "room_id": room_id,
        "week_start_ms": ws,
        "week_end_ms": we,
        "slots": slots,
    }


@app.post("/bookings", response_model=BookingResponse, status_code=201)
def api_create_booking(req: CreateBookingRequest):
    if not room_exists(req.room_id):
        raise HTTPException(status_code=404, detail="room_not_found")

    try:
        booking = create_booking(
            user_id=req.user_id,
            room_id=req.room_id,
            start_ms=req.start_ms,
            end_ms=req.end_ms,
            purpose=req.purpose,
            role=req.role or "student",
            members=req.members,
        )
        return {"booking": booking}

    except ValueError as e:
        # e.g. one booking/day, min_attendance, advance days, duration limits, cancel rules, etc.
        raise HTTPException(status_code=422, detail=str(e))

    except RuntimeError:
        # conflict
        raise HTTPException(status_code=409, detail="time_conflict")


@app.get("/bookings/me", response_model=MyBookingsResponse)
def api_my_bookings(user_id: str = Query(...)):
    bookings = list_my_bookings(user_id=user_id)
    return {"bookings": bookings}


@app.delete("/bookings/{booking_id}", response_model=OkResponse)
def api_cancel_booking(
    booking_id: str = Path(...),
    user_id: str = Query(...),
):
    try:
        cancel_booking(user_id=user_id, booking_id=booking_id)
        return {"ok": True}

    except LookupError:
        raise HTTPException(status_code=404, detail="booking_not_found")

    except PermissionError:
        raise HTTPException(status_code=403, detail="forbidden")

    except ValueError as e:
        # e.g. cannot cancel after start time
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/agent/chat", response_model=AgentChatResponse)
def api_agent_chat(req: AgentChatRequest):
    return run_agent(
        session_id=req.session_id,
        user_id=req.user_id,
        message=req.message,
    )
