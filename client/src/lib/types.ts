/** Shapes returned by the API (server/app/schemas). Everything is metric: °C, m/s, hPa, mm. */

export type Units = "metric" | "imperial";
export type Theme = "clear-day" | "clear-night" | "clouds" | "rain" | "storm" | "snow" | "mist";

export interface User {
  id: number;
  username: string;
  email: string;
  units: Units;
  created_at: string;
}

export interface City {
  id: number;
  name: string;
  state: string | null;
  country: string;
  lat: number;
  lon: number;
  label: string;
}

export interface Condition {
  condition: string;
  condition_id: number;
  description: string;
  icon: string;
  theme: Theme;
}

export interface CurrentWeather extends Condition {
  observed_at: string;
  timezone_offset_s: number;
  temp_c: number;
  feels_like_c: number;
  temp_min_c: number | null;
  temp_max_c: number | null;
  humidity: number;
  pressure_hpa: number;
  wind_speed_ms: number;
  wind_deg: number | null;
  wind_gust_ms: number | null;
  clouds_pct: number | null;
  visibility_m: number | null;
  sunrise: string | null;
  sunset: string | null;
  is_day: boolean;
}

export interface CurrentWeatherResponse {
  city: City;
  weather: CurrentWeather;
  fetched_at: string;
  stale: boolean;
}

export interface HourlyStep extends Condition {
  time: string;
  temp_c: number;
  feels_like_c: number;
  pop: number;
  rain_mm: number;
  wind_speed_ms: number;
  wind_deg: number | null;
}

export interface DailyForecast extends Condition {
  date: string;
  temp_min_c: number;
  temp_max_c: number;
  pop_max: number;
  rain_mm: number;
  humidity_mean: number;
  wind_max_ms: number;
}

export interface ForecastResponse {
  city: City;
  timezone_offset_s: number;
  hourly: HourlyStep[];
  daily: DailyForecast[];
  fetched_at: string;
  stale: boolean;
}

export interface AnalyticsDay {
  date: string;
  tmin: number | null;
  tmax: number | null;
  tmean: number | null;
  tmean_7d: number | null;
  humidity: number | null;
  precip: number | null;
  wind_max: number | null;
  normal_tmean: number | null;
  normal_tmin: number | null;
  normal_tmax: number | null;
  normal_p10: number | null;
  normal_p90: number | null;
  normal_precip: number | null;
  anomaly: number | null;
  category: "warm" | "cool" | "normal" | null;
}

export interface DayValue {
  date: string;
  value: number;
}

export interface AnalyticsSummary {
  days: number;
  days_with_data: number;
  coverage: number;
  low_coverage: boolean;
  missing_dates: string[];
  tmean_avg: number | null;
  tmin_avg: number | null;
  tmax_avg: number | null;
  warmest: DayValue | null;
  coldest: DayValue | null;
  humidity_avg: number | null;
  precip_total: number | null;
  precip_days_missing: number;
  rainy_days: number;
  windiest: DayValue | null;
  anomaly_avg: number | null;
  warm_days: number | null;
  cool_days: number | null;
}

export interface AnalyticsResponse {
  city: City;
  period: { start: string; end: string; days: number };
  normals: { available: boolean; baseline: string };
  daily: AnalyticsDay[];
  summary: AnalyticsSummary;
  extremes: Record<"hottest" | "coldest" | "wettest" | "windiest" | "warmest_vs_normal" | "coolest_vs_normal", DayValue[]>;
  stale: boolean;
  fetched_at: string | null;
}

export type Period = 30 | 90 | 365;

export interface RecentSearch {
  city: City;
  searched_at: string;
}

export interface DashboardCard {
  city: City;
  weather: CurrentWeather | null;     // null: the weather service failed and nothing is cached
  stale: boolean;
  error: string | null;
}

export interface DashboardResponse {
  username: string;
  favorites: DashboardCard[];
  recent: RecentSearch[];
}

/** One saved reading (taken when the user opened a city). */
export interface Snapshot {
  id: number;
  city: City;
  observed_at: string;
  temp_c: number;
  feels_like_c: number;
  humidity: number;
  pressure_hpa: number;
  wind_speed_ms: number;
  wind_deg: number | null;
  condition: string;
  description: string;
  icon: string;
}

export type CompareMetric = "tmean" | "tmean_7d" | "tmin" | "tmax" | "precip" | "humidity" | "wind_max" | "anomaly";

export interface CompareCity {
  city: City;
  normals_available: boolean;
  series: Partial<Record<CompareMetric, (number | null)[]>>;     // one value per date in CompareResponse.dates
  summary: AnalyticsSummary;
}

export interface CompareResponse {
  days: number;
  dates: string[];
  cities: CompareCity[];
  stale: boolean;
}
