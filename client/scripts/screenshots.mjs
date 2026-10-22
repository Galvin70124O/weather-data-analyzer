/**
 * Design self-check: screenshots of each screen at 375px and 1440px, light and dark.
 *
 *   npm.cmd run screenshots              (needs the API on :8000 and `npm.cmd run dev` on :5173)
 *   $env:SHOTS_ONLY = "city"; npm.cmd run screenshots     (only shots whose name contains "city")
 *
 * Uses the installed Microsoft Edge (no browser download). Writes to docs/screenshots/v2/ and
 * prints OVERFLOW for any page that scrolls sideways.
 *
 * - Full-page shots draw fixed bars (the mobile bottom nav) once, where the first screen ends;
 *   "-fold" shots show the first phone screen and "-scrolled" shots a desktop screen further
 *   down the page (sticky sidebar), exactly as a browser shows them.
 * - Weather scenarios: the real /weather answer is rewritten in the browser so every theme
 *   (clear day, clear night, rain, clouds, snow) can be checked whatever the sky is doing.
 */
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium, request } from "@playwright/test";

const BASE = process.env.SHOTS_BASE_URL ?? "http://localhost:5173";
const ONLY = process.env.SHOTS_ONLY ?? "";
const OUT = resolve(import.meta.dirname, "../../docs/screenshots/v2");
const USER = { username: "screenshots", email: "screenshots@example.com", password: "screenshots-demo-pass" };
const FAVOURITES = ["London", "Tokyo", "Cairo"];
const WIDTHS = [375, 1440];
const MODES = ["light", "dark"];

// clouds = cloud cover %, pop = chance of rain/snow now and today, so every number on the page agrees
const SCENARIOS = {
  "clear-day": { theme: "clear-day", icon: "01d", condition: "Clear", condition_id: 800, description: "clear sky", night: false, clouds: 3, pop: 0 },
  "clear-night": { theme: "clear-night", icon: "01n", condition: "Clear", condition_id: 800, description: "clear sky", night: true, clouds: 2, pop: 0 },
  rain: { theme: "rain", icon: "10d", condition: "Rain", condition_id: 501, description: "moderate rain", night: false, clouds: 92, pop: 0.9 },
  clouds: { theme: "clouds", icon: "04d", condition: "Clouds", condition_id: 803, description: "broken clouds", night: false, clouds: 75, pop: 0.1 },
  snow: { theme: "snow", icon: "13d", condition: "Snow", condition_id: 601, description: "snow", night: false, clouds: 96, pop: 0.8 },
};

const CONDITION = ["theme", "icon", "condition", "condition_id", "description"];
const conditionOf = (s) => Object.fromEntries(CONDITION.map((key) => [key, s[key]]));

async function signIn() {
  const api = await request.newContext({ baseURL: BASE, extraHTTPHeaders: { "Content-Type": "application/json" } });
  let res = await api.post("/api/auth/register", { data: USER });
  if (res.status() === 409) res = await api.post("/api/auth/login", { data: { identifier: USER.username, password: USER.password } });
  if (!res.ok()) throw new Error(`Sign-in failed: ${res.status()} ${await res.text()}`);
  const ids = [];
  for (const name of FAVOURITES) {
    const cities = await (await api.get(`/api/cities/search?q=${encodeURIComponent(name)}`)).json();
    if (!cities.length) throw new Error(`No city found for ${name}`);
    ids.push(cities[0].id);
    await api.post("/api/favorites", { data: { city_id: cities[0].id } });
    await api.get(`/api/cities/${cities[0].id}/weather`);   // also fills recent searches and saved readings
  }
  const state = await api.storageState();
  await api.dispose();
  return { state, ids };
}

/**
 * Rewrites GET /api/cities/:id/weather (and the "Now" hour and today's row of the forecast) so the
 * page shows the given condition and time of day consistently: hero, cloud cover, hourly, 5-day.
 */
async function fakeWeather(page, scenario) {
  await page.route(/\/api\/cities\/\d+\/forecast$/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    if (body.hourly?.[0]) Object.assign(body.hourly[0], conditionOf(scenario), { pop: scenario.pop });
    if (body.daily?.[0]) {
      Object.assign(body.daily[0], conditionOf({ ...scenario, icon: scenario.icon.replace("n", "d") }), { pop_max: scenario.pop });
      if (scenario.pop === 0) body.daily[0].rain_mm = 0;
    }
    await route.fulfill({ response, json: body });
  });
  await page.route(/\/api\/cities\/\d+\/weather$/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const w = body.weather;
    Object.assign(w, conditionOf(scenario), { clouds_pct: scenario.clouds });
    const rise = new Date(w.sunrise ?? Date.now()).getTime();
    const set = new Date(w.sunset ?? Date.now()).getTime();
    w.observed_at = new Date(scenario.night ? set + 3 * 3600_000 : (rise + set) / 2).toISOString();
    w.is_day = !scenario.night;
    await route.fulfill({ response, json: body });
  });
}

async function shoot(browser, { name, path, width, mode, state, ready, scenario, action, fold = false, scrolled = false, fullPage = true }) {
  if (ONLY && !name.includes(ONLY)) return;
  const context = await browser.newContext({
    viewport: { width, height: width < 600 ? 812 : 900 },
    colorScheme: mode,
    deviceScaleFactor: width < 600 ? 2 : 1,
    storageState: state,
  });
  await context.addInitScript((m) => localStorage.setItem("color-mode", m), mode);
  const page = await context.newPage();
  if (scenario) await fakeWeather(page, SCENARIOS[scenario]);
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  if (ready) await page.waitForSelector(ready, { timeout: 60_000 });
  if (action) await action(page);
  await page.waitForTimeout(800); // entrance transitions
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const file = resolve(OUT, `${name}-${width}-${mode}.png`);
  await page.screenshot({ path: file, fullPage, animations: "disabled" });
  console.log(`${overflow > 0 ? `OVERFLOW ${overflow}px ` : ""}${file}`);
  if (fold) await page.screenshot({ path: file.replace(".png", "-fold.png"), animations: "disabled" });
  if (scrolled) {
    await page.evaluate(() => window.scrollTo(0, 1200));
    await page.waitForTimeout(300);
    await page.screenshot({ path: file.replace(".png", "-scrolled.png"), animations: "disabled" });
  }
  await context.close();
}

await mkdir(OUT, { recursive: true });
const { state, ids } = await signIn();
const browser = await chromium.launch({ channel: "msedge" });
try {
  for (const mode of MODES) {
    for (const width of WIDTHS) {
      const mobile = width < 600;
      await shoot(browser, { name: "login", path: "/login", width, mode, ready: "form" });
      await shoot(browser, { name: "register", path: "/register", width, mode, ready: "form" });
      for (const scenario of Object.keys(SCENARIOS)) {
        await shoot(browser, {
          name: `city-${scenario}`, path: `/cities/${ids[0]}`, width, mode, state, scenario, ready: ".recharts-surface",
          fold: mobile && scenario === "clouds", scrolled: !mobile && scenario === "clouds",
        });
      }
      await shoot(browser, { name: "dashboard", path: "/", width, mode, state, ready: "a[data-wx]", fold: mobile });
      await shoot(browser, {
        name: "search", path: "/", width, mode, state, ready: "a[data-wx]", fullPage: false,   // a dialog: the screen as seen
        action: async (page) => {
          await page.keyboard.press("Control+k");
          await page.keyboard.type("Paris");
          await page.waitForSelector("[cmdk-item]", { timeout: 30_000 });
        },
      });
      await shoot(browser, { name: "compare", path: `/compare?ids=${ids.join(",")}&days=30`, width, mode, state, ready: ".recharts-surface" });
      await shoot(browser, { name: "compare-empty", path: "/compare", width, mode, state, ready: "main h1" });
      await shoot(browser, { name: "history", path: "/history", width, mode, state, ready: "main h1 ~ * , table, ul" });
      await shoot(browser, { name: "account", path: "/account", width, mode, state, ready: "form" });
    }
  }
} finally {
  await browser.close();
}
