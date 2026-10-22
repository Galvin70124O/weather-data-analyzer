/**
 * The only place that talks to the server.
 * - Same origin + httpOnly cookie: the browser sends the session cookie itself; we never see it.
 * - Every write sends Content-Type: application/json (the server rejects anything else with 415).
 */
import type {
  AnalyticsResponse,
  City,
  CompareResponse,
  CurrentWeatherResponse,
  DashboardResponse,
  ForecastResponse,
  Period,
  RecentSearch,
  Snapshot,
  Units,
  User,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

function messageFrom(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0].msg === "string") return detail[0].msg; // validation errors
  if (status >= 500) return "Something went wrong on our side. Please try again.";
  return `Request failed (${status}).`;
}

export async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const isWrite = method !== "GET";
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: isWrite ? { Accept: "application/json", "Content-Type": "application/json" } : { Accept: "application/json" },
      body: isWrite ? JSON.stringify(body ?? {}) : undefined,
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, messageFrom(data, response.status));
  return data as T;
}

export const api = {
  me: () => request<User>("GET", "/api/me"),
  login: (identifier: string, password: string) => request<User>("POST", "/api/auth/login", { identifier, password }),
  register: (username: string, email: string, password: string) =>
    request<User>("POST", "/api/auth/register", { username, email, password }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  setUnits: (units: Units) => request<User>("PATCH", "/api/me", { units }),

  searchCities: (q: string) => request<City[]>("GET", `/api/cities/search?q=${encodeURIComponent(q)}`),
  city: (id: number) => request<City>("GET", `/api/cities/${id}`),
  weather: (id: number) => request<CurrentWeatherResponse>("GET", `/api/cities/${id}/weather`),
  forecast: (id: number) => request<ForecastResponse>("GET", `/api/cities/${id}/forecast`),
  analytics: (id: number, days: Period) => request<AnalyticsResponse>("GET", `/api/cities/${id}/analytics?days=${days}`),

  favorites: () => request<{ city: City; created_at: string }[]>("GET", "/api/favorites"),
  addFavorite: (cityId: number) => request<{ city: City }>("POST", "/api/favorites", { city_id: cityId }),
  removeFavorite: (cityId: number) => request<void>("DELETE", `/api/favorites/${cityId}`),

  dashboard: () => request<DashboardResponse>("GET", "/api/dashboard"),
  recentSearches: () => request<RecentSearch[]>("GET", "/api/searches/recent"),
  clearRecentSearches: () => request<void>("DELETE", "/api/searches/recent"),
  history: ({ cityId, limit, offset }: { cityId?: number | null; limit: number; offset: number }) =>
    request<Snapshot[]>("GET", `/api/history?${new URLSearchParams({
      limit: String(limit), offset: String(offset), ...(cityId ? { city_id: String(cityId) } : {}),
    })}`),
  historyCities: () => request<City[]>("GET", "/api/history/cities"),
  compare: (cityIds: number[], days: Period) =>
    request<CompareResponse>("GET", `/api/analytics/compare?${cityIds.map((id) => `city_id=${id}`).join("&")}&days=${days}`),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("POST", "/api/auth/change-password", { current_password: currentPassword, new_password: newPassword }),
};
