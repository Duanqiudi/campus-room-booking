-- rooms
CREATE TABLE IF NOT EXISTS rooms (
  room_id        TEXT PRIMARY KEY,
  campus         TEXT NOT NULL,
  building       TEXT NOT NULL,
  floor          INTEGER NOT NULL,
  name           TEXT NOT NULL,
  capacity       INTEGER NOT NULL,
  min_attendance INTEGER NOT NULL DEFAULT 2,  -- 最低签到人数（先用于“预约时的组员数量校验”）
  features       TEXT NOT NULL DEFAULT '[]',
  is_active      INTEGER NOT NULL DEFAULT 1,
  category       TEXT NOT NULL DEFAULT 'library',
  activity       TEXT
);

CREATE INDEX IF NOT EXISTS idx_rooms_campus_floor
ON rooms(campus, floor);

-- bookings
CREATE TABLE IF NOT EXISTS bookings (
  booking_id     TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL,
  role           TEXT NOT NULL DEFAULT 'student', -- 'student' | 'staff'
  room_id        TEXT NOT NULL,
  start_ms       INTEGER NOT NULL,
  end_ms         INTEGER NOT NULL,
  status         TEXT NOT NULL,                  -- active | cancelled
  purpose        TEXT,
  members_json   TEXT NOT NULL DEFAULT '[]',     -- JSON array string
  created_at_ms  INTEGER NOT NULL,
  updated_at_ms  INTEGER NOT NULL,
  FOREIGN KEY(room_id) REFERENCES rooms(room_id)
);

CREATE INDEX IF NOT EXISTS idx_bookings_room_time
ON bookings(room_id, start_ms, end_ms);

CREATE INDEX IF NOT EXISTS idx_bookings_user_time
ON bookings(user_id, start_ms);
