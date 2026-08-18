const DAY_MS = 24 * 60 * 60 * 1000;

export function getWeekStartMsLocal(d: Date = new Date()): number {
  // Monday 00:00 local time
  const day = d.getDay(); // Sun=0 ... Sat=6
  const diffToMonday = (day + 6) % 7;
  const monday = new Date(d);
  monday.setHours(0, 0, 0, 0);
  monday.setTime(monday.getTime() - diffToMonday * DAY_MS);
  return monday.getTime();
}

export function fmtDayLabel(ms: number): string {
  const d = new Date(ms);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const w = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
  return `${mm}/${dd} ${w}`;
}

export function fmtTimeLabel(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}