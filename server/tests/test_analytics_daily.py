"""Pure analytics on small hand-made data, where the right answer is known."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.analytics.daily import daily_frame, extremes, rolling_mean, summarize, to_records


def day(d: int, **values):
    return {"date": date(2026, 1, d), **values}


def frame_with(values: list[float | None], column: str = "tmean", start: int = 1) -> pd.DataFrame:
    records = [day(start + i, **{column: v}) for i, v in enumerate(values) if v is not None]
    return daily_frame(records, date(2026, 1, start), date(2026, 1, start + len(values) - 1))


# --- daily_frame: one row per calendar day ---------------------------------------------------

def test_missing_days_become_explicit_nan_rows():
    frame = daily_frame([day(1, tmean=5.0), day(4, tmean=8.0)], date(2026, 1, 1), date(2026, 1, 5))
    assert list(frame.index.day) == [1, 2, 3, 4, 5]                     # every calendar day is there
    assert frame["tmean"].tolist()[0] == 5.0 and frame["tmean"].tolist()[3] == 8.0
    assert frame["tmean"].isna().tolist() == [False, True, True, False, True]
    assert list(frame.columns) == ["tmin", "tmax", "tmean", "humidity", "precip", "wind_max"]


def test_no_records_gives_an_all_nan_frame():
    frame = daily_frame([], date(2026, 1, 1), date(2026, 1, 3))
    assert len(frame) == 3 and frame.isna().all().all()


def test_duplicate_dates_are_an_error():
    with pytest.raises(ValueError, match="twice"):
        daily_frame([day(1, tmean=1.0), day(1, tmean=2.0)], date(2026, 1, 1), date(2026, 1, 2))


# --- rolling mean ---------------------------------------------------------------------

def test_seven_day_rolling_mean_of_known_values():
    # 1..10: the 7-day trailing mean on day 7 is mean(1..7) = 4, on day 10 it is mean(4..10) = 7
    frame = frame_with([float(v) for v in range(1, 11)])
    rolled = rolling_mean(frame["tmean"], window=7, min_periods=7)
    assert rolled.isna().tolist()[:6] == [True] * 6                       # not enough days yet
    assert rolled.tolist()[6:] == [4.0, 5.0, 6.0, 7.0]


def test_rolling_mean_needs_enough_real_values():
    # window 7, needs 5 real values. Days 2-4 missing: the window ending on day 7 has only 4.
    frame = frame_with([1.0, None, None, None, 5.0, 6.0, 7.0, 8.0, 9.0])
    rolled = rolling_mean(frame["tmean"], window=7, min_periods=5)
    assert np.isnan(rolled.iloc[6])                                      # days 1-7: 4 real values, no average
    assert np.isnan(rolled.iloc[7])                                      # days 2-8: still only 4
    assert rolled.iloc[8] == pytest.approx((5 + 6 + 7 + 8 + 9) / 5)      # days 3-9: 5 real values -> 7.0


def test_missing_days_are_not_averaged_as_zero():
    frame = frame_with([10.0, None, 10.0, 10.0, 10.0, 10.0, 10.0])
    assert rolling_mean(frame["tmean"], window=7, min_periods=5).iloc[-1] == 10.0


def test_rolling_mean_refuses_a_frame_with_gaps_in_the_index():
    gappy = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-01-01", "2026-01-03"]))
    with pytest.raises(ValueError, match="one row per calendar day"):
        rolling_mean(gappy)


# --- summary --------------------------------------------------------------------------

def full_records():
    return [
        day(1, tmin=1, tmax=9, tmean=5, humidity=80, precip=0.0, wind_max=4),
        day(2, tmin=3, tmax=11, tmean=7, humidity=70, precip=2.5, wind_max=9),
        day(3, tmin=-2, tmax=6, tmean=2, humidity=90, precip=0.4, wind_max=3),
        day(4, tmin=0, tmax=12, tmean=6, humidity=60, precip=12.0, wind_max=9),
    ]


def test_summary_of_a_complete_period():
    summary = summarize(daily_frame(full_records(), date(2026, 1, 1), date(2026, 1, 4)))
    assert summary["days"] == 4 and summary["days_with_data"] == 4 and summary["coverage"] == 1.0
    assert summary["low_coverage"] is False and summary["missing_dates"] == []
    assert summary["tmean_avg"] == 5.0                                   # (5+7+2+6)/4
    assert summary["warmest"] == {"date": "2026-01-04", "value": 12.0}
    assert summary["coldest"] == {"date": "2026-01-03", "value": -2.0}
    assert summary["precip_total"] == 14.9 and summary["rainy_days"] == 2   # >= 1 mm: 2.5 and 12.0
    assert summary["windiest"] == {"date": "2026-01-02", "value": 9.0}      # tie: earliest date wins


def test_summary_reports_missing_days_instead_of_hiding_them():
    records = full_records()[:2]                                         # days 3-5 missing
    summary = summarize(daily_frame(records, date(2026, 1, 1), date(2026, 1, 5)))
    assert summary["days"] == 5 and summary["days_with_data"] == 2 and summary["coverage"] == 0.4
    assert summary["low_coverage"] is True
    assert summary["missing_dates"] == ["2026-01-03", "2026-01-04", "2026-01-05"]
    assert summary["tmean_avg"] == 6.0                                   # mean of the real days only
    assert summary["precip_days_missing"] == 3


def test_summary_of_an_empty_period():
    summary = summarize(daily_frame([], date(2026, 1, 1), date(2026, 1, 3)))
    assert summary["tmean_avg"] is None and summary["warmest"] is None and summary["precip_total"] is None
    assert summary["low_coverage"] is True


# --- extremes -------------------------------------------------------------------------

def test_extremes_are_ordered_and_skip_missing_and_dry_days():
    frame = daily_frame(full_records(), date(2026, 1, 1), date(2026, 1, 6))   # days 5-6 missing
    result = extremes(frame, n=2)
    assert result["hottest"] == [{"date": "2026-01-04", "value": 12.0}, {"date": "2026-01-02", "value": 11.0}]
    assert result["coldest"][0] == {"date": "2026-01-03", "value": -2.0}
    assert [r["value"] for r in result["wettest"]] == [12.0, 2.5]
    assert result["windiest"] == [{"date": "2026-01-02", "value": 9.0}, {"date": "2026-01-04", "value": 9.0}]


def test_no_rain_means_no_wettest_days():
    frame = daily_frame([day(1, precip=0.0), day(2, precip=0.0)], date(2026, 1, 1), date(2026, 1, 2))
    assert extremes(frame)["wettest"] == []


# --- JSON records ----------------------------------------------------------------------

def test_records_turn_nan_into_null():
    frame = daily_frame([day(1, tmean=1.234)], date(2026, 1, 1), date(2026, 1, 2))
    rows = to_records(frame[["tmean"]])
    assert rows == [{"date": "2026-01-01", "tmean": 1.23}, {"date": "2026-01-02", "tmean": None}]
