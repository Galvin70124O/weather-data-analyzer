import { useReducedMotion } from "framer-motion";
import { useMemo } from "react";

import { cn } from "@/lib/utils";

// Meteocons by Bas Milius (MIT), named after OpenWeatherMap icon codes: 01d, 10n, ...
const ICONS = import.meta.glob("../../assets/weather-icons/*.svg", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

function svgFor(code: string): string | undefined {
  return ICONS[`../../assets/weather-icons/${code}.svg`];
}

/**
 * The icons animate with SVG <animate> tags inside the file, which CSS can't pause. For people
 * who prefer reduced motion we remove those tags, which leaves a still icon.
 */
export function stillSvg(svg: string): string {
  return svg.replace(/<animate(Transform|Motion)?\b[^>]*?(\/>|>[\s\S]*?<\/animate(Transform|Motion)?>)/g, "");
}

export function iconSource(code: string, reduceMotion: boolean): string | null {
  const svg = svgFor(code) ?? svgFor(`${code.slice(0, 2)}d`);    // unknown night code: use the day icon
  if (!svg) return null;
  // An <img> with a data: URL keeps each icon's internal ids (gradients) separate from the page
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(reduceMotion ? stillSvg(svg) : svg)}`;
}

export function WeatherIcon({ code, label, className }: {
  code: string;
  /** A short description ("light rain"). Leave out when the text next to the icon already says it. */
  label?: string;
  className?: string;
}) {
  const reduceMotion = useReducedMotion() ?? false;
  const src = useMemo(() => iconSource(code, reduceMotion), [code, reduceMotion]);
  if (!src) return null;
  return (
    <img
      src={src}
      alt={label ?? ""}
      aria-hidden={label ? undefined : true}
      draggable={false}
      className={cn("wx-icon pointer-events-none select-none", className)}
    />
  );
}
