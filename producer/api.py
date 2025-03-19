import requests
import xmltodict
import json
from kafka import KafkaProducer
from datetime import datetime

class ApiRequest:

    def __init__(self, url: str, kafka_uri: str, topic_api: str, timeout: int):
        self.url = url
        self.topic = topic_api
        self.timeout = timeout
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_uri,
            api_version=(3, 8, 0),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),  # Serializar a mensagem para JSON
            key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k  # Serializar chave, se for string
        )

    def request(self):
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            time_response = response.elapsed.total_seconds()
            self.producer.send(
                self.topic,
                key=f'Response {int(time_response)}'.encode('utf-8'),
                value=time_response
            )
            return response
        except requests.exceptions.RequestException as err:
            message_error = f'Erro ao solicitar API | {err} | ({datetime.now().strftime("%d/%m/%Y, %H:%M:%S")})'
            if isinstance(err, requests.exceptions.Timeout):
                self.producer.send(
                    self.topic,
                    key='Timeout'.encode('utf-8'),
                    value=message_error
                )
            else:
                self.producer.send(
                    self.topic,
                    key='Error'.encode('utf-8'),
                    value=message_error
                )
            print(message_error)
            return None
    
    def get(self):
        # Realiza uma requisição
        response = self.request()

        # Retorna uma lista vazia em caso de erro
        if not response:
            return []
        
        # Converte o conteúdo XML da resposta em um dicionário Python
        dict_data = xmltodict.parse(response.text)

        # Acessa o nó "status_agente" dentro da estrutura JSON
        status_agente_json = dict_data.get("system", {}).get("status_agente", [])

        # Filtra e retorna os status_agente que possuem um 'id' com mais de 10 caracteres
        return [
            status_agente for status_agente in status_agente_json
            if len(status_agente['id']) > 10
        ]
    
  