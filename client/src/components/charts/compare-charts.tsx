import { useMemo } from "react";
import { CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { COLORS, ChartCard, ChartTooltip, GRID, LegendItem, dateAxis, seriesColor, valueAxis } from "@/components/charts/chart-kit";
import type { CompareCity, CompareResponse, Units } from "@/lib/types";
import { rain, rainUnit, signedDegrees, temp, tempDelta, tempUnit } from "@/lib/units";

/** One row per date, with `c0_*`, `c1_*`... values per city in the user's units. Rain is cumulative. */
export interface CompareRow {
  date: string;
  [key: string]: string | number | null;
}

export function toCompareRows(data: CompareResponse, units: Units): CompareRow[] {
  const totals = data.cities.map(() => 0);
  return data.dates.map((date, i) => {
    const row: CompareRow = { date };
    data.cities.forEach((c, k) => {
      const precip = rain(c.series.precip?.[i], units);
      totals[k]! += precip ?? 0;
      row[`c${k}_tmean`] = temp(c.series.tmean?.[i], units);
      row[`c${k}_tmean7`] = temp(c.series.tmean_7d?.[i], units);
      row[`c${k}_anomaly`] = tempDelta(c.series.anomaly?.[i], units);
      row[`c${k}_precip`] = precip;
      row[`c${k}_rainTotal`] = totals[k]!;
    });
    return row;
  });
}

const num = (v: string | number | null | undefined) => (typeof v === "number" ? v : null);

function Legend({ cities }: { cities: CompareCity[] }) {
  return <>{cities.map((c, k) => <LegendItem key={c.city.id} color={seriesColor(k)} label={c.city.label} kind="line" />)}</>;
}

function CompareLines({ rows, cities, metric, format, axisFormat = format, zeroLine = false }: {
  rows: CompareRow[]; cities: CompareCity[]; metric: string; format: (v: number) => string;
  axisFormat?: (v: number) => string; zeroLine?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
        <CartesianGrid {...GRID} />
        <XAxis {...dateAxis(rows.length)} />
        <YAxis {...valueAxis(axisFormat)} domain={["auto", "auto"]} />
        {zeroLine && <ReferenceLine y={0} stroke={COLORS.axis} />}
        <Tooltip
          cursor={{ stroke: COLORS.grid }}
          content={(props) => (
            <ChartTooltip<CompareRow> {...props} rows={(row) => cities.map((c, k) => {
              const v = num(row[`c${k}_${metric}`]);
              return { label: c.city.name, value: v === null ? "no data" : format(v), color: seriesColor(k) };
            })} />
          )}
        />
        {cities.map((c, k) => (
          <Line key={c.city.id} dataKey={`c${k}_${metric}`} stroke={seriesColor(k)} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function columnsFor(cities: CompareCity[], metric: string, header: (name: string) => string) {
  return [
    { header: "date", value: (r: CompareRow) => r.date },
    ...cities.map((c, k) => ({ header: header(c.city.label), value: (r: CompareRow) => num(r[`c${k}_${metric}`]) })),
  ];
}

function lastValues(rows: CompareRow[], cities: CompareCity[], metric: string): string {
  const last = rows[rows.length - 1];
  return cities.map((c, k) => `${c.city.name} ${num(last?.[`c${k}_${metric}`])?.toFixed(1) ?? "no data"}`).join(", ");
}

export function CompareTemperatureChart({ rows, cities, units, days }: { rows: CompareRow[]; cities: CompareCity[]; units: Units; days: number }) {
  const u = tempUnit(units);
  return (
    <ChartCard
      title="Temperature"
      description="7-day mean of the daily average"
      filename={`compare-temperature-${days}d`}
      rows={rows}
      columns={[...columnsFor(cities, "tmean", (n) => `${n} mean ${u}`), ...columnsFor(cities, "tmean7", (n) => `${n} 7-day mean ${u}`).slice(1)]}
      summary={`7-day mean temperature over ${days} days. Latest: ${lastValues(rows, cities, "tmean7")} ${u}.`}
      legend={<Legend cities={cities} />}
    >
      <CompareLines rows={rows} cities={cities} metric="tmean7" format={(v) => `${Math.round(v)}°`} />
    </ChartCard>
  );
}

export function CompareAnomalyChart({ rows, cities, units, days }: { rows: CompareRow[]; cities: CompareCity[]; units: Units; days: number }) {
  return (
    <ChartCard
      title="Difference from normal"
      description="Each day against that city's own 1991–2020 average"
      filename={`compare-anomaly-${days}d`}
      rows={rows}
      columns={columnsFor(cities, "anomaly", (n) => `${n} difference ${tempUnit(units)}`)}
      summary={`Daily difference from each city's normal over ${days} days.`}
      legend={<Legend cities={cities} />}
    >
      <CompareLines rows={rows} cities={cities} metric="anomaly" format={(v) => signedDegrees(v)} zeroLine
                    axisFormat={(v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v))}°`} />
    </ChartCard>
  );
}

export function CompareRainChart({ rows, cities, units, days }: { rows: CompareRow[]; cities: CompareCity[]; units: Units; days: number }) {
  const unit = rainUnit(units);
  const digits = units === "imperial" ? 1 : 0;
  return (
    <ChartCard
      title="Rain, added up"
      description="Running total of precipitation"
      filename={`compare-rain-${days}d`}
      rows={rows}
      columns={[...columnsFor(cities, "precip", (n) => `${n} rain ${unit}`), ...columnsFor(cities, "rainTotal", (n) => `${n} running total ${unit}`).slice(1)]}
      summary={`Total precipitation over ${days} days: ${lastValues(rows, cities, "rainTotal")} ${unit}.`}
      legend={<Legend cities={cities} />}
    >
      <CompareLines rows={rows} cities={cities} metric="rainTotal" format={(v) => `${v.toFixed(digits)}`} />
    </ChartCard>
  );
}

/** The three overlaid charts (lazy-loaded with Recharts by the Compare page). */
export default function CompareCharts({ data, units }: { data: CompareResponse; units: Units }) {
  const rows = useMemo(() => toCompareRows(data, units), [data, units]);
  const withNormals = data.cities.some((c) => c.normals_available);
  return (
    <div className="space-y-4">
      <CompareTemperatureChart rows={rows} cities={data.cities} units={units} days={data.days} />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
        {withNormals && <CompareAnomalyChart rows={rows} cities={data.cities} units={units} days={data.days} />}
        <CompareRainChart rows={rows} cities={data.cities} units={units} days={data.days} />
      </div>
    </div>
  );
}
