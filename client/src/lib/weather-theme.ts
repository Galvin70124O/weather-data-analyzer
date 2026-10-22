/**
 * The look follows the weather: <html data-wx="rain" data-tod="night">.
 * globals.css turns those two attributes into the accent colour and the background gradient.
 */
import type { CurrentWeather, Theme } from "./types";

export type TimeOfDay = "day" | "night";

export function timeOfDay(weather: Pick<CurrentWeather, "observed_at" | "sunrise" | "sunset" | "is_day">): TimeOfDay {
  if (weather.sunrise && weather.sunset) {
    const now = new Date(weather.observed_at).getTime();
    return now >= new Date(weather.sunrise).getTime() && now < new Date(weather.sunset).getTime() ? "day" : "night";
  }
  return weather.is_day ? "day" : "night";
}

/** Clear skies have their own night look; everything else keeps its condition and gets darker at night. */
export function themeFor(weather: Pick<CurrentWeather, "theme" | "observed_at" | "sunrise" | "sunset" | "is_day">): {
  wx: Theme;
  tod: TimeOfDay;
} {
  const tod = timeOfDay(weather);
  let wx = weather.theme;
  if (wx === "clear-day" && tod === "night") wx = "clear-night";
  if (wx === "clear-night" && tod === "day") wx = "clear-day";
  return { wx, tod };
}

export function applyWeatherTheme(theme: { wx: Theme; tod: TimeOfDay } | null, root: HTMLElement = document.documentElement): void {
  if (theme) {
    root.dataset.wx = theme.wx;
    root.dataset.tod = theme.tod;
  } else {
    delete root.dataset.wx;
    delete root.dataset.tod;
  }
}
