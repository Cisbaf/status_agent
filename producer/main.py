import time

from monitoring import MonitoringStatusAgent
from api import ApiRequest
from control_producer import CachedRabbitMQProducer
import os

# Obter Variaveis de Ambiente
queue_status_agent = os.getenv("QUEUE_STATUS_AGENT")
queue_api = os.getenv("QUEUE_API")
api_uri = os.getenv("API_URI")
rabbitmq_uri = os.getenv("RABBITMQ_URI")
timeout_api_conn = os.getenv("TIMEOUT_API_CONN")
timeout_api_read = os.getenv("TIMEOUT_API_READ")


def create_producer_with_retry(rabbitmq_uri: str, max_retries: int = 10, delay_seconds: int = 3):
    """Tenta conectar ao RabbitMQ com retentativas, para tolerar o broker
    ainda estar subindo quando este container inicia."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return CachedRabbitMQProducer(rabbitmq_uri=rabbitmq_uri)
        except Exception as e:
            last_error = e
            print(f"Tentativa {attempt}/{max_retries} de conectar ao RabbitMQ falhou: {e}")
            time.sleep(delay_seconds)
    raise Exception(f"Não foi possível conectar ao RabbitMQ após {max_retries} tentativas: {last_error}")


# Inicializar Algoritimo
if __name__ == '__main__':
    if (not queue_status_agent
        or not api_uri
        or not rabbitmq_uri
        or not queue_api
        ):
        raise Exception("Erro ao obter variaveis de ambiente")

    producer = create_producer_with_retry(rabbitmq_uri=rabbitmq_uri)

    # Inicializa Classe de Request API
    api = ApiRequest(
        url=api_uri,
        timeout_conn=int(timeout_api_conn),
        timeout_read=int(timeout_api_read),
        topic_api=queue_api,
        producer=producer
    )
    # Inicializa Classe de Monitoramento
    monitoring = MonitoringStatusAgent(
        api=api,
        producer=producer,
        topic=queue_status_agent
    )
    # Starta o Looping de Monitoramento
    monitoring.run()
