from monitoring import MonitoringStatusAgent
from api import ApiRequest
from control_producer import CachedKafkaProducer
import os

# Obter Variaveis de Ambiente
topic_status_agent = os.getenv("TOPIC_STATUS_AGENT")
topic_api = os.getenv("TOPIC_API")
api_uri = os.getenv("API_URI")
kafka_uri = os.getenv("KAFKA_URI")
timeout_api_conn = os.getenv("TIMEOUT_API_CONN")
timeout_api_read = os.getenv("TIMEOUT_API_READ")

# Inicializar Algoritimo
if __name__ == '__main__':
    if (not topic_status_agent
        or not api_uri
        or not kafka_uri
        or not topic_api
        ):
        raise Exception("Erro ao obter variaveis de ambiente")
    
    producer = CachedKafkaProducer(kafka_uri=kafka_uri)
    
    # Inicializa Classe de Request API
    api = ApiRequest(
        url=api_uri,
        timeout_conn=int(timeout_api_conn),
        timeout_read=int(timeout_api_read),
        topic_api=topic_api,
        producer=producer
    )
    # Inicializa Classe de Monitoramento
    monitoring = MonitoringStatusAgent(
        api=api,
        producer=producer,
        topic=topic_status_agent
    )
    # Starta o Looping de Monitoramento
    monitoring.run()
