import { useEffect } from "react";

import type { CurrentWeather } from "@/lib/types";
import { applyWeatherTheme, themeFor } from "@/lib/weather-theme";

/** While a city page is open, the whole app takes on that city's weather look; leaving resets it. */
export function useWeatherTheme(weather: CurrentWeather | undefined): void {
  useEffect(() => {
    if (!weather) return;
    applyWeatherTheme(themeFor(weather));
  }, [weather]);

  useEffect(() => () => applyWeatherTheme(null), []);
}
