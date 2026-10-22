/**
 * Times in a CITY's local time. The API gives UTC instants plus the city's UTC offset (seconds);
 * we shift the instant and format it as UTC, so the viewer's own time zone never leaks in.
 */
function shifted(iso: string | Date, offsetS: number): Date {
  const instant = typeof iso === "string" ? new Date(iso) : iso;
  return new Date(instant.getTime() + offsetS * 1000);
}

export function localTime(iso: string | Date, offsetS: number): string {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }).format(shifted(iso, offsetS));
}

export function localHour(iso: string | Date, offsetS: number): string {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", timeZone: "UTC" }).format(shifted(iso, offsetS));
}

export function localWeekday(iso: string | Date, offsetS: number): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", timeZone: "UTC" }).format(shifted(iso, offsetS));
}

/** "Mon", "Tue"... for a YYYY-MM-DD date (already a local date). */
export function weekdayShort(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" }).format(new Date(`${isoDate}T12:00:00Z`));
}

/** "21 Oct" for a YYYY-MM-DD date. */
export function shortDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${isoDate}T12:00:00Z`));
}

/** "UTC+2", "UTC−5:30" */
export function utcOffsetLabel(offsetS: number): string {
  const sign = offsetS >= 0 ? "+" : "−";
  const minutes = Math.abs(offsetS) / 60;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `UTC${sign}${h}${m ? `:${String(m).padStart(2, "0")}` : ""}`;
}
