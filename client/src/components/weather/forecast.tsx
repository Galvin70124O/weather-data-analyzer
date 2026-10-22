import { Droplet } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WeatherIcon } from "@/components/weather/weather-icon";
import { localHour, weekdayShort } from "@/lib/time";
import type { DailyForecast as Day, HourlyStep, Units } from "@/lib/types";
import { formatRain, formatTemp, temp } from "@/lib/units";

/** The next 24 hours in 3-hour steps; scrolls sideways on small screens. */
export function HourlyStrip({ hours, offset, units, className }: { hours: HourlyStep[]; offset: number; units: Units; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader><CardTitle>Next 24 hours</CardTitle></CardHeader>
      <CardContent>
        <ol className="-mx-1 flex snap-x gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]" aria-label="Hourly forecast">
          {hours.map((hour, index) => (
            <li key={hour.time} className="flex min-w-[4.5rem] flex-1 snap-start flex-col items-center gap-1 rounded-md px-2 py-3 hover:bg-muted/60">
              <span className="num text-xs text-muted-foreground">{index === 0 ? "Now" : `${localHour(hour.time, offset)}:00`}</span>
              <WeatherIcon code={hour.icon} label={hour.description} className="size-11" />
              <span className="num text-base font-semibold">{formatTemp(hour.temp_c, units)}</span>
              <span className={`num flex items-center gap-0.5 text-xs ${hour.pop >= 0.2 ? "text-cool" : "text-transparent"}`} aria-hidden={hour.pop < 0.2}>
                <Droplet className="size-3" aria-hidden="true" />{Math.round(hour.pop * 100)}%
              </span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

/** Where a day's min..max sits on the week's overall range, as percentages for the bar. */
export function rangeBar(min: number, max: number, weekMin: number, weekMax: number): { left: number; width: number } {
  const span = weekMax - weekMin || 1;
  const left = ((min - weekMin) / span) * 100;
  const width = Math.max(((max - min) / span) * 100, 2);
  return { left: Math.min(Math.max(left, 0), 100 - width), width };
}

export function DailyForecast({ days, units, className }: { days: Day[]; units: Units; className?: string }) {
  if (!days.length) return null;
  const mins = days.map((d) => temp(d.temp_min_c, units) ?? 0);
  const maxes = days.map((d) => temp(d.temp_max_c, units) ?? 0);
  const weekMin = Math.min(...mins);
  const weekMax = Math.max(...maxes);
  return (
    <Card className={className}>
      <CardHeader><CardTitle>5-day forecast</CardTitle></CardHeader>
      <CardContent className="pt-3 sm:pt-4">
        <ol className="divide-y divide-border">
          {days.map((day, index) => {
            const bar = rangeBar(mins[index] ?? 0, maxes[index] ?? 0, weekMin, weekMax);
            return (
              <li key={day.date} className="grid grid-cols-[3rem_2.25rem_2.25rem_2.25rem_1fr_2.25rem] items-center gap-2 py-2.5 sm:grid-cols-[4rem_2.75rem_3rem_2.5rem_1fr_2.5rem] sm:gap-3 xl:py-3">
                <span className="text-sm font-medium">{index === 0 ? "Today" : weekdayShort(day.date)}</span>
                <WeatherIcon code={day.icon} label={day.description} className="size-10" />
                {/* Chance of rain and how much, only when it is likely to matter */}
                <span className="num flex flex-col text-xs leading-tight text-cool">
                  {day.pop_max >= 0.2 && <span>{Math.round(day.pop_max * 100)}%</span>}
                  {day.rain_mm >= 0.1 && <span className="hidden text-muted-foreground sm:inline">{formatRain(day.rain_mm, units)}</span>}
                </span>
                <span className="num text-right text-sm text-muted-foreground">{formatTemp(day.temp_min_c, units)}</span>
                <span className="relative h-1.5 rounded-full bg-muted" aria-hidden="true">
                  <span className="absolute inset-y-0 rounded-full bg-gradient-to-r from-chart-cool to-chart-warm"
                        style={{ left: `${bar.left}%`, width: `${bar.width}%` }} />
                </span>
                <span className="num text-sm font-semibold">{formatTemp(day.temp_max_c, units)}</span>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
