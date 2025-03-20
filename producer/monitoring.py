from kafka import KafkaProducer
from api import ApiRequest
from datetime import datetime, timedelta
import time
from utils import convert_time

class MonitoringStatusAgent:

    def __init__(self, api: ApiRequest, producer: KafkaProducer, topic: str):
        self.api = api
        self.producer =producer
        self.topic = topic
        self.lasts_api_data = {}

    def _convert_time_to_datetime_(self, time_str: str, dt: datetime):
        # Converte a string de tempo no formato HH:MM:SS para um datetime, subtraindo do datetime base
        if time_str != '00:00:00' and not '.' in time_str:
            hours, minutes, seconds = map(int, time_str.split(':'))
            dt -= timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return dt

    def _register_updates_(self, data: dict, dt: datetime):
        # Converte as datas de status e última data para datetime
        date_status_dt = self._convert_time_to_datetime_(data['date_status'], dt)
        last_date_dt = self._convert_time_to_datetime_(data['last_date'], dt)

        # Atualiza os campos com os valores formatados
        data['date_status_dt'] = date_status_dt.strftime("%d/%m/%Y, %H:%M:%S")
        data['last_date_dt'] = last_date_dt.strftime("%d/%m/%Y, %H:%M:%S")

        try:
            # Envia a mensagem para o Kafka
            self.producer.send(
                topic=self.topic,
                key=str(data['id']).encode('utf-8'),
                value=data
            )
        except Exception as e:
            # Se houver erro ao enviar a mensagem para o Kafka, imprime o erro
            print(f"Erro ao enviar para o Kafka: {e}")

    def _check_updates_(self, data: dict, dt: datetime):
        # Verifica se já existem dados anteriores para o 'id' e obtém as diferenças
        last_data_agent = self.lasts_api_data.get(data['id'], {})
        
        # Se não houver dados anteriores, não há alterações
        if last_data_agent:
            for key in last_data_agent.keys():
                # Se houver alterações, registra no Kafka
                if (key not in ["last_date", "date_status", "date_now"]
                    and last_data_agent[key] != data[key]
                ):
                    self._register_updates_(data.copy(), dt) # Registrar atualização
                    self.lasts_api_data[data['id']] = data  # Atualiza os dados com as últimas informações
                    return True
            
        return False

    def _check_registry_(self, data: dict, dt: datetime):
        if data['id'] not in self.lasts_api_data:
            self.lasts_api_data[data['id']] = data  # Se for a primeira vez que vimos esse 'id', adicionamos aos dados
            self._register_updates_(data.copy(), dt)

    def run(self):
        # Loop para consultar a API periodicamente
        while True:
            now = datetime.now()
            dt_timezone = convert_time(now)
            api_data = self.api.get()
            for data in api_data:
                # checa se o id já está registrado para monitoração
                self._check_registry_(data, dt_timezone)

                # checa se tem mudanças e registra mudanças
                self._check_updates_(data, dt_timezone)

            # Medindo tempo de execução para fazer uma requisição por segundo
            tempo_exec = (datetime.now() - now).total_seconds()
            if tempo_exec < 1:
                time.sleep(1 - tempo_exec)
            