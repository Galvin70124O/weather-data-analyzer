import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CityHero } from "@/components/weather/city-hero";
import { rangeBar } from "@/components/weather/forecast";
import { iconSource, stillSvg } from "@/components/weather/weather-icon";
import type { City, CurrentWeather } from "@/lib/types";
import { safeNext, validateRegistration } from "@/pages/auth-pages";

describe("weather icons", () => {
  it("removes every animation tag for reduced motion and keeps the drawing", () => {
    const svg = '<svg><circle r="1"><animate attributeName="r" values="1;2"/></circle>'
      + '<g><animateTransform attributeName="transform" type="rotate"></animateTransform></g></svg>';
    expect(stillSvg(svg)).toBe('<svg><circle r="1"></circle><g></g></svg>');
  });

  it("serves the real Meteocons file, still when asked", () => {
    const animated = decodeURIComponent(iconSource("10d", false)!);
    const still = decodeURIComponent(iconSource("10d", true)!);
    expect(animated).toContain("<animate");
    expect(still).not.toContain("<animate");
    expect(still).toContain("<svg");
  });

  it("falls back to the day icon for an unknown code, and to nothing for garbage", () => {
    expect(iconSource("01x", false)).toBe(iconSource("01d", false));
    expect(iconSource("zz", false)).toBeNull();
  });
});

describe("rangeBar", () => {
  it("places a day's min-max inside the week's range, in percent", () => {
    expect(rangeBar(10, 20, 0, 40)).toEqual({ left: 25, width: 25 });
    expect(rangeBar(0, 40, 0, 40)).toEqual({ left: 0, width: 100 });
  });

  it("stays visible and inside the track for tiny or flat ranges", () => {
    expect(rangeBar(40, 40, 0, 40)).toEqual({ left: 98, width: 2 });
    expect(rangeBar(5, 5, 5, 5)).toEqual({ left: 0, width: 2 });
  });
});

describe("validateRegistration (mirrors the server rules)", () => {
  it("accepts a valid account", () => {
    expect(validateRegistration("ada.l", "ada@example.com", "correct horse")).toEqual({});
  });

  it("explains each problem", () => {
    const errors = validateRegistration("a", "not-an-email", "short");
    expect(Object.keys(errors).sort()).toEqual(["email", "password", "username"]);
  });

  it("counts the bcrypt limit in bytes, not characters", () => {
    expect(validateRegistration("ada", "a@b.co", "é".repeat(36))).toEqual({});        // 72 bytes
    expect(validateRegistration("ada", "a@b.co", "é".repeat(37)).password).toMatch(/72 bytes/);
  });
});

describe("CityHero", () => {
  const city: City = { id: 1, name: "London", state: "England", country: "GB", lat: 51.5, lon: -0.12, label: "London, England, GB" };
  const weather: CurrentWeather = {
    condition: "Rain", condition_id: 500, description: "light rain", icon: "10d", theme: "rain",
    observed_at: "2026-10-22T12:00:00Z", timezone_offset_s: 3600,
    temp_c: 20, feels_like_c: 18.5, temp_min_c: 17, temp_max_c: 22,
    humidity: 81, pressure_hpa: 1009, wind_speed_ms: 5, wind_deg: 270, wind_gust_ms: null,
    clouds_pct: 90, visibility_m: 10000,
    sunrise: "2026-10-22T06:30:00Z", sunset: "2026-10-22T16:50:00Z", is_day: true,
  };

  function renderHero(props: Partial<Parameters<typeof CityHero>[0]> = {}) {
    const onToggleFavorite = vi.fn();
    render(<CityHero city={city} weather={weather} units="imperial" stale={false} isFavorite={false} onToggleFavorite={onToggleFavorite} {...props} />);
    return { onToggleFavorite };
  }

  it("shows every figure in °F and mph when the user picked imperial", () => {
    renderHero();
    expect(screen.getByRole("heading", { name: "London" })).toBeInTheDocument();
    expect(screen.getByText("68°")).toBeInTheDocument();                 // 20 °C
    expect(screen.getByText(/Feels like 65°/)).toBeInTheDocument();       // 18.5 °C
    expect(screen.getByText(/11 mph/)).toBeInTheDocument();               // 5 m/s
    expect(screen.queryByText(/km\/h/)).not.toBeInTheDocument();
  });

  it("shows the city's local times (UTC+1), not the browser's", () => {
    renderHero();
    expect(screen.getByText("07:30")).toBeInTheDocument();
    expect(screen.getByText("17:50")).toBeInTheDocument();
  });

  it("flags stale data and toggles the favourite from the keyboard", async () => {
    const { onToggleFavorite } = renderHero({ stale: true });
    expect(screen.getByText(/stale/i)).toBeInTheDocument();
    const star = screen.getByRole("button", { name: /favourite/i });
    star.focus();
    await userEvent.keyboard("{Enter}");
    expect(onToggleFavorite).toHaveBeenCalledOnce();
  });
});

describe("safeNext (login redirect)", () => {
  it("only follows paths inside the app", () => {
    expect(safeNext("/cities/3?x=1")).toBe("/cities/3?x=1");
    expect(safeNext(null)).toBe("/");
    expect(safeNext("https://evil.example")).toBe("/");
    expect(safeNext("//evil.example")).toBe("/");
    expect(safeNext("/\\evil.example")).toBe("/");
  });
});
