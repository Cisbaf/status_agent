import json
import os
import time

import pika
import pymongo
from pika.exceptions import AMQPError

from monitoring import MonitoringController

# Obter Variaveis de Ambiente
queue = os.getenv("QUEUE_STATUS_AGENT")
rabbitmq_uri = os.getenv("RABBITMQ_URI")
mongo_uri = os.getenv("MONGO_URI")
db_client = os.getenv("DB_CLIENT")


def make_on_message(monitoring: MonitoringController):
    def on_message(channel, method, properties, body):
        try:
            data = json.loads(body.decode("utf-8"))
            monitoring.check(data)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            # Não descarta a mensagem; devolve para a fila para nova tentativa
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    return on_message


def run():
    client = pymongo.MongoClient(mongo_uri)
    db = client[db_client]
    monitoring = MonitoringController(database=db)

    while True:
        try:
            params = pika.URLParameters(rabbitmq_uri)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=queue, on_message_callback=make_on_message(monitoring))

            print("Consumer conectado ao RabbitMQ. Aguardando mensagens...")
            channel.start_consuming()
        except AMQPError as e:
            print(f"Conexão com RabbitMQ perdida ou falhou: {e}. Tentando reconectar em 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            try:
                channel.stop_consuming()
                connection.close()
            except Exception:
                pass
            break


# Inicializar Algoritimo
if __name__ == '__main__':
    if not queue or not rabbitmq_uri or not mongo_uri or not db_client:
        raise Exception("Erro ao obter variaveis de ambiente")

    run()
