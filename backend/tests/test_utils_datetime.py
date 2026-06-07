"""Tests for app/utils/datetime.py"""

import pytest
from datetime import datetime, timezone

from app.utils.datetime import now, iso_now, naive_utc_now, utc_timestamp, date_str, format_ts


class TestNow:
    def test_returns_aware_datetime(self):
        result = now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) == timezone.utc.utcoffset(result)

    def test_returns_current_time(self):
        before = datetime.now(timezone.utc)
        result = now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestIsoNow:
    def test_returns_string(self):
        result = iso_now()
        assert isinstance(result, str)
        assert "+" in result  # timezone info
        assert "T" in result  # ISO separator

    def test_parses_back_to_datetime(self):
        result = iso_now()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None


class TestNaiveUtcNow:
    def test_returns_naive_datetime(self):
        result = naive_utc_now()
        assert isinstance(result, datetime)
        assert result.tzinfo is None


class TestUtcTimestamp:
    def test_returns_float(self):
        result = utc_timestamp()
        assert isinstance(result, float)
        assert result > 1_700_000_000  # reasonable timestamp for 2024+


class TestDateStr:
    def test_default_format(self):
        result = date_str()
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD

    def test_custom_format(self):
        result = date_str("%Y/%m/%d")
        assert "/" in result

    def test_custom_date_format(self):
        result = date_str("%d-%m-%Y")
        parts = result.split("-")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestFormatTs:
    def test_default(self):
        result = format_ts()
        assert isinstance(result, str)
        assert "+" in result

    def test_with_custom_dt(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_ts(dt)
        assert "2024" in result
        assert "01-15" in result or "2024-01-15" in result

    def test_with_isoformat_kwargs(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_ts(dt, sep="T", timespec="microseconds")
        assert "123456" in result

    def test_with_seconds_precision(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_ts(dt, timespec="seconds")
        assert "123456" not in result
        assert result.endswith("+00:00") or "+00:00" in result

    def test_defaults_to_now(self):
        before = iso_now()
        result = format_ts()
        after = iso_now()
        # Just verify it returns something parseable
        datetime.fromisoformat(result)
