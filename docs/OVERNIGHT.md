# Overnight report

Work log while you were asleep. Every stage was committed separately (nothing pushed or deployed,
`.env` untouched). Commit hashes and the morning checklist are filled in at the end.

## Decisions (stage A)

- **Weather palette:** each theme has three hero stops (`--hero-1..3`) for the City hero and login
  scene, and two softer backdrop stops (`--wx-1/2`, the hero stops mixed into the page background).
  I tuned them with a small script against the same rules as `tokens.test.ts`; the test now also
  checks text on every hero stop, on the stat chips over the hero and on glass over the scene.
- **Light muted text** darkened from `#4a5568` to `#3f4a5c`. Stronger contrast everywhere, and it
  leaves room for more colourful light gradients. Light rain accent darkened to `#155e75` (it was
  under 3:1 on the night-rain gradient).
- **Chart marks vs text:** `--chart-warm`/`--chart-cool` are new mark colours (3:1 on cards:
  orange `#ea580c`, blue `#2563eb` in light). `--warm`/`--cool` stay for text (4.5:1).
- **Temperature chart:** low–high band = light warm fill with a thin warm edge; normal range = cool
  blue fill with dashed edges. The legend swatch shows the dashed edge too.
- **Sidebar:** the aside is a full-height column (so its background runs the whole page) holding a
  `sticky top-0 h-screen` nav. Checked with a scrolled 1440px viewport shot.
- **Wind chip:** the direction moved into the label ("Wind · SW") so the value stays on one line.
- **5-day card:** rain amount per day under the rain chance (desktop/tablet; on phones only the
  chance, so the range bars keep their width). Rows are a bit taller on xl, so the card lines up
  with the hero.
- **Login scene (item 11):** your message was cut off after "on desktop a light". I read it with
  your follow-up ("themed login backdrop"): the login/register background uses the clear-day or
  clear-night scene by the visitor's own clock (no city is known yet), and on desktop there is a
  left panel with the weather icon, a one-line pitch and three features. Show/hide password toggle
  on every password field. Login no longer disables its button; it explains empty fields.
- **Screenshots of every theme:** `screenshots.mjs` rewrites the real `/weather` answer in the
  browser (condition, icon, time of day), so clear-day, clear-night, rain, clouds and snow are all
  shot from the same city whatever the sky is doing.

## Decisions (stage B)

- **Search (Ctrl+K):** one palette for the whole app (Radix Dialog + cmdk), opened by Ctrl+K/⌘K,
  the header button (sm and up) and a "Search" tab in the phone bottom nav (the 375px header has no
  room left). 250 ms debounce, 2-letter minimum (the server's), recent searches when empty.
  Compare reuses it in "pick" mode.
- **Layout route:** all logged-in pages share one `RequireLogin` layout (search + shell), so the
  shell isn't rebuilt on every navigation.
- **Per-card themes:** dashboard cards carry `data-wx`/`data-tod` themselves. The dark theme
  selectors now also match nested elements (`.dark [data-wx]`); `tokens.test.ts` checks the nested
  form equals the `<html>` form.
- **Colour mode** is a small shared store (header toggle and Account page always agree).
- **Compare:** cities and period live in the URL (`/compare?ids=3,7&days=90`). City *i* always uses
  `--series-i` (chip dot, lines, table header). Rain is shown as a running total (daily bars of 3
  cities over 365 days are unreadable). Light `--series-2` brightened to amber `#d97706` (3.2:1).
- **History:** the API had only `limit`; I added `offset` (stable order by time, then id) and
  `GET /api/history/cities` (cities you have readings for, for the filter). Both scoped to the
  user, with tests. Pages of 20 (asks for 21 to know if there is a next page). Export CSV fetches
  every matching reading in batches of 500. Times are in the viewer's own time zone (a reading is
  "when you looked"; the CSV has UTC). Phones get a list instead of the table.
- **City labels:** a state with the same name as the city is left out ("Cairo, EG", not
  "Cairo, Cairo, EG"), in `City.label`, with a test.
- **Stale badge:** City page, dashboard cards and Compare. Saved readings (History) are records,
  so "stale" doesn't apply there.
- **Account:** units and appearance as segmented controls, change password (same rules as the
  server; other sessions are signed out by the server), log out.
