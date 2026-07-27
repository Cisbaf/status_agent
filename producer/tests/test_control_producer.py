import json
import time
from unittest.mock import MagicMock, patch

import pytest
from pika.exceptions import AMQPError

from control_producer import CachedRabbitMQProducer


@pytest.fixture
def mock_pika(monkeypatch):
    """
    Mocka pika.URLParameters e pika.BlockingConnection para que os testes
    não dependam de um RabbitMQ real.
    """
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.is_open = True
    mock_connection.channel.return_value = mock_channel

    with patch("control_producer.pika.BlockingConnection", return_value=mock_connection) as mock_conn_cls, \
         patch("control_producer.pika.URLParameters") as mock_params_cls:
        yield {
            "connection_cls": mock_conn_cls,
            "connection": mock_connection,
            "channel": mock_channel,
            "params_cls": mock_params_cls,
        }


def wait_until_queue_empty(producer, timeout=2.0):
    """Espera a fila interna do producer esvaziar (mensagem processada pela thread)."""
    start = time.time()
    while producer.queue and time.time() - start < timeout:
        time.sleep(0.02)


def test_init_connects_and_starts_background_thread(mock_pika):
    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")

    mock_pika["connection_cls"].assert_called_once()
    assert producer.thread.is_alive()

    producer.close()


def test_send_enqueues_message_without_blocking(mock_pika):
    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")

    producer.send(topic="my_queue", value={"foo": "bar"}, key="123")

    wait_until_queue_empty(producer)
    producer.close()

    mock_pika["channel"].queue_declare.assert_called_with(queue="my_queue", durable=True)
    mock_pika["channel"].basic_publish.assert_called_once()
    _, kwargs = mock_pika["channel"].basic_publish.call_args
    assert kwargs["routing_key"] == "my_queue"
    assert json.loads(kwargs["body"].decode("utf-8")) == {"foo": "bar"}


def test_send_declares_queue_only_once_per_topic(mock_pika):
    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")

    producer.send(topic="my_queue", value={"a": 1})
    wait_until_queue_empty(producer)
    producer.send(topic="my_queue", value={"a": 2})
    wait_until_queue_empty(producer)

    producer.close()

    assert mock_pika["channel"].queue_declare.call_count == 1
    assert mock_pika["channel"].basic_publish.call_count == 2


def test_send_serializes_string_values_as_utf8(mock_pika):
    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")

    producer.send(topic="errors", value="mensagem de erro", key="TimeOut")
    wait_until_queue_empty(producer)
    producer.close()

    _, kwargs = mock_pika["channel"].basic_publish.call_args
    assert kwargs["body"] == "mensagem de erro".encode("utf-8")


def test_send_retries_and_reconnects_on_amqp_error(mock_pika):
    mock_pika["channel"].basic_publish.side_effect = [AMQPError("falha simulada"), None]

    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")
    producer.send(topic="my_queue", value={"a": 1})

    # Dá tempo para a primeira tentativa falhar, reconectar (sleep 1s) e tentar de novo
    time.sleep(1.5)
    wait_until_queue_empty(producer, timeout=2.0)
    producer.close()

    assert mock_pika["channel"].basic_publish.call_count == 2
    # reconectou: BlockingConnection foi chamado mais de uma vez (init + reconexão)
    assert mock_pika["connection_cls"].call_count >= 2


def test_close_stops_thread_and_closes_connection(mock_pika):
    producer = CachedRabbitMQProducer(rabbitmq_uri="amqp://user:pass@localhost/")

    producer.close()

    assert producer.running is False
    assert not producer.thread.is_alive()
    mock_pika["connection"].close.assert_called()
