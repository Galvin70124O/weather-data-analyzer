/**
 * Shared look for EVERY chart: same palette (CSS tokens), axes, grid and tooltip, plus the card
 * with the "Export CSV" button. New charts should only be built from these pieces.
 */
import { Download } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadCsv, safeFilename, toCsv, type CsvColumn } from "@/lib/csv";
import { shortDate } from "@/lib/time";

export const COLORS = {
  grid: "var(--chart-grid)",
  axis: "var(--chart-axis)",
  band: "var(--chart-band)",
  normal: "var(--chart-normal)",
  line: "var(--chart-line)",
  muted: "var(--muted-foreground)",
  warm: "var(--warm)",
  cool: "var(--cool)",
  rain: "var(--chart-rain)",
  series: ["var(--series-1)", "var(--series-2)", "var(--series-3)"],
} as const;

const TICK = { fill: COLORS.axis, fontSize: 12 };

/** Props for <XAxis>: dates as "21 Oct", only a few labels so they never overlap. */
export function dateAxis(count: number) {
  return {
    dataKey: "date",
    tick: TICK,
    tickLine: false,
    axisLine: { stroke: COLORS.grid },
    tickFormatter: (value: string) => shortDate(value),
    // Evenly spaced labels; Recharts drops more of them when the chart is narrow (phones)
    interval: count > 6 ? ("equidistantPreserveStart" as const) : 0,
    minTickGap: 40,
  } as const;
}

export function valueAxis(format: (v: number) => string) {
  return { tick: TICK, tickLine: false, axisLine: false, width: 44, tickFormatter: format } as const;
}

export const GRID = { stroke: COLORS.grid, strokeDasharray: "3 3", vertical: false } as const;

export interface TooltipRow {
  label: string;
  value: string;
  color?: string;
}

/** One tooltip design for all charts. `rows(datum)` says what to show for the hovered day. */
export function ChartTooltip<T extends { date: string }>({ active, payload, rows }: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: T }>;
  rows: (datum: T) => TooltipRow[];
}) {
  const datum = payload?.[0]?.payload;
  if (!active || !datum) return null;
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-sm shadow-pop">
      <p className="mb-1 font-medium">{shortDate(datum.date)}</p>
      <dl className="space-y-0.5">
        {rows(datum).map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-6">
            <dt className="flex items-center gap-2 text-muted-foreground">
              {row.color && <span className="size-2 rounded-full" style={{ background: row.color }} aria-hidden="true" />}
              {row.label}
            </dt>
            <dd className="num font-medium">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function LegendItem({ color, label, kind = "swatch" }: { color: string; label: string; kind?: "swatch" | "line" | "dash" }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      {kind === "swatch" && <span className="h-2.5 w-3.5 rounded-sm" style={{ background: color }} aria-hidden="true" />}
      {kind === "line" && <span className="h-0.5 w-4 rounded-full" style={{ background: color }} aria-hidden="true" />}
      {kind === "dash" && <span className="w-4 border-t-2 border-dashed" style={{ borderColor: color }} aria-hidden="true" />}
      {label}
    </span>
  );
}

/** A chart in a card, with a title, a legend, an "Export CSV" button and an accessible text summary. */
export function ChartCard<Row>({ title, description, legend, rows, columns, filename, summary, children }: {
  title: string;
  description?: string;
  legend?: ReactNode;
  rows: Row[];
  columns: CsvColumn<Row>[];
  filename: string;
  /** Read by screen readers instead of the drawing. */
  summary: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex-nowrap">
        <div className="min-w-0 flex-1">
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription className="mt-1">{description}</CardDescription>}
        </div>
        <Button variant="outline" size="sm" className="shrink-0" onClick={() => downloadCsv(safeFilename(filename), toCsv(rows, columns))}>
          <Download aria-hidden="true" /> Export CSV
        </Button>
      </CardHeader>
      <CardContent className="pt-4">
        {legend && <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1">{legend}</div>}
        <figure>
          <div className="h-64 w-full sm:h-72" aria-hidden="true">{children}</div>
          <figcaption className="sr-only">{summary}</figcaption>
        </figure>
      </CardContent>
    </Card>
  );
}
