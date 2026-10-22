/**
 * The server always sends metric. These helpers convert ONLY for display, based on the user's
 * choice (users.units). Wind is shown in km/h (metric) or mph (imperial), rain in mm or inches.
 */
import type { Units } from "./types";

export const cToF = (c: number): number => (c * 9) / 5 + 32;
/** A temperature DIFFERENCE (e.g. an anomaly) converts without the +32 offset. */
export const cDeltaToF = (delta: number): number => (delta * 9) / 5;

export function temp(c: number | null | undefined, units: Units): number | null {
  if (c === null || c === undefined || Number.isNaN(c)) return null;
  return units === "imperial" ? cToF(c) : c;
}

export function tempDelta(delta: number | null | undefined, units: Units): number | null {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return null;
  return units === "imperial" ? cDeltaToF(delta) : delta;
}

export function formatTemp(c: number | null | undefined, units: Units, withUnit = false): string {
  const value = temp(c, units);
  if (value === null) return "–";
  return `${Math.round(value)}°${withUnit ? (units === "imperial" ? "F" : "C") : ""}`;
}

/** A °C difference from the API, shown in the user's unit: "+2.3°". */
export function formatDelta(delta: number | null | undefined, units: Units): string {
  return signedDegrees(tempDelta(delta, units));
}

/** Format a difference that is ALREADY in the display unit: "+2.3°", "−0.4°", "±0.0°". */
export function signedDegrees(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "–";
  const rounded = Math.round(value * 10) / 10;
  return `${rounded > 0 ? "+" : rounded < 0 ? "−" : "±"}${Math.abs(rounded).toFixed(1)}°`;
}

export function wind(ms: number | null | undefined, units: Units): number | null {
  if (ms === null || ms === undefined) return null;
  return units === "imperial" ? ms * 2.236936 : ms * 3.6;
}

export function formatWind(ms: number | null | undefined, units: Units): string {
  const value = wind(ms, units);
  return value === null ? "–" : `${Math.round(value)} ${units === "imperial" ? "mph" : "km/h"}`;
}

export function rain(mm: number | null | undefined, units: Units): number | null {
  if (mm === null || mm === undefined) return null;
  return units === "imperial" ? mm / 25.4 : mm;
}

export function formatRain(mm: number | null | undefined, units: Units): string {
  const value = rain(mm, units);
  if (value === null) return "–";
  return units === "imperial" ? `${value.toFixed(2)} in` : `${value.toFixed(value < 10 ? 1 : 0)} mm`;
}

export const tempUnit = (units: Units): string => (units === "imperial" ? "°F" : "°C");
export const windUnit = (units: Units): string => (units === "imperial" ? "mph" : "km/h");
export const rainUnit = (units: Units): string => (units === "imperial" ? "in" : "mm");

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
export function compass(deg: number | null | undefined): string {
  if (deg === null || deg === undefined) return "";
  return COMPASS[Math.round((((deg % 360) + 360) % 360) / 45) % 8] ?? "";
}
