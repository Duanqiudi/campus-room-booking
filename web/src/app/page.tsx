"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Bot,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Library,
  LoaderCircle,
  Menu,
  MessageSquareText,
  RefreshCw,
  Send,
  Trophy,
  UserRound,
  X,
} from "lucide-react";
import type { AgentResponse, Booking, Room, ScheduleResponse, Slot } from "@/lib/types";
import { fmtDayLabel, fmtTimeLabel, getWeekStartMsLocal } from "@/lib/time";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const USER_ID = "u_001";
const SESSION_ID = "web-demo";
const DAY_MS = 24 * 60 * 60 * 1000;
const CELL_MS = 30 * 60 * 1000;
const OPEN_MIN = 9 * 60;
const CELL_COUNT = 24;

type View = "assistant" | "schedule" | "bookings";
type Message = { id: number; role: "user" | "assistant"; text: string; status?: AgentResponse["status"] };

function overlaps(aStart: number, aEnd: number, bStart: number, bEnd: number) {
  return !(aEnd <= bStart || aStart >= bEnd);
}

function reserved(cellStart: number, cellEnd: number, slots: Slot[]) {
  return slots.some(
    (slot) => slot.status === "reserved" && overlaps(cellStart, cellEnd, slot.start_ms, slot.end_ms),
  );
}

function formatDateTime(ms: number) {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(ms));
}

function tomorrowLabel() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().slice(0, 10);
}

export default function Home() {
  const [view, setView] = useState<View>("assistant");
  const [mobileNav, setMobileNav] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [category, setCategory] = useState<"library" | "sports">("library");
  const [roomId, setRoomId] = useState("D-1012G");
  const [weekStartMs, setWeekStartMs] = useState(() => getWeekStartMsLocal());
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "assistant",
      text: "Tell me what you need. I can find a room or sports facility, check availability, and complete the booking after you confirm.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);

  const loadRooms = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/rooms`);
      if (!response.ok) throw new Error("rooms_failed");
      const payload = (await response.json()) as { rooms: Room[] };
      setRooms(payload.rooms);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  const loadSchedule = useCallback(async () => {
    setScheduleLoading(true);
    try {
      const params = new URLSearchParams({ room_id: roomId, week_start_ms: String(weekStartMs) });
      const response = await fetch(`${API_BASE}/schedule?${params}`);
      if (!response.ok) throw new Error("schedule_failed");
      setSchedule((await response.json()) as ScheduleResponse);
      setOnline(true);
    } catch {
      setSchedule(null);
      setOnline(false);
    } finally {
      setScheduleLoading(false);
    }
  }, [roomId, weekStartMs]);

  const loadBookings = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/bookings/me?user_id=${USER_ID}`);
      if (!response.ok) throw new Error("bookings_failed");
      const payload = (await response.json()) as { bookings: Booking[] };
      setBookings(payload.bookings);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    void loadRooms();
  }, [loadRooms]);

  useEffect(() => {
    void loadSchedule();
  }, [loadSchedule]);

  useEffect(() => {
    if (view === "bookings") void loadBookings();
  }, [loadBookings, view]);

  const visibleRooms = useMemo(
    () => rooms.filter((room) => room.category === category),
    [category, rooms],
  );

  useEffect(() => {
    if (visibleRooms.length && !visibleRooms.some((room) => room.room_id === roomId)) {
      setRoomId(visibleRooms[0].room_id);
    }
  }, [roomId, visibleRooms]);

  const sendMessage = useCallback(
    async (rawMessage: string) => {
      const message = rawMessage.trim();
      if (!message || sending) return;
      const id = Date.now();
      setMessages((current) => [...current, { id, role: "user", text: message }]);
      setInput("");
      setSending(true);
      try {
        const response = await fetch(`${API_BASE}/agent/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: SESSION_ID, user_id: USER_ID, message }),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = (await response.json()) as AgentResponse;
        setMessages((current) => [
          ...current,
          { id: id + 1, role: "assistant", text: payload.message, status: payload.status },
        ]);
        setPendingConfirmation(payload.status === "needs_confirmation");
        if (payload.status === "completed") {
          void loadSchedule();
          void loadBookings();
        }
        setOnline(true);
      } catch (error) {
        const detail = error instanceof Error ? error.message : "request_failed";
        setMessages((current) => [
          ...current,
          { id: id + 1, role: "assistant", text: `The booking service is unavailable (${detail}).`, status: "failed" },
        ]);
        setOnline(false);
      } finally {
        setSending(false);
      }
    },
    [loadBookings, loadSchedule, sending],
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    void sendMessage(input);
  }

  function openSlot(startMs: number) {
    const endMs = startMs + CELL_MS;
    const prompt = `Book ${roomId} on ${new Date(startMs).toISOString().slice(0, 10)} ${new Date(startMs)
      .toTimeString()
      .slice(0, 5)}-${new Date(endMs).toTimeString().slice(0, 5)} for 2 people`;
    setInput(prompt);
    setView("assistant");
  }

  const navItems: { id: View; label: string; icon: typeof Bot }[] = [
    { id: "assistant", label: "Booking assistant", icon: MessageSquareText },
    { id: "schedule", label: "Resource schedule", icon: CalendarDays },
    { id: "bookings", label: "My bookings", icon: UserRound },
  ];

  const dayHeaders = Array.from({ length: 7 }, (_, index) => weekStartMs + index * DAY_MS);
  const timeLabels = Array.from({ length: CELL_COUNT }, (_, index) => fmtTimeLabel(OPEN_MIN + index * 30));
  const slots = schedule?.slots ?? [];
  const quickPrompts = [
    `Book D-1012G on ${tomorrowLabel()} 14:00-15:00 for 2 people`,
    "Book badminton tomorrow 18:00-19:00 for 2 people",
    "Show my bookings",
  ];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><CalendarDays size={19} /></div>
          <div><strong>Campus Reserve</strong><span>Unified booking</span></div>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={view === item.id ? "nav-item active" : "nav-item"}
                onClick={() => { setView(item.id); setMobileNav(false); }}
              >
                <Icon size={18} />{item.label}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-meta">
          <div className="identity"><UserRound size={17} /><div><strong>Yifeng Xie</strong><span>{USER_ID}</span></div></div>
          <div className={`service-state ${online === false ? "offline" : ""}`}>
            <span />{online === null ? "Checking service" : online ? "Service online" : "Service offline"}
          </div>
        </div>
      </aside>

      {mobileNav && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}

      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Menu /></button>
          <div>
            <h1>{navItems.find((item) => item.id === view)?.label}</h1>
            <p>Taicang campus · Library and sports facilities</p>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" title="Refresh data" onClick={() => { void loadRooms(); void loadSchedule(); }}><RefreshCw size={18} /></button>
            <div className="avatar">YX</div>
          </div>
        </header>

        {view === "assistant" && (
          <section className="assistant-view">
            <div className="conversation" aria-live="polite">
              <div className="conversation-intro">
                <div className="assistant-symbol"><Bot size={23} /></div>
                <div><h2>What would you like to book?</h2><p>Use natural language. I will verify policy and availability before making changes.</p></div>
              </div>
              <div className="messages">
                {messages.map((message) => (
                  <div key={message.id} className={`message-row ${message.role}`}>
                    <div className="message-avatar">{message.role === "assistant" ? <Bot size={16} /> : "YX"}</div>
                    <div className={`message-bubble ${message.status === "failed" ? "error" : ""}`}>
                      {message.text}
                      {message.status === "needs_confirmation" && <span className="message-label">Confirmation required</span>}
                    </div>
                  </div>
                ))}
                {sending && <div className="message-row assistant"><div className="message-avatar"><Bot size={16} /></div><div className="message-bubble typing"><LoaderCircle size={16} className="spin" />Checking policy and availability</div></div>}
              </div>
            </div>

            <div className="composer-zone">
              {messages.length <= 1 && (
                <div className="quick-prompts">
                  {quickPrompts.map((prompt) => <button key={prompt} onClick={() => void sendMessage(prompt)}>{prompt}</button>)}
                </div>
              )}
              {pendingConfirmation && (
                <div className="confirmation-actions">
                  <button className="secondary-button" onClick={() => void sendMessage("no")}><X size={17} />Cancel</button>
                  <button className="primary-button" onClick={() => void sendMessage("yes")}><Check size={17} />Confirm booking</button>
                </div>
              )}
              <form className="composer" onSubmit={submit}>
                <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="e.g. Book a badminton court tomorrow at 18:00 for two people" />
                <button className="send-button" disabled={!input.trim() || sending} aria-label="Send message"><Send size={18} /></button>
              </form>
            </div>
          </section>
        )}

        {view === "schedule" && (
          <section className="content-view">
            <div className="toolbar">
              <div className="segmented" aria-label="Resource category">
                <button className={category === "library" ? "selected" : ""} onClick={() => setCategory("library")}><Library size={16} />Library</button>
                <button className={category === "sports" ? "selected" : ""} onClick={() => setCategory("sports")}><Trophy size={16} />Sports</button>
              </div>
              <select value={roomId} onChange={(event) => setRoomId(event.target.value)} aria-label="Resource">
                {visibleRooms.map((room) => <option key={room.room_id} value={room.room_id}>{room.name}</option>)}
              </select>
              <div className="week-controls">
                <button className="icon-button" title="Previous week" onClick={() => setWeekStartMs((value) => value - 7 * DAY_MS)}><ChevronLeft size={18} /></button>
                <button className="text-button" onClick={() => setWeekStartMs(getWeekStartMsLocal())}>This week</button>
                <button className="icon-button" title="Next week" onClick={() => setWeekStartMs((value) => value + 7 * DAY_MS)}><ChevronRight size={18} /></button>
              </div>
            </div>

            <div className="schedule-legend"><span><i className="available" />Available</span><span><i className="reserved" />Reserved</span><span>{scheduleLoading && <LoaderCircle size={14} className="spin" />}30-minute slots</span></div>
            <div className="calendar-frame">
              <div className="calendar-grid" style={{ gridTemplateColumns: "88px repeat(7, minmax(92px, 1fr))" }}>
                <div className="calendar-corner">Time</div>
                {dayHeaders.map((day) => <div key={day} className="day-header">{fmtDayLabel(day)}</div>)}
                {timeLabels.map((label, rowIndex) => {
                  const offset = OPEN_MIN * 60 * 1000 + rowIndex * CELL_MS;
                  return (
                    <div className="calendar-row" key={label}>
                      <div className="time-label">{label}</div>
                      {dayHeaders.map((day) => {
                        const start = day + offset;
                        const isReserved = reserved(start, start + CELL_MS, slots);
                        return <button key={start} className={`slot ${isReserved ? "slot-reserved" : ""}`} disabled={isReserved} title={isReserved ? "Reserved" : `Book ${formatDateTime(start)}`} onClick={() => openSlot(start)} />;
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {view === "bookings" && (
          <section className="content-view">
            <div className="section-heading"><div><h2>Current reservations</h2><p>All bookings made under {USER_ID}</p></div><button className="secondary-button" onClick={() => void loadBookings()}><RefreshCw size={16} />Refresh</button></div>
            <div className="booking-list">
              {bookings.length === 0 && <div className="empty-state"><CalendarDays size={28} /><h3>No bookings yet</h3><p>Use the assistant or select an available schedule slot.</p><button className="primary-button" onClick={() => setView("assistant")}>Start a booking</button></div>}
              {bookings.map((booking) => (
                <article className="booking-item" key={booking.booking_id}>
                  <div className="booking-icon">{booking.room_id.startsWith("D-") ? <Library size={20} /> : <Trophy size={20} />}</div>
                  <div className="booking-main"><div><h3>{booking.room_id}</h3><span className={`status-badge ${booking.status}`}>{booking.status}</span></div><p><Clock3 size={15} />{formatDateTime(booking.start_ms)} to {formatDateTime(booking.end_ms)}</p><small>{booking.booking_id} · {booking.members.length} attendee(s)</small></div>
                  {booking.status === "active" && <button className="danger-button" onClick={() => { setInput(`Cancel booking ${booking.booking_id}`); setView("assistant"); }}>Cancel</button>}
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
