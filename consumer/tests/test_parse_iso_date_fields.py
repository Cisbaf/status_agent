from datetime import datetime

from main import parse_iso_date_fields


def test_converts_valid_iso_strings_to_datetime():
    data = {
        "id": "AGENTE1",
        "date_status_dt_iso": "2026-01-15T11:59:55",
        "last_date_dt_iso": "2026-01-15T12:00:00",
    }

    result = parse_iso_date_fields(data)

    assert isinstance(result["date_status_dt_iso"], datetime)
    assert result["date_status_dt_iso"] == datetime(2026, 1, 15, 11, 59, 55)
    assert isinstance(result["last_date_dt_iso"], datetime)


def test_ignores_missing_iso_fields():
    data = {"id": "AGENTE1", "status": "online"}

    result = parse_iso_date_fields(data)

    assert result == {"id": "AGENTE1", "status": "online"}


def test_ignores_unparseable_iso_string_without_raising():
    data = {"id": "AGENTE1", "date_status_dt_iso": "isso nao e uma data"}

    result = parse_iso_date_fields(data)

    # Mantém o valor original (string) quando não é possível fazer o parse,
    # em vez de descartar a mensagem inteira
    assert result["date_status_dt_iso"] == "isso nao e uma data"


def test_does_not_touch_non_date_fields():
    data = {"id": "AGENTE1", "status": "online", "date_status_dt_iso": "2026-01-15T11:59:55"}

    result = parse_iso_date_fields(data)

    assert result["id"] == "AGENTE1"
    assert result["status"] == "online"
