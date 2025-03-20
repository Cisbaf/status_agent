from datetime import datetime, timezone
from kafka import KafkaProducer
import pytz
import json

def convert_time(dt: datetime):
    return dt.astimezone(timezone.utc).astimezone(pytz.timezone('America/Sao_Paulo'))
    
def make_producer(kafka_uri: str, api_version=(3, 8, 0)):
    return KafkaProducer(
        bootstrap_servers=kafka_uri,
        api_version=api_version,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),  # Serializar a mensagem para JSON
        key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k  # Serializar chave, se for string
    )