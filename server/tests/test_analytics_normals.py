"""Climate normals and comparison against them, on hand-made data with known answers."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.analytics.compare import compare_cities
from app.analytics.daily import daily_frame
from app.analytics.normals import attach_normals, compute_normals, noleap_day_of_year


def test_leap_day_is_treated_as_28_february():
    index = pd.to_datetime(["2020-02-28", "2020-02-29", "2020-03-01", "2021-03-01", "2020-12-31", "2021-12-31"])
    assert noleap_day_of_year(pd.DatetimeIndex(index)).tolist() == [59, 59, 60, 60, 365, 365]


def history(start: str, end: str, tmean) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="D", name="date")
    values = tmean(index) if callable(tmean) else np.full(len(index), tmean, dtype=float)
    frame = pd.DataFrame({"tmean": values}, index=index)
    for column in ["tmin", "tmax", "humidity", "precip", "wind_max"]:
        frame[column] = frame["tmean"] + {"tmin": -5, "tmax": 5, "humidity": 60, "precip": 0, "wind_max": 0}[column]
    return frame


def test_constant_climate_has_that_constant_as_normal():
    normals = compute_normals(history("1991-01-01", "1993-12-31", 10.0), min_values=10)
    assert len(normals) == 365 and list(normals.index[[0, -1]]) == [1, 365]
    assert normals["normal_tmean"].eq(10.0).all()
    assert normals["normal_tmin"].eq(5.0).all() and normals["normal_tmax"].eq(15.0).all()
    assert normals["normal_p10"].eq(10.0).all() and normals["normal_p90"].eq(10.0).all()


def test_normal_is_the_mean_of_a_15_day_window():
    # tmean = day of year. The normal for day 100 = mean of days 93..107 = 100
    normals = compute_normals(history("1991-01-01", "1993-12-31", lambda idx: noleap_day_of_year(idx).astype(float)),
                              min_values=10)
    assert normals.loc[100, "normal_tmean"] == pytest.approx(100.0)
    assert normals.loc[180, "normal_tmean"] == pytest.approx(180.0)


def test_window_wraps_around_new_year():
    # day 1: the window is 359..365 and 1..8. Mean = (sum(359..365) + sum(1..8)) / 15
    normals = compute_normals(history("1991-01-01", "1993-12-31", lambda idx: noleap_day_of_year(idx).astype(float)),
                              min_values=10)
    expected = (sum(range(359, 366)) + sum(range(1, 9))) / 15
    assert normals.loc[1, "normal_tmean"] == pytest.approx(expected)


def test_too_little_data_gives_no_normal_instead_of_a_wrong_one():
    frame = history("1991-01-01", "1991-12-31", 10.0)
    frame.loc["1991-06-01":"1991-06-30", "tmean"] = np.nan        # June missing
    normals = compute_normals(frame, min_values=5)
    assert np.isnan(normals.loc[167, "normal_tmean"])             # mid-June: no data in its window
    assert normals.loc[10, "normal_tmean"] == 10.0


def test_attach_normals_anomaly_and_category():
    normals = compute_normals(history("1991-01-01", "1993-12-31", lambda idx: np.where(idx.year == 1992, 12.0, 8.0)),
                              min_values=10)   # p10 = 8, p90 = 12, mean ~ 9.33
    period = daily_frame([{"date": date(2026, 1, 1), "tmean": 15.0}, {"date": date(2026, 1, 2), "tmean": 5.0},
                          {"date": date(2026, 1, 3), "tmean": 10.0}], date(2026, 1, 1), date(2026, 1, 4))
    result = attach_normals(period, normals)
    assert result["category"].tolist() == ["warm", "cool", "normal", None]   # day 4 has no data
    assert result["anomaly"].iloc[0] == pytest.approx(15.0 - normals.loc[1, "normal_tmean"])
    assert np.isnan(result["anomaly"].iloc[3])


def test_attach_normals_without_normals_for_a_day():
    normals = compute_normals(history("1991-01-01", "1991-12-31", 10.0), min_values=10_000)   # never enough data
    period = daily_frame([{"date": date(2026, 1, 1), "tmean": 12.0}], date(2026, 1, 1), date(2026, 1, 1))
    result = attach_normals(period, normals)
    assert np.isnan(result["anomaly"].iloc[0]) and result["category"].iloc[0] is None


def test_compare_aligns_cities_on_the_same_dates():
    a = daily_frame([{"date": date(2026, 1, d), "tmean": float(d)} for d in range(1, 4)], date(2026, 1, 1), date(2026, 1, 3))
    b = daily_frame([{"date": date(2026, 1, 2), "tmean": 20.0}], date(2026, 1, 1), date(2026, 1, 3))
    result = compare_cities({1: a, 2: b})
    assert result["dates"] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert result["cities"][1]["series"]["tmean"] == [1.0, 2.0, 3.0]
    assert result["cities"][2]["series"]["tmean"] == [None, 20.0, None]     # missing stays null, not shifted
    assert result["cities"][2]["summary"]["days_with_data"] == 1
