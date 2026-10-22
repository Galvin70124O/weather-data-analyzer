import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Clock, CloudOff, Search, Star, X } from "lucide-react";
import { Link } from "react-router-dom";

import { useSearch } from "@/components/search/command-palette";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { WeatherIcon } from "@/components/weather/weather-icon";
import { useUnits } from "@/hooks/use-auth";
import { api, ApiError } from "@/lib/api";
import { localTime } from "@/lib/time";
import type { DashboardCard, RecentSearch, Units } from "@/lib/types";
import { formatTemp } from "@/lib/units";
import { themeFor } from "@/lib/weather-theme";

/** "Good morning" / "Good afternoon" / "Good evening" by the viewer's own clock. */
export function greeting(hour: number): string {
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 18) return "Good afternoon";
  return "Good evening";
}

/** A favourite city in its own weather gradient: the card carries data-wx/data-tod itself. */
export function CityCard({ card, units, onRetry }: { card: DashboardCard; units: Units; onRetry: () => void }) {
  const { city, weather } = card;
  if (!weather) {
    return (
      <Card className="flex h-full flex-col justify-between gap-4 p-4 sm:p-5">
        <div>
          <p className="font-semibold">{city.name}</p>
          <p className="text-sm text-muted-foreground">{city.label}</p>
        </div>
        <div className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-sm text-muted-foreground"><CloudOff className="size-4" aria-hidden="true" />{card.error ?? "No weather right now."}</p>
          <Button variant="outline" size="sm" onClick={onRetry}>Retry</Button>
        </div>
      </Card>
    );
  }
  const theme = themeFor(weather);
  return (
    <Link
      to={`/cities/${city.id}`}
      data-wx={theme.wx}
      data-tod={theme.tod}
      className="wx-hero group flex h-full flex-col justify-between gap-2 rounded-lg border border-border/60 p-4 shadow-card transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:gap-6 sm:p-5"
      aria-label={`${city.label}: ${formatTemp(weather.temp_c, units, true)}, ${weather.description}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-lg font-semibold">{city.name}</p>
          <p className="truncate text-sm text-muted-foreground">{city.label.slice(city.name.length + 2) || city.country}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {card.stale && <Badge tone="warning">Stale data</Badge>}
          <span className="num flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="size-3.5" aria-hidden="true" />{localTime(new Date(), weather.timezone_offset_s)}
          </span>
        </div>
      </div>
      {/* Phones: icon, temperature and condition on one row; wider: temperature left, icon right */}
      <div className="flex items-center gap-3 sm:items-end sm:justify-between">
        <WeatherIcon code={weather.icon} className="-my-1 size-12 shrink-0 sm:order-last sm:-mb-2 sm:-mr-2 sm:size-20" />
        <p className="num text-4xl font-light leading-none tracking-tighter sm:hidden">{formatTemp(weather.temp_c, units)}</p>
        <div className="min-w-0">
          <p className="num hidden text-5xl font-light leading-none tracking-tighter sm:block">{formatTemp(weather.temp_c, units)}</p>
          <p className="truncate font-medium capitalize sm:mt-2">{weather.description}</p>
          <p className="num text-sm text-muted-foreground">Feels like {formatTemp(weather.feels_like_c, units)}</p>
        </div>
      </div>
    </Link>
  );
}

function RecentSearches({ recent }: { recent: RecentSearch[] }) {
  const client = useQueryClient();
  const clear = useMutation({
    mutationFn: api.clearRecentSearches,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["recent-searches"] });
    },
  });
  return (
    <section aria-labelledby="recent-title" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 id="recent-title" className="text-lg font-semibold tracking-tight">Recent searches</h2>
        {recent.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => clear.mutate()} disabled={clear.isPending}>
            <X aria-hidden="true" /> Clear
          </Button>
        )}
      </div>
      {recent.length ? (
        <ul className="flex flex-wrap gap-2">
          {recent.map(({ city }) => (
            <li key={city.id}>
              <Link to={`/cities/${city.id}`} className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-sm hover:bg-muted focus-visible:outline-2 focus-visible:outline-accent">
                <Clock className="size-3.5 text-muted-foreground" aria-hidden="true" />{city.label}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">Cities you open show up here.</p>
      )}
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
      {[0, 1, 2].map((i) => <Skeleton key={i} className="h-48" />)}
    </div>
  );
}

export function DashboardPage() {
  const { units } = useUnits();
  const { openSearch } = useSearch();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard, staleTime: 5 * 60_000 });
  const data = dashboard.data;

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {greeting(new Date().getHours())}{data ? `, ${data.username}` : ""}
          </h1>
          <p className="text-muted-foreground">Your cities right now.</p>
        </div>
        {/* Phones search from the bottom nav */}
        <Button variant="outline" className="hidden sm:inline-flex" onClick={() => openSearch()}><Search aria-hidden="true" /> Find a city</Button>
      </div>

      <section aria-labelledby="favourites-title" className="space-y-3">
        <h2 id="favourites-title" className="sr-only">Favourite cities</h2>
        {dashboard.isPending && <DashboardSkeleton />}
        {dashboard.isError && (
          <ErrorState title="Your dashboard didn't load" message={dashboard.error instanceof ApiError ? dashboard.error.message : undefined}
                      onRetry={() => dashboard.refetch()} />
        )}
        {data && (data.favorites.length ? (
          <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-3">
            {data.favorites.map((card, index) => (
              <motion.div key={card.city.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
                <CityCard card={card} units={units} onRetry={() => dashboard.refetch()} />
              </motion.div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Star />}
            title="No favourite cities yet"
            message="Find a city and tap the star on its page. Your favourites show up here with their live weather."
            action={<Button onClick={() => openSearch()}><Search aria-hidden="true" /> Find a city</Button>}
          />
        ))}
      </section>

      {data && <RecentSearches recent={data.recent} />}
    </div>
  );
}
