/**
 * WCAG AA for every theme: parses globals.css, resolves the tokens for each mode (light/dark) x
 * weather theme x time of day, and checks text pairs (4.5:1) and chart/UI graphics (3:1).
 * Translucent colours (glass, the 10% warm note) are blended onto what they sit on first.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Read from disk: Vitest replaces CSS imports (even ?raw) with an empty string. Tests run from client/.
const css = readFileSync(resolve(process.cwd(), "src/styles/globals.css"), "utf-8").replace(/\/\*[\s\S]*?\*\//g, "");

type Vars = Record<string, string>;
type Rgba = [number, number, number, number];

function block(selector: string): Vars {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`(?:^|\\n|\\})\\s*${escaped}\\s*\\{([^}]*)\\}`).exec(css);
  if (!match) throw new Error(`No CSS block for ${selector}`);
  const vars: Vars = {};
  for (const [, name, value] of match[1]!.matchAll(/--([\w-]+)\s*:\s*([^;]+);/g)) vars[name!] = value!.trim();
  return vars;
}

function parse(color: string): Rgba {
  const hex = /^#([0-9a-f]{6})$/i.exec(color);
  if (hex) {
    const n = parseInt(hex[1]!, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  const rgb = /^rgb\((\d+) (\d+) (\d+)(?: \/ ([\d.]+))?\)$/.exec(color);
  if (rgb) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3]), rgb[4] ? Number(rgb[4]) : 1];
  throw new Error(`Can't parse colour ${color}`);
}

/** Paint `top` over an opaque `bottom`. */
function over(top: Rgba, bottom: Rgba): Rgba {
  const a = top[3];
  return [top[0] * a + bottom[0] * (1 - a), top[1] * a + bottom[1] * (1 - a), top[2] * a + bottom[2] * (1 - a), 1];
}

function luminance([r, g, b]: Rgba): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

export function contrast(a: Rgba, b: Rgba): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const WX = ["clear-day", "clear-night", "clouds", "rain", "storm", "snow", "mist"] as const;

function tokens(mode: "light" | "dark", wx: (typeof WX)[number] | null, night: boolean): Vars {
  const dark = mode === "dark" ? ".dark" : "";
  let vars = { ...block(":root"), ...(dark ? block(".dark") : {}) };
  if (wx) vars = { ...vars, ...block(`${dark}[data-wx="${wx}"]`) };
  if (wx && night && wx !== "clear-night") vars = { ...vars, ...block(`${dark}[data-tod="night"]:not([data-wx="clear-night"])`) };
  return vars;
}

const cases = (["light", "dark"] as const).flatMap((mode) => [
  { name: `${mode} / default`, vars: tokens(mode, null, false) },
  ...WX.flatMap((wx) => [false, true].map((night) => ({ name: `${mode} / ${wx}${night ? " / night" : ""}`, vars: tokens(mode, wx, night) }))),
]);

describe.each(cases)("tokens: $name", ({ vars }) => {
  const c = (name: string) => parse(vars[name] ?? (() => { throw new Error(`missing --${name}`); })());
  const background = c("background");
  // Everything the page's text can sit on: plain surfaces, the gradient stops, and glass over each of them
  const pageSurfaces = [background, over(c("wx-1"), background), over(c("wx-2"), background)];
  const surfaces = [
    ...pageSurfaces,
    c("card"),
    c("muted"),
    ...pageSurfaces.map((s) => over(c("glass"), s)),
  ];

  it.each(["foreground", "muted-foreground"])("%s text is AA (4.5:1) on every surface", (name) => {
    for (const surface of surfaces) expect(contrast(c(name), surface)).toBeGreaterThanOrEqual(4.5);
  });

  it("accent-foreground is readable on accent (buttons, active °C/°F)", () => {
    expect(contrast(c("accent-foreground"), c("accent"))).toBeGreaterThanOrEqual(4.5);
  });

  it("accent (focus ring, active nav, links) is 3:1 on every surface", () => {
    for (const surface of surfaces) expect(contrast(c("accent"), surface)).toBeGreaterThanOrEqual(3);
  });

  it("status colours used as text are AA on cards and on their own 10% tint", () => {
    for (const name of ["warm", "cool", "destructive", "success"]) {
      for (const surface of [c("card"), background]) {
        expect(contrast(c(name), surface)).toBeGreaterThanOrEqual(4.5);
        const tint = over([...c(name).slice(0, 3), 0.1] as Rgba, surface);
        expect(contrast(c(name), tint)).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it("chart axis text is AA and chart marks are 3:1 on cards", () => {
    expect(contrast(c("chart-axis"), c("card"))).toBeGreaterThanOrEqual(4.5);
    for (const name of ["chart-line", "chart-rain", "warm", "cool", "series-1", "series-2", "series-3"]) {
      expect(contrast(c(name), c("card"))).toBeGreaterThanOrEqual(3);
    }
  });
});

describe("contrast()", () => {
  it("matches known WCAG values", () => {
    expect(contrast([0, 0, 0, 1], [255, 255, 255, 1])).toBeCloseTo(21, 5);
    expect(contrast([119, 119, 119, 1], [255, 255, 255, 1])).toBeCloseTo(4.48, 2);
  });
});
