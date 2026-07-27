import json
import threading
import time
from collections import deque

import pika
from pika.exceptions import AMQPError


class CachedRabbitMQProducer:
    """
    Produtor de mensagens para RabbitMQ que mantém uma fila interna em memória
    e envia as mensagens em ordem, com retentativas em caso de falha.

    Mantém a mesma interface pública do antigo CachedKafkaProducer
    (send(topic, value, key=None)) para minimizar mudanças no restante do código.
    Aqui, "topic" é usado como o nome da fila (queue) do RabbitMQ.
    """

    def __init__(self, rabbitmq_uri: str):
        self.rabbitmq_uri = rabbitmq_uri
        self._connection = None
        self._channel = None
        self._declared_queues = set()

        self.queue = deque()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.running = True

        self._connect()
        self.thread.start()

    def _connect(self):
        """Abre (ou reabre) a conexão e o canal com o RabbitMQ."""
        params = pika.URLParameters(self.rabbitmq_uri)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._declared_queues = set()

    def _ensure_queue(self, queue_name: str):
        if queue_name not in self._declared_queues:
            self._channel.queue_declare(queue=queue_name, durable=True)
            self._declared_queues.add(queue_name)

    def send(self, topic, value, key=None):
        """Adiciona a mensagem à fila interna para envio ordenado."""
        with self.lock:
            self.queue.append((topic, value, key))

    def _serialize(self, value):
        if isinstance(value, (bytes, bytearray)):
            return value
        if isinstance(value, str):
            return value.encode("utf-8")
        return json.dumps(value).encode("utf-8")

    def _process_queue(self):
        """Processa a fila em ordem, tentando publicar cada mensagem."""
        while self.running:
            if not self.queue:
                time.sleep(0.1)
                continue

            with self.lock:
                if not self.queue:
                    continue
                topic, value, key = self.queue[0]

            try:
                if key is not None and isinstance(key, (bytes, bytearray)):
                    key_str = key.decode("utf-8")
                else:
                    key_str = key

                self._ensure_queue(topic)

                body = self._serialize(value)

                self._channel.basic_publish(
                    exchange="",
                    routing_key=topic,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # mensagem persistente
                        headers={"key": key_str} if key_str is not None else None,
                    ),
                )

                with self.lock:
                    self.queue.popleft()
            except AMQPError as e:
                print(f"Erro ao enviar ({topic}-{key}): {e}. Reconectando e retentando...")
                self._safe_reconnect()
                time.sleep(1)
            except Exception as e:
                print(f"Erro inesperado: {e}")
                time.sleep(1)

    def _safe_reconnect(self):
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        try:
            self._connect()
        except Exception as e:
            print(f"Falha ao reconectar ao RabbitMQ: {e}")

    def close(self):
        """Encerra o produtor e a thread de background."""
        self.running = False
        self.thread.join()
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
