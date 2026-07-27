from datetime import datetime
import pytz

from utils import convert_time


def test_convert_time_returns_datetime_in_sao_paulo_timezone():
    naive_dt = datetime(2026, 1, 15, 12, 0, 0)

    result = convert_time(naive_dt)

    assert result.tzinfo is not None
    assert result.tzinfo.zone == "America/Sao_Paulo"


def test_convert_time_applies_correct_utc_offset():
    # 12:00 UTC -> horário de São Paulo (UTC-3, sem horário de verão vigente)
    from datetime import timezone
    utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    result = convert_time(utc_dt)

    assert result.hour == 9
    assert result.utcoffset().total_seconds() == -3 * 3600
