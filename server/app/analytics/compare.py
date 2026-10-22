"""Side-by-side comparison of 2-3 cities over the same days. Pure function."""
from typing import Any

import pandas as pd

from app.analytics.daily import rolling_mean, summarize, to_records

COMPARED = ["tmean", "tmean_7d", "tmin", "tmax", "precip", "humidity", "wind_max", "anomaly"]


def compare_cities(frames: dict[int, pd.DataFrame]) -> dict[str, Any]:
    """
    frames: city id -> daily frame (from daily_frame, optionally with normals attached).
    If a frame already has "tmean_7d" (period_frame computes it with 6 warm-up days before the
    period), it is kept: recomputing it here would leave the first days of the chart empty.
    All cities are put on the same dates (the union), so a day one city is missing stays an
    explicit null for that city instead of shifting its line.
    Returns {"dates": [...], "cities": {id: {"series": {metric: [...]}, "summary": {...}}}}.
    """
    if not frames:
        return {"dates": [], "cities": {}}
    index = frames[next(iter(frames))].index
    for frame in frames.values():
        index = index.union(frame.index)
    dates = [d.date().isoformat() for d in index]

    cities: dict[int, Any] = {}
    for city_id, frame in frames.items():
        aligned = frame.reindex(index)
        if "tmean_7d" not in aligned:
            aligned = aligned.assign(tmean_7d=rolling_mean(aligned["tmean"]))
        columns = [c for c in COMPARED if c in aligned]
        rows = to_records(aligned[columns])
        cities[city_id] = {
            "series": {column: [row[column] for row in rows] for column in columns},
            # The city's own period: cities in other time zones can end a day apart, and the
            # other city's extra date isn't a missing day for this one
            "summary": summarize(frame),
        }
    return {"dates": dates, "cities": cities}
