import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CloudRain, Flame, Snowflake, Thermometer } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { AnomalyChart, RainChart, TemperatureChart, toChartDays } from "@/components/charts/analytics-charts";
import { Card } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { ErrorState } from "@/components/ui/states";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { shortDate } from "@/lib/time";
import type { AnalyticsResponse, Period, Units } from "@/lib/types";
import { formatDelta, formatRain, formatTemp } from "@/lib/units";

const PERIODS: Period[] = [30, 90, 365];

function Stat({ icon, label, value, hint }: { icon: ReactNode; label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <Card className="p-4">
      <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground [&_svg]:size-3.5">{icon}{label}</p>
      <p className="num mt-1.5 text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="num mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}

function Summary({ data, units }: { data: AnalyticsResponse; units: Units }) {
  const s = data.summary;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat icon={<Thermometer />} label="Average" value={formatTemp(s.tmean_avg, units, true)}
            hint={s.anomaly_avg !== null ? `${formatDelta(s.anomaly_avg, units)} vs normal` : "No normal yet"} />
      <Stat icon={<Flame />} label="Warmest day" value={formatTemp(s.warmest?.value, units, true)}
            hint={s.warmest ? shortDate(s.warmest.date) : "–"} />
      <Stat icon={<Snowflake />} label="Coldest night" value={formatTemp(s.coldest?.value, units, true)}
            hint={s.coldest ? shortDate(s.coldest.date) : "–"} />
      <Stat icon={<CloudRain />} label="Rain" value={formatRain(s.precip_total, units)} hint={`${s.rainy_days} rainy days`} />
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      <Skeleton className="h-80" />
      <div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-80" /><Skeleton className="h-80" /></div>
    </div>
  );
}

export function AnalyticsSection({ cityId, cityName, units }: { cityId: number; cityName: string; units: Units }) {
  const [days, setDays] = useState<Period>(30);
  const query = useQuery({ queryKey: ["analytics", cityId, days], queryFn: () => api.analytics(cityId, days), staleTime: 30 * 60_000 });
  const chartDays = useMemo(() => (query.data ? toChartDays(query.data.daily, units) : []), [query.data, units]);
  const data = query.data;

  return (
    <section aria-labelledby="analytics-title" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="analytics-title" className="text-xl font-semibold tracking-tight">{days === 365 ? "Past year" : `Past ${days} days`}</h2>
          <p className="text-sm text-muted-foreground">
            {data ? `${shortDate(data.period.start)} – ${shortDate(data.period.end)}` : "The last days, compared with the 1991–2020 normal"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {data?.stale && <Badge tone="warning">Stale data</Badge>}
          <Tabs value={String(days)} onValueChange={(v) => setDays(Number(v) as Period)}>
            <TabsList aria-label="Period">
              {PERIODS.map((p) => <TabsTrigger key={p} value={String(p)}>{p === 365 ? "1 year" : `${p} days`}</TabsTrigger>)}
            </TabsList>
          </Tabs>
        </div>
      </div>

      {query.isPending && <AnalyticsSkeleton />}
      {query.isError && (
        <ErrorState
          title="History isn't available right now"
          message={query.error instanceof ApiError ? query.error.message : undefined}
          onRetry={() => query.refetch()}
        />
      )}
      {data && (
        <>
          {data.summary.low_coverage && (
            <p className="flex items-start gap-2 rounded-md border border-warm/40 bg-warm/10 px-3 py-2 text-sm text-warm">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              Only {data.summary.days_with_data} of {data.summary.days} days have data, so averages may be off.
            </p>
          )}
          {!data.normals.available && (
            <p className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
              The 1991–2020 normals couldn't be loaded yet; they'll appear next time.
            </p>
          )}
          <Summary data={data} units={units} />
          <TemperatureChart days={chartDays} units={units} cityName={cityName} hasNormals={data.normals.available} />
          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
            {data.normals.available && <AnomalyChart days={chartDays} units={units} cityName={cityName} />}
            <RainChart days={chartDays} units={units} cityName={cityName} />
          </div>
        </>
      )}
    </section>
  );
}
