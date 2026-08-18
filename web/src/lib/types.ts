export type Slot = {
  start_ms: number;
  end_ms: number;
  status: "reserved" | "closed";
  booking_id?: string | null;
};

export type ScheduleResponse = {
  room_id: string;
  week_start_ms: number;
  week_end_ms: number;
  slots: Slot[];
};

export type Room = {
  room_id: string;
  campus: string;
  building: string;
  floor: number;
  name: string;
  capacity: number;
  min_attendance: number;
  features: string[];
  is_active: boolean;
  category: "library" | "sports";
  activity?: string | null;
};

export type Booking = {
  booking_id: string;
  user_id: string;
  room_id: string;
  start_ms: number;
  end_ms: number;
  status: "active" | "cancelled";
  created_at_ms: number;
  purpose?: string | null;
  members: string[];
};

export type AgentResponse = {
  session_id: string;
  status: "needs_clarification" | "needs_confirmation" | "completed" | "failed";
  message: string;
  pending_action?: Record<string, unknown> | null;
  data?: Record<string, unknown> | null;
};
