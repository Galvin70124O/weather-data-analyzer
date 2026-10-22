import { api, ApiError, request } from "./api";
import { safeFilename, toCsv } from "./csv";
import { localTime, utcOffsetLabel } from "./time";
import { applyWeatherTheme, themeFor, timeOfDay } from "./weather-theme";
import {
  compass, formatDelta, formatRain, formatTemp, formatWind, signedDegrees, temp, tempDelta,
} from "./units";

describe("units", () => {
  it("converts temperatures for display only", () => {
    expect(temp(0, "imperial")).toBe(32);
    expect(temp(100, "imperial")).toBe(212);
    expect(temp(21.4, "metric")).toBe(21.4);
    expect(formatTemp(21.6, "metric")).toBe("22°");
    expect(formatTemp(21.6, "imperial", true)).toBe("71°F");
  });

  it("converts a difference without the +32 offset", () => {
    expect(tempDelta(2, "imperial")).toBeCloseTo(3.6);
    expect(formatDelta(2, "imperial")).toBe("+3.6°");
    expect(formatDelta(-0.44, "metric")).toBe("−0.4°");
    expect(formatDelta(0.01, "metric")).toBe("±0.0°");
  });

  it("formats an already-converted difference without converting again", () => {
    expect(signedDegrees(3.6)).toBe("+3.6°");
    expect(signedDegrees(null)).toBe("–");
  });

  it("shows missing values as a dash, never 0", () => {
    expect(formatTemp(null, "metric")).toBe("–");
    expect(formatTemp(Number.NaN, "imperial")).toBe("–");
    expect(formatRain(null, "metric")).toBe("–");
    expect(formatWind(undefined, "metric")).toBe("–");
  });

  it("converts wind and rain", () => {
    expect(formatWind(10, "metric")).toBe("36 km/h");
    expect(formatWind(10, "imperial")).toBe("22 mph");
    expect(formatRain(25.4, "imperial")).toBe("1.00 in");
    expect(formatRain(3.25, "metric")).toBe("3.3 mm");
    expect(formatRain(123.4, "metric")).toBe("123 mm");
  });

  it("names compass directions, wrapping around", () => {
    expect(compass(0)).toBe("N");
    expect(compass(225)).toBe("SW");
    expect(compass(359)).toBe("N");
    expect(compass(-90)).toBe("W");
    expect(compass(null)).toBe("");
  });
});

describe("time", () => {
  it("shows the city's local time, not the browser's", () => {
    expect(localTime("2026-01-01T12:00:00Z", 9 * 3600)).toBe("21:00");
    expect(localTime("2026-01-01T02:00:00Z", -5 * 3600)).toBe("21:00");
    expect(utcOffsetLabel(5.5 * 3600)).toBe("UTC+5:30");
    expect(utcOffsetLabel(-3 * 3600)).toBe("UTC−3");
  });
});

describe("csv", () => {
  const columns = [
    { header: "date", value: (r: { date: string; t: number | null; note: string }) => r.date },
    { header: "temp °C", value: (r: { t: number | null }) => r.t },
    { header: "note", value: (r: { note: string }) => r.note },
  ];

  it("writes missing values as empty cells and quotes when needed", () => {
    const csv = toCsv([{ date: "2026-01-01", t: 1.234, note: 'a "b", c' }, { date: "2026-01-02", t: null, note: "" }], columns);
    expect(csv).toBe('date,temp °C,note\r\n2026-01-01,1.23,"a ""b"", c"\r\n2026-01-02,,\r\n');
  });

  it("neutralises spreadsheet formulas in text but keeps negative numbers", () => {
    const csv = toCsv([{ date: "=HYPERLINK(1)", t: -3, note: "@cmd" }], columns);
    expect(csv.split("\r\n")[1]).toBe("'=HYPERLINK(1),-3,'@cmd");
  });

  it("makes safe file names", () => {
    expect(safeFilename("São Paulo, BR – 30 days")).toBe("s-o-paulo-br-30-days");
    expect(safeFilename("../../")).toBe("export");
  });
});

describe("weather theme", () => {
  const base = { observed_at: "2026-06-01T12:00:00Z", sunrise: "2026-06-01T04:00:00Z", sunset: "2026-06-01T20:00:00Z", is_day: true };

  it("uses sunrise and sunset for day/night", () => {
    expect(timeOfDay(base)).toBe("day");
    expect(timeOfDay({ ...base, observed_at: "2026-06-01T21:00:00Z" })).toBe("night");
    expect(timeOfDay({ ...base, sunrise: null, sunset: null, is_day: false })).toBe("night");
  });

  it("switches clear skies to the night look, keeps other conditions", () => {
    const night = { ...base, observed_at: "2026-06-01T22:00:00Z" };
    expect(themeFor({ ...night, theme: "clear-day" })).toEqual({ wx: "clear-night", tod: "night" });
    expect(themeFor({ ...base, theme: "clear-night" })).toEqual({ wx: "clear-day", tod: "day" });
    expect(themeFor({ ...night, theme: "rain" })).toEqual({ wx: "rain", tod: "night" });
  });

  it("sets and clears the attributes globals.css reads", () => {
    const root = document.createElement("html");
    applyWeatherTheme({ wx: "storm", tod: "night" }, root);
    expect(root.dataset).toMatchObject({ wx: "storm", tod: "night" });
    applyWeatherTheme(null, root);
    expect(root.dataset.wx).toBeUndefined();
  });
});

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  function stubFetch(status: number, body: unknown) {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("sends JSON on every write, logout included (the server rejects anything else)", async () => {
    const fetchMock = stubFetch(204, undefined);
    await api.logout();
    const [path, init] = fetchMock.mock.calls[0]!;
    expect(path).toBe("/api/auth/logout");
    expect(init).toMatchObject({ method: "POST", credentials: "same-origin", body: "{}" });
    expect(init.headers["Content-Type"]).toBe("application/json");
  });

  it("sends no body on reads", async () => {
    const fetchMock = stubFetch(200, { ok: true });
    await request("GET", "/api/health");
    expect(fetchMock.mock.calls[0]![1].body).toBeUndefined();
  });

  it("turns server errors into ApiError with the server's message", async () => {
    stubFetch(409, { detail: "That username is taken." });
    await expect(request("POST", "/api/auth/register", {})).rejects.toEqual(new ApiError(409, "That username is taken."));
  });

  it("uses the first validation message", async () => {
    stubFetch(422, { detail: [{ msg: "Value error, too short" }] });
    await expect(request("POST", "/x", {})).rejects.toMatchObject({ status: 422, message: "Value error, too short" });
  });

  it("reports a network failure without leaking details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(request("GET", "/api/me")).rejects.toMatchObject({ status: 0 });
  });
});
