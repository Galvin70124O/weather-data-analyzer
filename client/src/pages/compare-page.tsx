import { useQuery } from "@tanstack/react-query";
import { BarChart3, Plus, X } from "lucide-react";
import { lazy, Suspense, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { seriesColor } from "@/components/charts/chart-kit";
import { useSearch } from "@/components/search/command-palette";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUnits } from "@/hooks/use-auth";
import { api, ApiError } from "@/lib/api";
import { downloadCsv, toCsv } from "@/lib/csv";
import { shortDate } from "@/lib/time";
import type { City, CompareCity, CompareResponse, Period, Units } from "@/lib/types";
import { formatDelta, formatRain, formatTemp } from "@/lib/units";

const CompareCharts = lazy(() => import("@/components/charts/compare-charts"));

export const MAX_COMPARE = 3;
const PERIODS: Period[] = [30, 90, 365];

/** ?ids=3,7&days=90 -> [3, 7], 90. Bad or repeated ids are dropped; days falls back to 30. */
export function parseCompareParams(params: URLSearchParams): { ids: number[]; days: Period } {
  const ids = [...new Set((params.get("ids") ?? "").split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0))].slice(0, MAX_COMPARE);
  const days = Number(params.get("days"));
  return { ids, days: (PERIODS as number[]).includes(days) ? (days as Period) : 30 };
}

/** The summary table: one row per figure, one column per city (in its series colour). */
export function summaryRows(cities: CompareCity[], units: Units): { label: string; values: string[] }[] {
  const pick = (f: (c: CompareCity) => string) => cities.map(f);
  return [
    { label: "Average", values: pick((c) => formatTemp(c.summary.tmean_avg, units, true)) },
    { label: "Average high", values: pick((c) => formatTemp(c.summary.tmax_avg, units, true)) },
    { label: "Average low", values: pick((c) => formatTemp(c.summary.tmin_avg, units, true)) },
    { label: "vs 1991–2020 normal", values: pick((c) => (c.normals_available ? formatDelta(c.summary.anomaly_avg, units) : "–")) },
    { label: "Warmest day", values: pick((c) => (c.summary.warmest ? `${formatTemp(c.summary.warmest.value, units)} · ${shortDate(c.summary.warmest.date)}` : "–")) },
    { label: "Coldest night", values: pick((c) => (c.summary.coldest ? `${formatTemp(c.summary.coldest.value, units)} · ${shortDate(c.summary.coldest.date)}` : "–")) },
    { label: "Rain", values: pick((c) => formatRain(c.summary.precip_total, units)) },
    { label: "Rainy days", values: pick((c) => String(c.summary.rainy_days)) },
    { label: "Days with data", values: pick((c) => `${c.summary.days_with_data} of ${c.summary.days}`) },
  ];
}

function SummaryTable({ data, units }: { data: CompareResponse; units: Units }) {
  const rows = summaryRows(data.cities, units);
  const exportCsv = () => downloadCsv(`compare-summary-${data.days}d`, toCsv(rows, [
    { header: "", value: (r) => r.label },
    ...data.cities.map((c, k) => ({ header: c.city.label, value: (r: (typeof rows)[number]) => r.values[k] })),
  ]));
  return (
    <Card>
      <CardHeader className="flex-nowrap">
        <CardTitle className="min-w-0 flex-1">Summary</CardTitle>
        <Button variant="outline" size="sm" className="shrink-0" onClick={exportCsv}>Export CSV</Button>
      </CardHeader>
      <CardContent className="pt-3">
        {/* Fixed layout: on phones the cells wrap instead of the table scrolling sideways */}
        <table className="num w-full table-fixed text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th scope="col" className="w-[30%] py-2 pr-3 font-medium text-muted-foreground sm:w-1/4"><span className="sr-only">Figure</span></th>
              {data.cities.map((c, k) => (
                <th key={c.city.id} scope="col" className="py-2 pr-3 font-semibold">
                  {/* Phones: the dot sits above the name, so the name keeps the column's full width */}
                  <span className="flex flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-2">
                    <span className="size-2.5 shrink-0 rounded-full" style={{ background: seriesColor(k) }} aria-hidden="true" />
                    <span className="min-w-0">{c.city.name}</span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row" className="py-2 pr-3 text-left font-normal text-muted-foreground">{row.label}</th>
                {row.values.map((v, k) => <td key={k} className="py-2 pr-3">{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function CityPicker({ ids, cities, onChange }: { ids: number[]; cities: Map<number, City>; onChange: (ids: number[]) => void }) {
  const { openSearch } = useSearch();
  const favorites = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });
  const suggestions = (favorites.data ?? []).map((f) => f.city).filter((c) => !ids.includes(c.id)).slice(0, 4);
  const full = ids.length >= MAX_COMPARE;
  const add = (city: City) => onChange([...ids, city.id]);

  return (
    <div className="space-y-3">
      <ul className="flex flex-wrap items-center gap-2" aria-label="Cities being compared">
        {ids.map((id, k) => (
          <li key={id} className="inline-flex items-center gap-2 rounded-full border border-border bg-card py-1 pl-3 pr-1 text-sm">
            <span className="size-2.5 rounded-full" style={{ background: seriesColor(k) }} aria-hidden="true" />
            {cities.get(id)?.label ?? <Skeleton className="h-4 w-20" />}
            <button type="button" onClick={() => onChange(ids.filter((x) => x !== id))}
                    className="grid size-7 place-items-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-accent"
                    aria-label={`Remove ${cities.get(id)?.name ?? "city"}`}>
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </li>
        ))}
        <li>
          <Button variant="outline" size="sm" disabled={full}
                  onClick={() => openSearch({ title: "Add a city to compare", onPick: add, exclude: ids })}>
            <Plus aria-hidden="true" /> {full ? `Up to ${MAX_COMPARE} cities` : "Add city"}
          </Button>
        </li>
      </ul>
      {!full && suggestions.length > 0 && (
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          Favourites:
          {suggestions.map((c) => (
            <button key={c.id} type="button" onClick={() => add(c)}
                    className="rounded-full border border-dashed border-border px-2.5 py-0.5 text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent">
              + {c.name}
            </button>
          ))}
        </p>
      )}
    </div>
  );
}

export function ComparePage() {
  const [params, setParams] = useSearchParams();
  const { ids, days } = parseCompareParams(params);
  const { units } = useUnits();
  const update = (next: { ids?: number[]; days?: Period }) =>
    setParams({ ids: (next.ids ?? ids).join(","), days: String(next.days ?? days) }, { replace: true });

  const compare = useQuery({
    queryKey: ["compare", ids, days],
    queryFn: () => api.compare(ids, days),
    enabled: ids.length >= 2,
    staleTime: 30 * 60_000,
  });
  // Chip labels: from the comparison when loaded, otherwise one lookup per city
  const lookups = useQuery({
    queryKey: ["cities", ids],
    queryFn: () => Promise.all(ids.map((id) => api.city(id))),
    enabled: ids.length > 0,
    staleTime: Infinity,
  });
  const cities = useMemo(() => new Map((lookups.data ?? []).map((c) => [c.id, c])), [lookups.data]);
  const data = compare.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Compare</h1>
          <p className="text-muted-foreground">Two or three cities over the same days, one colour each.</p>
        </div>
        <div className="flex items-center gap-2">
          {data?.stale && <Badge tone="warning">Stale data</Badge>}
          <Tabs value={String(days)} onValueChange={(v) => update({ days: Number(v) as Period })}>
            <TabsList aria-label="Period">
              {PERIODS.map((p) => <TabsTrigger key={p} value={String(p)}>{p === 365 ? "1 year" : `${p} days`}</TabsTrigger>)}
            </TabsList>
          </Tabs>
        </div>
      </div>

      <CityPicker ids={ids} cities={cities} onChange={(next) => update({ ids: next })} />

      {ids.length < 2 && (
        <EmptyState icon={<BarChart3 />} title={ids.length ? "Add one more city" : "Pick two or three cities"}
                    message="Add cities with the button above, or from your favourites. Each one keeps its colour on every chart." />
      )}
      {ids.length >= 2 && compare.isPending && (
        <div className="space-y-4" aria-hidden="true"><Skeleton className="h-72" /><Skeleton className="h-80" /></div>
      )}
      {compare.isError && (
        <ErrorState title="The comparison didn't load" message={compare.error instanceof ApiError ? compare.error.message : undefined}
                    onRetry={() => compare.refetch()} />
      )}
      {data && ids.length >= 2 && (
        <>
          <SummaryTable data={data} units={units} />
          <Suspense fallback={<Skeleton className="h-80" aria-hidden="true" />}>
            <CompareCharts data={data} units={units} />
          </Suspense>
        </>
      )}
    </div>
  );
}
