import requests
import xmltodict
from control_producer import CachedRabbitMQProducer
from datetime import datetime
from utils import convert_time


class ApiRequest:

    def __init__(self, url: str, topic_api: str, producer: CachedRabbitMQProducer, timeout_conn=1, timeout_read=1):
        self.url = url
        self.topic = topic_api
        self.timeout_conn = timeout_conn
        self.timeout_read = timeout_read
        self.producer = producer

    def _get_data_(self):
        try:
            response = requests.get(self.url, timeout=(self.timeout_conn, self.timeout_read))
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

        # Normaliza os ids e filtra os status_agente que possuem um 'id' com 10 ou mais caracteres
        result = []
        for status_agente in status_agente_json:
            status_agente['id'] = self._normalize_id_(status_agente['id'])
            if len(status_agente['id']) >= 10:
                result.append(status_agente)
        return result

    @staticmethod
    def _normalize_id_(agent_id: str):
        # A API remove os zeros à esquerda dos ids numéricos (ex.: 00413539784 -> 413539784).
        # Só ids de 9 dígitos são completados, para não mudar a collection dos ids de 10+ já gravados.
        if agent_id.isdigit() and len(agent_id) == 9:
            return agent_id.zfill(11)
        return agent_id
    
  