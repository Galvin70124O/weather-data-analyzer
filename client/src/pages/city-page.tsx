import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { useParams } from "react-router-dom";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { ErrorState } from "@/components/ui/states";
import { CityHero } from "@/components/weather/city-hero";
import { DailyForecast, HourlyStrip } from "@/components/weather/forecast";
import { useUnits } from "@/hooks/use-auth";
import { useWeatherTheme } from "@/hooks/use-weather-theme";
import { api, ApiError } from "@/lib/api";

// The charts (Recharts) are most of the bundle: load them only when a City page opens
const AnalyticsSection = lazy(() => import("@/components/charts/analytics-section").then((m) => ({ default: m.AnalyticsSection })));

function HeroSkeleton() {
  return (
    <Card glass aria-hidden="true">
      <CardContent className="space-y-6 sm:p-8">
        <Skeleton className="h-8 w-48" />
        <div className="flex items-center gap-6"><Skeleton className="size-28 rounded-full" /><Skeleton className="h-20 w-40" /></div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-14" />)}</div>
      </CardContent>
    </Card>
  );
}

export function CityPage() {
  const cityId = Number(useParams().cityId);
  const { units } = useUnits();
  const client = useQueryClient();

  const weather = useQuery({ queryKey: ["weather", cityId], queryFn: () => api.weather(cityId), staleTime: 5 * 60_000 });
  const forecast = useQuery({ queryKey: ["forecast", cityId], queryFn: () => api.forecast(cityId), staleTime: 30 * 60_000 });
  const favorites = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });
  const isFavorite = favorites.data?.some((f) => f.city.id === cityId) ?? false;
  const toggleFavorite = useMutation({
    mutationFn: async () => {
      if (isFavorite) await api.removeFavorite(cityId);
      else await api.addFavorite(cityId);
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["favorites"] }),
  });

  useWeatherTheme(weather.data?.weather);

  if (weather.isError) {
    const notFound = weather.error instanceof ApiError && weather.error.status === 404;
    return (
      <ErrorState
        title={notFound ? "We couldn't find that city" : "The weather service didn't answer"}
        message={weather.error instanceof ApiError ? weather.error.message : undefined}
        onRetry={notFound ? undefined : () => weather.refetch()}
      />
    );
  }

  // Phones: hero, hourly, 5-day. xl: hero and 5-day side by side, hourly full width below.
  // minmax(0, ...) everywhere so the sideways-scrolling hourly strip can't widen the page.
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        {weather.data ? (
          <CityHero
            className="xl:col-start-1 xl:row-start-1"
            city={weather.data.city}
            weather={weather.data.weather}
            today={forecast.data?.daily[0]}
            units={units}
            stale={weather.data.stale}
            isFavorite={isFavorite}
            onToggleFavorite={() => toggleFavorite.mutate()}
          />
        ) : (
          <HeroSkeleton />
        )}

        {forecast.isError ? (
          <div className="xl:col-span-2">
            <ErrorState title="The forecast isn't available right now" onRetry={() => forecast.refetch()} />
          </div>
        ) : forecast.data ? (
          <>
            <HourlyStrip className="xl:col-span-2 xl:row-start-2" hours={forecast.data.hourly} offset={forecast.data.timezone_offset_s} units={units} />
            <DailyForecast className="xl:col-start-2 xl:row-start-1" days={forecast.data.daily} units={units} />
          </>
        ) : (
          <>
            <Skeleton className="h-48 xl:col-span-2 xl:row-start-2" aria-hidden="true" />
            <Skeleton className="h-80 xl:col-start-2 xl:row-start-1" aria-hidden="true" />
          </>
        )}
      </div>

      <Suspense fallback={<Skeleton className="h-96" aria-hidden="true" />}>
        <AnalyticsSection cityId={cityId} cityName={weather.data?.city.name ?? "city"} units={units} />
      </Suspense>
    </div>
  );
}
