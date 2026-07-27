import json
from unittest.mock import MagicMock

import pytest

from main import make_on_message


@pytest.fixture
def mock_monitoring():
    return MagicMock()


@pytest.fixture
def mock_channel():
    return MagicMock()


@pytest.fixture
def mock_method():
    method = MagicMock()
    method.delivery_tag = 42
    return method


def test_on_message_processes_valid_json_and_acks(mock_monitoring, mock_channel, mock_method):
    on_message = make_on_message(mock_monitoring)
    body = json.dumps({"id": "AGENTE1234567", "status": "online"}).encode("utf-8")

    on_message(mock_channel, mock_method, None, body)

    mock_monitoring.check.assert_called_once_with({"id": "AGENTE1234567", "status": "online"})
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=42)
    mock_channel.basic_nack.assert_not_called()


def test_on_message_nacks_and_requeues_on_invalid_json(mock_monitoring, mock_channel, mock_method):
    on_message = make_on_message(mock_monitoring)
    body = b"isso nao e um json valido"

    on_message(mock_channel, mock_method, None, body)

    mock_monitoring.check.assert_not_called()
    mock_channel.basic_ack.assert_not_called()
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=42, requeue=True)


def test_on_message_nacks_and_requeues_when_monitoring_raises(mock_monitoring, mock_channel, mock_method):
    mock_monitoring.check.side_effect = RuntimeError("erro ao gravar no mongo")
    on_message = make_on_message(mock_monitoring)
    body = json.dumps({"id": "AGENTE1234567", "status": "online"}).encode("utf-8")

    on_message(mock_channel, mock_method, None, body)

    mock_channel.basic_ack.assert_not_called()
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=42, requeue=True)
