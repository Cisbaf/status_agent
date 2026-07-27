from unittest.mock import MagicMock, patch

import pytest
import requests

from api import ApiRequest


XML_RESPONSE_VALID = """<?xml version="1.0"?>
<system>
    <status_agente>
        <id>AGENTE1234567</id>
        <status>online</status>
        <date_status>00:00:05</date_status>
        <last_date>00:01:00</last_date>
    </status_agente>
    <status_agente>
        <id>curto</id>
        <status>online</status>
        <date_status>00:00:00</date_status>
        <last_date>00:00:00</last_date>
    </status_agente>
</system>
"""


@pytest.fixture
def mock_producer():
    return MagicMock()


@pytest.fixture
def api_request(mock_producer):
    return ApiRequest(
        url="http://fake-api/test",
        topic_api="api_status_agent",
        producer=mock_producer,
        timeout_conn=1,
        timeout_read=1,
    )


def test_get_filters_ids_with_less_than_10_chars(api_request):
    mock_response = MagicMock()
    mock_response.text = XML_RESPONSE_VALID
    mock_response.raise_for_status.return_value = None

    with patch("api.requests.get", return_value=mock_response):
        result = api_request.get()

    assert len(result) == 1
    assert result[0]["id"] == "AGENTE1234567"


def test_get_returns_empty_list_on_request_exception(api_request, mock_producer):
    with patch("api.requests.get", side_effect=requests.exceptions.ConnectionError("boom")):
        result = api_request.get()

    assert result == []


def test_get_sends_error_message_to_producer_on_timeout(api_request, mock_producer):
    with patch("api.requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        api_request.get()

    mock_producer.send.assert_called_once()
    _, kwargs = mock_producer.send.call_args
    assert kwargs["key"] == b"TimeOut"


def test_get_sends_other_error_key_for_non_timeout_errors(api_request, mock_producer):
    with patch("api.requests.get", side_effect=requests.exceptions.ConnectionError("boom")):
        api_request.get()

    mock_producer.send.assert_called_once()
    _, kwargs = mock_producer.send.call_args
    assert kwargs["key"] == b"OtherError"


def test_get_raises_for_status_error_is_handled(api_request, mock_producer):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")

    with patch("api.requests.get", return_value=mock_response):
        result = api_request.get()

    assert result == []
    mock_producer.send.assert_called_once()
