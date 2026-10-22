import { motion } from "framer-motion";
import { ArrowUp, Clock, Cloud, Droplets, Gauge, Star, Sunrise, Sunset, Wind } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/misc";
import { WeatherIcon } from "@/components/weather/weather-icon";
import { localTime, localWeekday, utcOffsetLabel } from "@/lib/time";
import type { City, CurrentWeather, DailyForecast, Units } from "@/lib/types";
import { compass, formatTemp, formatWind } from "@/lib/units";

export function StatChip({ icon, label, value, title }: { icon: ReactNode; label: string; value: ReactNode; title?: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 rounded-md border border-border/70 bg-card/55 px-2.5 py-2.5 sm:gap-3 sm:px-3" title={title}>
      <span className="text-muted-foreground [&_svg]:size-4" aria-hidden="true">{icon}</span>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="num whitespace-nowrap text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

/** The city's local clock, updated every minute. */
function useNow(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

export function CityHero({ city, weather, today, units, stale, isFavorite, onToggleFavorite, className }: {
  city: City;
  weather: CurrentWeather;
  today?: DailyForecast;
  units: Units;
  stale: boolean;
  isFavorite: boolean;
  onToggleFavorite: () => void;
  className?: string;
}) {
  const now = useNow();
  const offset = weather.timezone_offset_s;
  const place = [city.state, city.country].filter(Boolean).join(", ");
  const windArrow = weather.wind_deg === null ? null : (
    // wind_deg = where the wind comes FROM; the arrow points where it blows TO
    <ArrowUp className="inline size-3.5 align-[-2px]" style={{ transform: `rotate(${weather.wind_deg + 180}deg)` }} aria-hidden="true" />
  );

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} aria-labelledby="city-name" className={className}>
      <Card className="wx-hero h-full overflow-hidden border-border/60">
        <div className="flex flex-col gap-6 p-5 sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 id="city-name" className="truncate text-2xl font-semibold tracking-tight sm:text-3xl">{city.name}</h1>
              <p className="mt-1 flex flex-col gap-x-2 gap-y-0.5 text-sm text-muted-foreground sm:flex-row sm:items-center">
                <span>{place}</span>
                <span aria-hidden="true" className="hidden sm:inline">·</span>
                <span className="num inline-flex items-center gap-1">
                  <Clock className="size-3.5" aria-hidden="true" />
                  {localWeekday(now, offset)} {localTime(now, offset)}
                  <span className="sr-only"> local time</span> ({utcOffsetLabel(offset)})
                </span>
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {stale && <Badge tone="warning" title="The weather service didn't answer; this is the last saved reading.">Stale data</Badge>}
              <Button variant="ghost" size="icon" onClick={onToggleFavorite} aria-pressed={isFavorite}
                      aria-label={isFavorite ? `Remove ${city.name} from favourites` : `Add ${city.name} to favourites`}>
                <Star className={isFavorite ? "fill-accent text-accent" : ""} />
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-6">
            <WeatherIcon code={weather.icon} className="-my-2 size-20 shrink-0 sm:-my-4 sm:size-36" />
            <div className="min-w-0">
              <p className="num text-6xl font-light leading-none tracking-tighter sm:text-8xl">
                {formatTemp(weather.temp_c, units)}
                <span className="sr-only">{units === "imperial" ? " Fahrenheit" : " Celsius"}</span>
              </p>
              <p className="mt-2 text-lg font-medium capitalize">{weather.description}</p>
              <p className="num mt-0.5 text-sm text-muted-foreground">
                Feels like {formatTemp(weather.feels_like_c, units)}
                {today && <> · H {formatTemp(today.temp_max_c, units)} · L {formatTemp(today.temp_min_c, units)}</>}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <StatChip icon={<Droplets />} label="Humidity" value={`${weather.humidity}%`} />
            <StatChip
              icon={<Wind />}
              label={weather.wind_deg === null ? "Wind" : `Wind · ${compass(weather.wind_deg)}`}
              title={weather.wind_gust_ms ? `Gusts ${formatWind(weather.wind_gust_ms, units)}` : undefined}
              value={<>{windArrow} {formatWind(weather.wind_speed_ms, units)}</>}
            />
            <StatChip icon={<Gauge />} label="Pressure" value={`${weather.pressure_hpa} hPa`} />
            <StatChip icon={<Cloud />} label="Cloud cover" value={weather.clouds_pct === null ? "–" : `${weather.clouds_pct}%`} />
            <StatChip icon={<Sunrise />} label="Sunrise" value={weather.sunrise ? localTime(weather.sunrise, offset) : "–"} />
            <StatChip icon={<Sunset />} label="Sunset" value={weather.sunset ? localTime(weather.sunset, offset) : "–"} />
          </div>
        </div>
      </Card>
    </motion.section>
  );
}
