import { Area, Bar, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { COLORS, ChartCard, ChartTooltip, GRID, LegendItem, dateAxis, valueAxis } from "@/components/charts/chart-kit";
import type { AnalyticsDay, Units } from "@/lib/types";
import { rain, rainUnit, signedDegrees, temp, tempDelta, tempUnit } from "@/lib/units";

/** Chart rows in the user's units (the API is metric). Missing stays null: the chart shows a gap. */
export interface ChartDay {
  date: string;
  tmin: number | null;
  tmax: number | null;
  tmean: number | null;
  tmean7: number | null;
  normalLow: number | null;
  normalHigh: number | null;
  normalMean: number | null;
  anomaly: number | null;
  precip: number | null;
  category: AnalyticsDay["category"];
  band: [number, number] | null;
  normalBand: [number, number] | null;
}

export function toChartDays(days: AnalyticsDay[], units: Units): ChartDay[] {
  return days.map((d) => {
    const tmin = temp(d.tmin, units);
    const tmax = temp(d.tmax, units);
    const normalLow = temp(d.normal_p10, units);
    const normalHigh = temp(d.normal_p90, units);
    return {
      date: d.date,
      tmin,
      tmax,
      tmean: temp(d.tmean, units),
      tmean7: temp(d.tmean_7d, units),
      normalLow,
      normalHigh,
      normalMean: temp(d.normal_tmean, units),
      anomaly: tempDelta(d.anomaly, units),
      precip: rain(d.precip, units),
      category: d.category,
      band: tmin !== null && tmax !== null ? [tmin, tmax] : null,
      normalBand: normalLow !== null && normalHigh !== null ? [normalLow, normalHigh] : null,
    };
  });
}

const fmt = (value: number | null, unit: string, digits = 1) => (value === null ? "no data" : `${value.toFixed(digits)}${unit}`);

export function TemperatureChart({ days, units, cityName, hasNormals }: { days: ChartDay[]; units: Units; cityName: string; hasNormals: boolean }) {
  const u = tempUnit(units);
  const withData = days.filter((d) => d.tmean !== null);
  const summary = withData.length
    ? `Daily temperatures for ${cityName} over ${days.length} days, from ${fmt(Math.min(...withData.map((d) => d.tmin ?? Infinity)), u)} to ${fmt(Math.max(...withData.map((d) => d.tmax ?? -Infinity)), u)}.`
    : "No temperature data for this period.";
  return (
    <ChartCard
      title="Temperature"
      description={hasNormals ? "Daily low–high, against the 1991–2020 normal range" : "Daily low–high"}
      filename={`${cityName}-temperature-${days.length}d`}
      rows={days}
      columns={[
        { header: "date", value: (d) => d.date },
        { header: `min ${u}`, value: (d) => d.tmin },
        { header: `max ${u}`, value: (d) => d.tmax },
        { header: `mean ${u}`, value: (d) => d.tmean },
        { header: `7-day mean ${u}`, value: (d) => d.tmean7 },
        { header: `normal low ${u}`, value: (d) => d.normalLow },
        { header: `normal high ${u}`, value: (d) => d.normalHigh },
      ]}
      summary={summary}
      legend={<>
        <LegendItem color={COLORS.band} label="Low–high" />
        {hasNormals && <LegendItem color={COLORS.normal} edge={COLORS.normalEdge} label="Normal range" />}
        <LegendItem color={COLORS.line} label="7-day mean" kind="line" />
        {hasNormals && <LegendItem color={COLORS.muted} label="Normal mean" kind="dash" />}
      </>}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...dateAxis(days.length)} />
          <YAxis {...valueAxis((v) => `${Math.round(v)}°`)} domain={["auto", "auto"]} />
          <Tooltip
            cursor={{ stroke: COLORS.grid }}
            content={(props) => (
              <ChartTooltip<ChartDay> {...props} rows={(d) => [
                { label: "High", value: fmt(d.tmax, u), color: COLORS.warm },
                { label: "Low", value: fmt(d.tmin, u), color: COLORS.cool },
                { label: "7-day mean", value: fmt(d.tmean7, u), color: COLORS.line },
                ...(hasNormals ? [{ label: "Normal", value: d.normalLow === null ? "no data" : `${fmt(d.normalLow, "", 0)}–${fmt(d.normalHigh, u, 0)}` }] : []),
              ]} />
            )}
          />
          {hasNormals && <Area dataKey="normalBand" stroke={COLORS.normalEdge} strokeWidth={1} strokeDasharray="3 3" fill={COLORS.normal} isAnimationActive={false} />}
          <Area dataKey="band" stroke={COLORS.bandEdge} strokeWidth={1} fill={COLORS.band} isAnimationActive={false} />
          {hasNormals && <Line dataKey="normalMean" stroke={COLORS.muted} strokeWidth={1.5} strokeDasharray="4 4" dot={false} isAnimationActive={false} />}
          <Line dataKey="tmean7" stroke={COLORS.line} strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AnomalyChart({ days, units, cityName }: { days: ChartDay[]; units: Units; cityName: string }) {
  const known = days.filter((d) => d.anomaly !== null);
  const warm = known.filter((d) => (d.anomaly ?? 0) > 0).length;
  return (
    <ChartCard
      title="Difference from normal"
      description="How much warmer or cooler each day was than the 1991–2020 average"
      filename={`${cityName}-anomaly-${days.length}d`}
      rows={days}
      columns={[
        { header: "date", value: (d) => d.date },
        { header: `difference ${tempUnit(units)}`, value: (d) => d.anomaly },
        { header: "category", value: (d) => d.category },
      ]}
      summary={`${warm} of ${known.length} days were warmer than normal, ${known.length - warm} cooler or equal.`}
      legend={<><LegendItem color={COLORS.warm} label="Warmer" /><LegendItem color={COLORS.cool} label="Cooler" /></>}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...dateAxis(days.length)} />
          <YAxis {...valueAxis((v) => `${v > 0 ? "+" : ""}${Math.round(v)}°`)} />
          <ReferenceLine y={0} stroke={COLORS.axis} />
          <Tooltip
            cursor={{ fill: COLORS.grid }}
            content={(props) => (
              <ChartTooltip<ChartDay> {...props} rows={(d) => [
                { label: "vs normal", value: d.anomaly === null ? "no data" : signedDegrees(d.anomaly) },
              ]} />
            )}
          />
          <Bar dataKey="anomaly" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {days.map((d) => <Cell key={d.date} fill={(d.anomaly ?? 0) > 0 ? COLORS.warm : COLORS.cool} />)}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function RainChart({ days, units, cityName }: { days: ChartDay[]; units: Units; cityName: string }) {
  const total = days.reduce((sum, d) => sum + (d.precip ?? 0), 0);       // already in the display unit
  return (
    <ChartCard
      title="Rain"
      description="Daily precipitation"
      filename={`${cityName}-rain-${days.length}d`}
      rows={days}
      columns={[{ header: "date", value: (d) => d.date }, { header: `precipitation ${rainUnit(units)}`, value: (d) => d.precip }]}
      summary={`Total precipitation over ${days.length} days: ${total.toFixed(units === "imperial" ? 2 : 1)} ${rainUnit(units)}.`}
      legend={<LegendItem color={COLORS.rain} label={`Rain (${rainUnit(units)})`} />}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...dateAxis(days.length)} />
          <YAxis {...valueAxis((v) => (units === "imperial" ? v.toFixed(1) : `${Math.round(v)}`))} />
          <Tooltip
            cursor={{ fill: COLORS.grid }}
            content={(props) => (
              <ChartTooltip<ChartDay> {...props} rows={(d) => [{ label: "Rain", value: d.precip === null ? "no data" : `${d.precip.toFixed(units === "imperial" ? 2 : 1)} ${rainUnit(units)}`, color: COLORS.rain }]} />
            )}
          />
          <Bar dataKey="precip" fill={COLORS.rain} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
