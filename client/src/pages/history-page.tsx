import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, History, Loader2 } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useSearch } from "@/components/search/command-palette";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/form";
import { Skeleton } from "@/components/ui/misc";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { WeatherIcon } from "@/components/weather/weather-icon";
import { useUnits } from "@/hooks/use-auth";
import { api, ApiError } from "@/lib/api";
import { downloadCsv, toCsv } from "@/lib/csv";
import type { Snapshot, Units } from "@/lib/types";
import { compass, formatTemp, formatWind, temp, tempUnit, wind, windUnit } from "@/lib/units";

export const PAGE_SIZE = 20;
const EXPORT_BATCH = 500;          // the server's maximum page

/** ?city=3&page=2 -> city 3, page 2 (pages start at 1; anything odd falls back). */
export function parseHistoryParams(params: URLSearchParams): { cityId: number | null; page: number } {
  const city = Number(params.get("city"));
  const page = Number(params.get("page"));
  return { cityId: Number.isInteger(city) && city > 0 ? city : null, page: Number.isInteger(page) && page > 1 ? page : 1 };
}

/** We ask for one row more than a page: if it comes back, there is a next page. */
export function splitPage<T>(rows: T[], size: number): { rows: T[]; hasNext: boolean } {
  return { rows: rows.slice(0, size), hasNext: rows.length > size };
}

/** Saved readings are shown in the viewer's own time (the reading says when you looked). */
const when = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

async function allReadings(cityId: number | null): Promise<Snapshot[]> {
  const out: Snapshot[] = [];
  for (let offset = 0; ; offset += EXPORT_BATCH) {
    const batch = await api.history({ cityId, limit: EXPORT_BATCH, offset });
    out.push(...batch);
    if (batch.length < EXPORT_BATCH) return out;
  }
}

function exportCsv(rows: Snapshot[], units: Units): string {
  return toCsv(rows, [
    { header: "observed_at (UTC)", value: (r) => r.observed_at },
    { header: "city", value: (r) => r.city.label },
    { header: "condition", value: (r) => r.description },
    { header: `temp ${tempUnit(units)}`, value: (r) => temp(r.temp_c, units) },
    { header: `feels like ${tempUnit(units)}`, value: (r) => temp(r.feels_like_c, units) },
    { header: "humidity %", value: (r) => r.humidity },
    { header: "pressure hPa", value: (r) => r.pressure_hpa },
    { header: `wind ${windUnit(units)}`, value: (r) => wind(r.wind_speed_ms, units) },
    { header: "wind from", value: (r) => compass(r.wind_deg) },
  ]);
}

function ReadingRow({ r, units }: { r: Snapshot; units: Units }) {
  return (
    <tr className="align-middle">
      <td className="num whitespace-nowrap py-2.5 pr-4 text-muted-foreground">{when.format(new Date(r.observed_at))}</td>
      <td className="py-2.5 pr-4 font-medium">{r.city.label}</td>
      <td className="py-2.5 pr-4">
        <span className="flex items-center gap-2 capitalize"><WeatherIcon code={r.icon} className="size-8" />{r.description}</span>
      </td>
      <td className="num py-2.5 pr-4 text-right font-semibold">{formatTemp(r.temp_c, units)}</td>
      <td className="num py-2.5 pr-4 text-right text-muted-foreground">{formatTemp(r.feels_like_c, units)}</td>
      <td className="num py-2.5 pr-4 text-right">{r.humidity}%</td>
      <td className="num whitespace-nowrap py-2.5 pr-4 text-right">{formatWind(r.wind_speed_ms, units)} {compass(r.wind_deg)}</td>
      <td className="num whitespace-nowrap py-2.5 text-right">{r.pressure_hpa} hPa</td>
    </tr>
  );
}

function ReadingCard({ r, units }: { r: Snapshot; units: Units }) {
  return (
    <li className="flex items-center gap-3 py-3">
      <WeatherIcon code={r.icon} label={r.description} className="size-10 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{r.city.label}</p>
        <p className="num truncate text-sm text-muted-foreground">{when.format(new Date(r.observed_at))}</p>
      </div>
      <div className="text-right">
        <p className="num text-lg font-semibold">{formatTemp(r.temp_c, units)}</p>
        <p className="num text-xs text-muted-foreground">{r.humidity}% · {formatWind(r.wind_speed_ms, units)}</p>
      </div>
    </li>
  );
}

export function HistoryPage() {
  const [params, setParams] = useSearchParams();
  const { cityId, page } = parseHistoryParams(params);
  const { units } = useUnits();
  const { openSearch } = useSearch();
  const [exporting, setExporting] = useState(false);
  const go = (next: { cityId?: number | null; page?: number }) => {
    const city = next.cityId === undefined ? cityId : next.cityId;
    const p = next.page ?? 1;
    setParams({ ...(city ? { city: String(city) } : {}), ...(p > 1 ? { page: String(p) } : {}) });
  };

  const cities = useQuery({ queryKey: ["history-cities"], queryFn: api.historyCities });
  const readings = useQuery({
    queryKey: ["history", cityId, page],
    queryFn: () => api.history({ cityId, limit: PAGE_SIZE + 1, offset: (page - 1) * PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });
  const current = readings.data ? splitPage(readings.data, PAGE_SIZE) : null;
  const cityName = cities.data?.find((c) => c.id === cityId)?.name;

  async function onExport() {
    setExporting(true);
    try {
      downloadCsv(`readings-${cityName ?? "all-cities"}`, exportCsv(await allReadings(cityId), units));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">History</h1>
          <p className="text-muted-foreground">Every reading saved when you opened a city.</p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label htmlFor="history-city" className="block text-xs text-muted-foreground">City</Label>
            <select
              id="history-city"
              value={cityId ?? ""}
              onChange={(e) => go({ cityId: e.target.value ? Number(e.target.value) : null })}
              className="h-9 rounded-md border border-input bg-card px-2 text-sm focus-visible:outline-2 focus-visible:outline-accent"
            >
              <option value="">All cities</option>
              {cities.data?.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
          <Button variant="outline" size="sm" className="h-9" onClick={onExport} disabled={exporting || !current?.rows.length}>
            {exporting ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Download aria-hidden="true" />} Export CSV
          </Button>
        </div>
      </div>

      {readings.isPending && (
        <Card className="space-y-3 p-5" aria-hidden="true">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-10" />)}</Card>
      )}
      {readings.isError && (
        <ErrorState title="Your readings didn't load" message={readings.error instanceof ApiError ? readings.error.message : undefined}
                    onRetry={() => readings.refetch()} />
      )}
      {current && current.rows.length === 0 && (
        <EmptyState
          icon={<History />}
          title={page > 1 ? "No more readings" : cityId ? "No readings for this city" : "No readings yet"}
          message="A reading is saved each time you open a city's page."
          action={page > 1 ? <Button variant="outline" onClick={() => go({ page: 1 })}>Back to the first page</Button>
                           : <Button onClick={() => openSearch()}>Find a city</Button>}
        />
      )}
      {current && current.rows.length > 0 && (
        <Card className={readings.isPlaceholderData ? "opacity-70 transition-opacity" : undefined}>
          {/* Phones: a list; wider screens: a table */}
          <ul className="divide-y divide-border px-4 sm:hidden">
            {current.rows.map((r) => <ReadingCard key={r.id} r={r} units={units} />)}
          </ul>
          <div className="hidden overflow-x-auto px-5 py-2 sm:block">
            <table className="w-full text-sm">
              <caption className="sr-only">Saved weather readings, newest first</caption>
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th scope="col" className="py-2.5 pr-4 font-medium">Saved</th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">City</th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">Condition</th>
                  <th scope="col" className="py-2.5 pr-4 text-right font-medium">Temp</th>
                  <th scope="col" className="py-2.5 pr-4 text-right font-medium">Feels</th>
                  <th scope="col" className="py-2.5 pr-4 text-right font-medium">Humidity</th>
                  <th scope="col" className="py-2.5 pr-4 text-right font-medium">Wind</th>
                  <th scope="col" className="py-2.5 text-right font-medium">Pressure</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {current.rows.map((r) => <ReadingRow key={r.id} r={r} units={units} />)}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {current && (page > 1 || current.hasNext) && (
        <nav aria-label="Pages" className="flex items-center justify-between gap-3">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => go({ page: page - 1 })}>
            <ChevronLeft aria-hidden="true" /> Newer
          </Button>
          <span className="num text-sm text-muted-foreground" aria-current="page">Page {page}</span>
          <Button variant="outline" size="sm" disabled={!current.hasNext} onClick={() => go({ page: page + 1 })}>
            Older <ChevronRight aria-hidden="true" />
          </Button>
        </nav>
      )}
    </div>
  );
}
