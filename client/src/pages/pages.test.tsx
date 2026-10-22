import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { toCompareRows } from "@/components/charts/compare-charts";
import { isSearchShortcut, SearchProvider } from "@/components/search/command-palette";
import { useColorMode } from "@/hooks/use-color-mode";
import type { AnalyticsSummary, City, CompareResponse, CurrentWeather, DashboardCard } from "@/lib/types";
import { validatePasswordChange } from "@/pages/account-page";
import { parseCompareParams, summaryRows } from "@/pages/compare-page";
import { CityCard, greeting } from "@/pages/dashboard-page";
import { parseHistoryParams, splitPage } from "@/pages/history-page";

const london: City = { id: 1, name: "London", state: "England", country: "GB", lat: 51.5, lon: -0.12, label: "London, England, GB" };
const paris: City = { id: 2, name: "Paris", state: null, country: "FR", lat: 48.85, lon: 2.35, label: "Paris, FR" };

function summary(over: Partial<AnalyticsSummary> = {}): AnalyticsSummary {
  return {
    days: 3, days_with_data: 3, coverage: 1, low_coverage: false, missing_dates: [],
    tmean_avg: 10, tmin_avg: 5, tmax_avg: 15, warmest: { date: "2026-10-02", value: 18 }, coldest: null,
    humidity_avg: 70, precip_total: 25.4, precip_days_missing: 0, rainy_days: 2, windiest: null,
    anomaly_avg: 1, warm_days: 2, cool_days: 1, ...over,
  };
}

describe("small page helpers", () => {
  it("greets by the time of day", () => {
    expect(greeting(8)).toBe("Good morning");
    expect(greeting(14)).toBe("Good afternoon");
    expect(greeting(21)).toBe("Good evening");
    expect(greeting(3)).toBe("Good evening");
  });

  it("reads compare cities and period from the URL, safely", () => {
    expect(parseCompareParams(new URLSearchParams("ids=3,7,3,x,-1,9,12&days=90"))).toEqual({ ids: [3, 7, 9], days: 90 });
    expect(parseCompareParams(new URLSearchParams("days=45"))).toEqual({ ids: [], days: 30 });
  });

  it("reads history filter and page from the URL", () => {
    expect(parseHistoryParams(new URLSearchParams("city=4&page=3"))).toEqual({ cityId: 4, page: 3 });
    expect(parseHistoryParams(new URLSearchParams("city=abc&page=0"))).toEqual({ cityId: null, page: 1 });
  });

  it("knows there is a next page when the extra row comes back", () => {
    expect(splitPage([1, 2, 3], 2)).toEqual({ rows: [1, 2], hasNext: true });
    expect(splitPage([1, 2], 2)).toEqual({ rows: [1, 2], hasNext: false });
  });

  it("checks a password change before sending it", () => {
    expect(validatePasswordChange("old-password", "new-password", "new-password")).toEqual({});
    expect(validatePasswordChange("", "short", "other")).toEqual({
      current: "Enter your current password.", next: "At least 8 characters.", confirm: "The two new passwords don't match.",
    });
    expect(validatePasswordChange("same-password", "same-password", "same-password").next).toMatch(/different/);
  });

  it("recognises Ctrl+K and ⌘K only", () => {
    expect(isSearchShortcut({ key: "k", ctrlKey: true, metaKey: false, altKey: false })).toBe(true);
    expect(isSearchShortcut({ key: "K", ctrlKey: false, metaKey: true, altKey: false })).toBe(true);
    expect(isSearchShortcut({ key: "k", ctrlKey: false, metaKey: false, altKey: false })).toBe(false);
    expect(isSearchShortcut({ key: "k", ctrlKey: true, metaKey: false, altKey: true })).toBe(false);
  });
});

describe("compare", () => {
  const data: CompareResponse = {
    days: 3,
    dates: ["2026-10-01", "2026-10-02", "2026-10-03"],
    stale: false,
    cities: [
      { city: london, normals_available: true, summary: summary(), series: { tmean: [0, 10, null], tmean_7d: [null, null, null], precip: [25.4, null, 25.4], anomaly: [1, -1, null] } },
      { city: paris, normals_available: false, summary: summary({ tmean_avg: null }), series: { tmean: [20, 21, 22], precip: [0, 0, 0] } },
    ],
  };

  it("puts every city on the same dates, in the user's units, with rain added up", () => {
    const rows = toCompareRows(data, "imperial");
    expect(rows.map((r) => r.c0_tmean)).toEqual([32, 50, null]);
    expect(rows.map((r) => r.c0_rainTotal)).toEqual([1, 1, 2]);           // inches, a missing day adds nothing
    expect(rows[0]!.c0_anomaly).toBeCloseTo(1.8);                          // a difference: no +32
    expect(rows.map((r) => r.c1_anomaly)).toEqual([null, null, null]);     // no normals: null, not 0
  });

  it("builds the summary table one column per city", () => {
    const rows = summaryRows(data.cities, "metric");
    expect(rows.find((r) => r.label === "Average")!.values).toEqual(["10°C", "–"]);
    expect(rows.find((r) => r.label === "vs 1991–2020 normal")!.values).toEqual(["+1.0°", "–"]);
    expect(rows.find((r) => r.label === "Warmest day")!.values[0]).toBe("18° · 2 Oct");
  });
});

describe("dashboard card", () => {
  const weather: CurrentWeather = {
    condition: "Rain", condition_id: 500, description: "light rain", icon: "10n", theme: "rain",
    observed_at: "2026-10-22T22:00:00Z", timezone_offset_s: 3600, temp_c: 9, feels_like_c: 7, temp_min_c: null, temp_max_c: null,
    humidity: 90, pressure_hpa: 1000, wind_speed_ms: 4, wind_deg: 200, wind_gust_ms: null, clouds_pct: 100, visibility_m: null,
    sunrise: "2026-10-22T06:30:00Z", sunset: "2026-10-22T16:50:00Z", is_day: false,
  };

  function renderCard(card: DashboardCard) {
    const onRetry = vi.fn();
    render(<MemoryRouter><CityCard card={card} units="metric" onRetry={onRetry} /></MemoryRouter>);
    return onRetry;
  }

  it("wears the city's own weather theme and links to the city", () => {
    renderCard({ city: london, weather, stale: true, error: null });
    const link = screen.getByRole("link", { name: /London, England, GB: 9°C, light rain/ });
    expect(link).toHaveAttribute("href", "/cities/1");
    expect(link).toHaveAttribute("data-wx", "rain");
    expect(link).toHaveAttribute("data-tod", "night");
    expect(screen.getByText("Stale data")).toBeInTheDocument();
  });

  it("shows a failing city's own error with a retry, not a broken card", async () => {
    const onRetry = renderCard({ city: paris, weather: null, stale: false, error: "The weather service didn't answer." });
    expect(screen.getByText("The weather service didn't answer.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("colour mode", () => {
  it("is shared: changing it in one place updates every user of the hook", () => {
    const a = renderHook(() => useColorMode());
    const b = renderHook(() => useColorMode());
    act(() => a.result.current.setMode("light"));
    expect(b.result.current.mode).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    act(() => b.result.current.toggle());
    expect(a.result.current.mode).toBe("dark");
  });
});

describe("city search (Ctrl+K)", () => {
  afterEach(() => vi.unstubAllGlobals());

  function json(body: unknown) {
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  }

  function renderApp(children: ReactNode = null) {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/"]}>
          <SearchProvider>
            <Routes>
              <Route path="/" element={<p>home{children}</p>} />
              <Route path="/cities/:id" element={<p>city page</p>} />
            </Routes>
          </SearchProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("opens with Ctrl+K, searches as you type and opens the picked city", async () => {
    const fetchMock = vi.fn((url: string) => Promise.resolve(json(url.includes("/search?") ? [london, { ...london, id: 5, state: "Ontario", country: "CA", label: "London, Ontario, CA" }] : [])));
    vi.stubGlobal("fetch", fetchMock);
    renderApp();
    await userEvent.keyboard("{Control>}k{/Control}");
    const input = await screen.findByPlaceholderText(/Search a city/);
    await userEvent.type(input, "lon");
    expect(await screen.findByText(", Ontario, CA")).toBeInTheDocument();
    const searches = fetchMock.mock.calls.filter(([url]) => url.includes("/search?"));
    expect(searches.map(([url]) => url)).toEqual(["/api/cities/search?q=lon"]);       // debounced: one request
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(await screen.findByText("city page")).toBeInTheDocument();
  });

  it("asks for two letters before searching", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(json([]))));
    renderApp();
    await userEvent.keyboard("{Control>}k{/Control}");
    await userEvent.type(await screen.findByPlaceholderText(/Search a city/), "l");
    expect(await screen.findByText("Type at least 2 letters to search.")).toBeInTheDocument();
  });
});
