/**
 * Design self-check: full-page screenshots of each screen at 375px and 1440px, light and dark.
 *
 *   npm.cmd run screenshots              (needs the API on :8000 and `npm.cmd run dev` on :5173)
 *   $env:SHOTS_CITY = "Tokyo"; npm.cmd run screenshots
 *
 * Uses the installed Microsoft Edge (no browser download). Writes to docs/screenshots/v2/ and
 * prints any page that scrolls sideways. Full-page shots draw fixed bars (the mobile bottom nav,
 * the desktop sidebar) only once, where the first screen ends; the "-fold" shot shows the first
 * screen exactly as a phone does.
 */
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium, request } from "@playwright/test";

const BASE = process.env.SHOTS_BASE_URL ?? "http://localhost:5173";
const CITY = process.env.SHOTS_CITY ?? "London";
const OUT = resolve(import.meta.dirname, "../../docs/screenshots/v2");
const USER = { username: "screenshots", email: "screenshots@example.com", password: "screenshots-demo-pass" };
const WIDTHS = [375, 1440];
const MODES = ["light", "dark"];

async function signIn() {
  const api = await request.newContext({ baseURL: BASE, extraHTTPHeaders: { "Content-Type": "application/json" } });
  let res = await api.post("/api/auth/register", { data: USER });
  if (res.status() === 409) res = await api.post("/api/auth/login", { data: { identifier: USER.username, password: USER.password } });
  if (!res.ok()) throw new Error(`Sign-in failed: ${res.status()} ${await res.text()}`);
  const cities = await (await api.get(`/api/cities/search?q=${encodeURIComponent(CITY)}`)).json();
  if (!cities.length) throw new Error(`No city found for ${CITY}`);
  await api.post("/api/favorites", { data: { city_id: cities[0].id } });
  const state = await api.storageState();
  await api.dispose();
  return { state, cityId: cities[0].id };
}

async function shoot(browser, { name, path, width, mode, state, ready, fold = false }) {
  const context = await browser.newContext({
    viewport: { width, height: width < 600 ? 812 : 900 },
    colorScheme: mode,
    deviceScaleFactor: width < 600 ? 2 : 1,
    storageState: state,
  });
  await context.addInitScript((m) => localStorage.setItem("color-mode", m), mode);
  const page = await context.newPage();
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  if (ready) await page.waitForSelector(ready, { timeout: 60_000 });
  await page.waitForTimeout(800); // entrance transitions
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const file = resolve(OUT, `${name}-${width}-${mode}.png`);
  await page.screenshot({ path: file, fullPage: true, animations: "disabled" });
  console.log(`${overflow > 0 ? "OVERFLOW " + overflow + "px " : ""}${file}`);
  if (fold) await page.screenshot({ path: file.replace(".png", "-fold.png"), animations: "disabled" });
  await context.close();
}

await mkdir(OUT, { recursive: true });
const { state, cityId } = await signIn();
const browser = await chromium.launch({ channel: "msedge" });
try {
  for (const mode of MODES) {
    for (const width of WIDTHS) {
      await shoot(browser, { name: "login", path: "/login", width, mode, state: undefined, ready: "form" });
      await shoot(browser, { name: "register", path: "/register", width, mode, state: undefined, ready: "form" });
      await shoot(browser, { name: "city", path: `/cities/${cityId}`, width, mode, state, ready: ".recharts-surface", fold: width < 600 });
    }
  }
} finally {
  await browser.close();
}
