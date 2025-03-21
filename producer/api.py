import requests
import xmltodict
from control_producer import CachedKafkaProducer
from datetime import datetime
from utils import convert_time


class ApiRequest:

    def __init__(self, url: str, timeout: int, topic_api: str, producer: CachedKafkaProducer):
        self.url = url
        self.topic = topic_api
        self.timeout = timeout
        self.producer = producer

    def _get_data_(self):
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as err:
            dt = convert_time(datetime.now()).strftime("%d/%m/%Y, %H:%M:%S")
            message_error = f'{err} | ({dt})'

            if isinstance(err, requests.exceptions.Timeout):
                key = 'TimeOut'
            else:
                key = 'OtherError'

            self.producer.send(
                self.topic,
                key=key.encode('utf-8'),
                value=message_error
            )
            print(message_error)
            return None
    
    def get(self):
        # Realiza uma requisição
        response = self._get_data_()

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
    
  