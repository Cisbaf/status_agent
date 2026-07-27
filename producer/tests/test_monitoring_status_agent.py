from datetime import datetime
from unittest.mock import MagicMock

import pytest

from monitoring import MonitoringStatusAgent


@pytest.fixture
def mock_producer():
    return MagicMock()


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def monitoring(mock_api, mock_producer):
    return MonitoringStatusAgent(api=mock_api, producer=mock_producer, topic="status_agent")


def make_agent_data(agent_id="AGENTE1234567", status="online", date_status="00:00:05", last_date="00:01:00"):
    return {
        "id": agent_id,
        "status": status,
        "date_status": date_status,
        "last_date": last_date,
    }


def test_check_registry_registers_new_agent_and_sends_to_producer(monitoring, mock_producer):
    data = make_agent_data()
    dt = datetime(2026, 1, 15, 12, 0, 0)

    monitoring._check_registry_(data, dt)

    assert data["id"] in monitoring.lasts_api_data
    mock_producer.send.assert_called_once()
    _, kwargs = mock_producer.send.call_args
    assert kwargs["key"] == str(data["id"]).encode("utf-8")
    assert kwargs["topic"] == "status_agent"


def test_check_registry_does_not_duplicate_known_agent(monitoring, mock_producer):
    data = make_agent_data()
    dt = datetime(2026, 1, 15, 12, 0, 0)

    monitoring._check_registry_(data, dt)
    monitoring._check_registry_(data, dt)

    mock_producer.send.assert_called_once()


def test_check_updates_detects_status_change(monitoring, mock_producer):
    dt = datetime(2026, 1, 15, 12, 0, 0)
    original = make_agent_data(status="online")
    monitoring._check_registry_(original, dt)
    mock_producer.reset_mock()

    changed = make_agent_data(status="offline")
    changed_detected = monitoring._check_updates_(changed, dt)

    assert changed_detected is True
    mock_producer.send.assert_called_once()
    assert monitoring.lasts_api_data[changed["id"]]["status"] == "offline"


def test_check_updates_ignores_timestamp_only_fields(monitoring, mock_producer):
    dt = datetime(2026, 1, 15, 12, 0, 0)
    original = make_agent_data()
    monitoring._check_registry_(original, dt)
    mock_producer.reset_mock()

    # Só mudam campos de data, que devem ser ignorados na detecção de mudança
    same_data_new_timestamps = make_agent_data(date_status="00:00:10", last_date="00:01:10")
    changed_detected = monitoring._check_updates_(same_data_new_timestamps, dt)

    assert changed_detected is False
    mock_producer.send.assert_not_called()


def test_check_updates_returns_false_when_no_previous_data(monitoring, mock_producer):
    dt = datetime(2026, 1, 15, 12, 0, 0)
    data = make_agent_data()

    result = monitoring._check_updates_(data, dt)

    assert result is False
    mock_producer.send.assert_not_called()
