"""
Climate normals (1991-2020) and comparing a period against them. Pure functions.

A "normal" for a day of the year is the average over 30 years of all days within ±7 days of
it (a 15-day window). The window smooths out the day-to-day noise of only 30 samples, and
wraps around the year end (the normal for 2 January also uses late-December days).

Leap years: 29 February is treated as 28 February, so every year has days 1-365 and
1 March is always day 60.
"""
import numpy as np
import pandas as pd

HALF_WINDOW = 7            # ±7 days -> a 15-day window
DAYS = 365
MIN_VALUES = 100           # fewer real values in a window than this -> no normal for that day (NaN)

NORMAL_COLUMNS = ["normal_tmean", "normal_tmin", "normal_tmax", "normal_p10", "normal_p90",
                  "normal_precip", "normal_humidity", "normal_wind_max"]


def noleap_day_of_year(index: pd.DatetimeIndex) -> np.ndarray:
    """Day of year 1-365; 29 Feb counts as 28 Feb (59), and later days in leap years shift back by one."""
    day = index.dayofyear.to_numpy().copy()
    leap_after_feb = index.is_leap_year & (day >= 60)
    day[leap_after_feb] -= 1
    return day


def _circular_distance(days: np.ndarray, target: int) -> np.ndarray:
    gap = np.abs(days - target)
    return np.minimum(gap, DAYS - gap)


def _stat(values: np.ndarray, how: str, min_values: int) -> float:
    values = values[~np.isnan(values)]
    if len(values) < min_values:
        return np.nan
    if how == "mean":
        return float(values.mean())
    return float(np.percentile(values, {"p10": 10, "p90": 90}[how]))


def compute_normals(history: pd.DataFrame, half_window: int = HALF_WINDOW, min_values: int = MIN_VALUES) -> pd.DataFrame:
    """
    history: daily frame (index = dates, columns tmin/tmax/tmean/humidity/precip/wind_max), e.g. 1991-2020.
    Returns one row per day of year 1-365 with the NORMAL_COLUMNS.
    normal_p10/p90: the 10th/90th percentile of the daily mean temperature, i.e. the "normal range":
    8 in 10 days at this time of year fall inside it.
    """
    days = noleap_day_of_year(history.index)
    columns = {name: history[name].to_numpy(dtype=float) for name in ["tmean", "tmin", "tmax", "precip", "humidity", "wind_max"]}
    rows = []
    for target in range(1, DAYS + 1):
        near = _circular_distance(days, target) <= half_window
        rows.append({
            "day_of_year": target,
            "normal_tmean": _stat(columns["tmean"][near], "mean", min_values),
            "normal_tmin": _stat(columns["tmin"][near], "mean", min_values),
            "normal_tmax": _stat(columns["tmax"][near], "mean", min_values),
            "normal_p10": _stat(columns["tmean"][near], "p10", min_values),
            "normal_p90": _stat(columns["tmean"][near], "p90", min_values),
            "normal_precip": _stat(columns["precip"][near], "mean", min_values),
            "normal_humidity": _stat(columns["humidity"][near], "mean", min_values),
            "normal_wind_max": _stat(columns["wind_max"][near], "mean", min_values),
        })
    return pd.DataFrame(rows).set_index("day_of_year")


def attach_normals(frame: pd.DataFrame, normals: pd.DataFrame) -> pd.DataFrame:
    """
    Add the normal for each day, plus:
      anomaly  = tmean - normal_tmean (NaN if either is missing)
      category = "warm" above the normal range (p90), "cool" below it (p10), "normal" inside,
                 None if we can't tell (missing data)
    """
    result = frame.copy()
    days = noleap_day_of_year(frame.index)
    aligned = normals.reindex(days)
    for column in NORMAL_COLUMNS:
        result[column] = aligned[column].to_numpy() if column in aligned else np.nan
    result["anomaly"] = result["tmean"] - result["normal_tmean"]
    known = result["tmean"].notna() & result["normal_p10"].notna() & result["normal_p90"].notna()
    category = np.where(result["tmean"] > result["normal_p90"], "warm",
                        np.where(result["tmean"] < result["normal_p10"], "cool", "normal"))
    result["category"] = pd.Series(np.where(known, category, None), index=result.index, dtype=object)
    return result
