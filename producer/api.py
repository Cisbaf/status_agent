import requests
import xmltodict
import json
from kafka import KafkaProducer


class ApiRequest:

    def __init__(self, url: str, kafka_uri: str, topic_api: str):
        self.url = url
        self.topic = topic_api
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_uri,
            api_version=(3, 8, 0),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),  # Serializar a mensagem para JSON
            key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k  # Serializar chave, se for string
        )
    
    def request(self):
        try:
            # Realiza uma requisição GET na URL fornecida com timeout de 10 segundos
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()

            # Registra o tempo de resposta da API
            time_response = response.elapsed.total_seconds()
            self.producer.send(
                self.topic,
                key=str(time_response).encode('utf-8'),
                value=time_response
            )

            # Converte o conteúdo XML da resposta em um dicionário Python
            dict_data = xmltodict.parse(response.text)
            
            # Acessa o nó "status_agente" dentro da estrutura JSON
            status_agente_json = dict_data.get("system", {}).get("status_agente", [])
            
            # Filtra e retorna os status_agente que possuem um 'id' com mais de 10 caracteres
            return [
                status_agente for status_agente in status_agente_json
                if len(status_agente['id']) > 10
            ]
        except requests.exceptions.RequestException as e:
            # Exibe uma mensagem de erro caso a requisição falhe
            print(f"Erro na requisição HTTP: {e}")
            return []  # Retorna uma lista vazia em caso de erro
