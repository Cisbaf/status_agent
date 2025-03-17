from kafka import KafkaConsumer
import os, json, pymongo
from monitoring import MonitoringController

# Obter Variaveis de Ambiente
topic = os.getenv("TOPIC_STATUS_AGENT")
kafka_uri = os.getenv("KAFKA_URI")
group_id = os.getenv("GROUP_ID")
mongo_uri = os.getenv("MONGO_URI")
db_client = os.getenv("DB_CLIENT")

# Inicializar Algoritimo
if __name__ == '__main__':
    if not topic or not group_id or not kafka_uri or not mongo_uri or not db_client:
        raise Exception("Erro ao obter variaveis de ambiente")

    # Inicializar Kafka Producer
    consumer = KafkaConsumer(
        topic,  # The Kafka topic to consume from
        api_version=(3, 8, 0),
        bootstrap_servers=kafka_uri,  # Change this if your Kafka broker is running elsewhere
        auto_offset_reset='earliest',  # Start reading at the beginning of the topic if no offset is found
        enable_auto_commit=True,
        group_id=group_id,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    client = pymongo.MongoClient(mongo_uri)
    db = client[db_client]

    monitoring = MonitoringController(database=db)

    for message in consumer:
        monitoring.check(message.value)