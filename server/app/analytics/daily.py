"""
Pure analytics on daily weather: DataFrame in, DataFrame/dict out. No database, no HTTP.

Missing data is handled EXPLICITLY:
- daily_frame() puts every calendar day in the frame; a day without data is a row of NaN.
  (Dropping missing days would make "the last 30 days" quietly cover fewer days, and a
  7-row rolling window would then span more than 7 calendar days.)
- Averages skip NaN, but every summary reports how many days actually had data
  ("coverage"), and is flagged low_coverage when too many are missing.
- A rolling mean needs a minimum number of real values in its window, otherwise it is NaN.
All values are metric: °C, %, mm, m/s.
"""
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

METRICS = ["tmin", "tmax", "tmean", "humidity", "precip", "wind_max"]
RAINY_DAY_MM = 1.0              # a day with at least 1 mm of rain counts as rainy (WMO convention)
LOW_COVERAGE_BELOW = 0.8        # flag summaries where fewer than 80% of days have data


def daily_frame(records: list[dict[str, Any]], start: date, end: date) -> pd.DataFrame:
    """
    One row per calendar day from start to end (inclusive), indexed by date.
    records: dicts with "date" plus any of METRICS. Days that aren't in records become NaN rows.
    """
    index = pd.date_range(start, end, freq="D", name="date")
    if not records:
        return pd.DataFrame(np.nan, index=index, columns=METRICS)
    frame = pd.DataFrame.from_records(records)
    frame["date"] = pd.to_datetime(frame["date"])
    if frame["date"].duplicated().any():
        raise ValueError("daily_frame: the same date appears twice")
    frame = frame.set_index("date").reindex(columns=METRICS).astype(float)
    return frame.reindex(index)


def _require_daily_index(series: pd.Series) -> None:
    index = series.index
    if not isinstance(index, pd.DatetimeIndex) or (len(index) > 1 and (index.to_series().diff().dropna() != pd.Timedelta(days=1)).any()):
        raise ValueError("expected one row per calendar day (use daily_frame first)")


def rolling_mean(series: pd.Series, window: int = 7, min_periods: int = 5) -> pd.Series:
    """
    Trailing mean of the last `window` days (today included).
    NaN when fewer than `min_periods` of those days have data: we don't pretend a 7-day
    average exists when most of the week is missing.
    """
    _require_daily_index(series)
    return series.rolling(window, min_periods=min_periods).mean()


def _extreme(series: pd.Series, largest: bool) -> dict[str, Any] | None:
    values = series.dropna()
    if values.empty:
        return None
    when = values.idxmax() if largest else values.idxmin()     # first date wins on ties
    return {"date": when.date().isoformat(), "value": round(float(values[when]), 2)}


def _mean(series: pd.Series) -> float | None:
    values = series.dropna()
    return None if values.empty else round(float(values.mean()), 2)


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    """Headline numbers for a period, with explicit coverage."""
    days = len(frame)
    with_data = int(frame["tmean"].notna().sum())
    precip_known = frame["precip"].dropna()
    summary: dict[str, Any] = {
        "days": days,
        "days_with_data": with_data,
        "coverage": round(with_data / days, 3) if days else 0.0,
        "low_coverage": days == 0 or with_data / days < LOW_COVERAGE_BELOW,
        "missing_dates": [d.date().isoformat() for d in frame.index[frame["tmean"].isna()]],
        "tmean_avg": _mean(frame["tmean"]),
        "tmin_avg": _mean(frame["tmin"]),
        "tmax_avg": _mean(frame["tmax"]),
        "warmest": _extreme(frame["tmax"], largest=True),
        "coldest": _extreme(frame["tmin"], largest=False),
        "humidity_avg": _mean(frame["humidity"]),
        "precip_total": round(float(precip_known.sum()), 1) if not precip_known.empty else None,
        "precip_days_missing": int(frame["precip"].isna().sum()),
        "rainy_days": int((precip_known >= RAINY_DAY_MM).sum()),
        "windiest": _extreme(frame["wind_max"], largest=True),
    }
    if "anomaly" in frame:
        summary["anomaly_avg"] = _mean(frame["anomaly"])
        summary["warm_days"] = int((frame.get("category") == "warm").sum())
        summary["cool_days"] = int((frame.get("category") == "cool").sum())
    return summary


def _top(series: pd.Series, n: int, largest: bool, exclude_zero: bool = False) -> list[dict[str, Any]]:
    values = series.dropna()
    if exclude_zero:
        values = values[values > 0]
    # Stable order: by value, then by date (earliest first on ties)
    ordered = values.reset_index().sort_values([values.name or 0, "date"], ascending=[not largest, True], kind="mergesort")
    return [{"date": row["date"].date().isoformat(), "value": round(float(row[values.name or 0]), 2)}
            for _, row in ordered.head(n).iterrows()]


def extremes(frame: pd.DataFrame, n: int = 3) -> dict[str, list[dict[str, Any]]]:
    """The n most extreme days of each kind. Missing values never count as extremes."""
    result = {
        "hottest": _top(frame["tmax"], n, largest=True),
        "coldest": _top(frame["tmin"], n, largest=False),
        "wettest": _top(frame["precip"], n, largest=True, exclude_zero=True),
        "windiest": _top(frame["wind_max"], n, largest=True),
    }
    if "anomaly" in frame:
        result["warmest_vs_normal"] = _top(frame["anomaly"], n, largest=True)
        result["coolest_vs_normal"] = _top(frame["anomaly"], n, largest=False)
    return result


def to_records(frame: pd.DataFrame, decimals: int = 2) -> list[dict[str, Any]]:
    """Rows for JSON: {"date": "YYYY-MM-DD", ...}, with NaN as None (JSON null)."""
    rows = []
    for when, values in frame.iterrows():
        row: dict[str, Any] = {"date": when.date().isoformat()}
        for column, value in values.items():
            if isinstance(value, (float, np.floating)):
                row[column] = None if np.isnan(value) else round(float(value), decimals)
            else:
                row[column] = None if value is None or (isinstance(value, float) and np.isnan(value)) else value
        rows.append(row)
    return rows
