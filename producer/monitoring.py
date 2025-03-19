from kafka import KafkaProducer
from api import ApiRequest
from datetime import datetime, timezone, timedelta
import pytz, json, time

class MonitoringStatusAgent:

    def __init__(self, topic: str, kafka_uri: str, api: ApiRequest):
        self.topic = topic
        self.lasts_api_data = {}
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_uri,
            api_version=(3, 8, 0),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),  # Serializar a mensagem para JSON
            key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k  # Serializar chave, se for string
        )
        self.api = api

    def convert_time(self, dt: datetime):
        return dt.astimezone(timezone.utc).astimezone(pytz.timezone('America/Sao_Paulo'))
    
    def get_updates(self, data: dict):
        # Verifica se já existem dados anteriores para o 'id' e obtém as diferenças
        last_data_agent = self.lasts_api_data.get(data['id'], {})
        
        # Se não houver dados anteriores, não há alterações
        if not last_data_agent:
            return []
        
        # Lista de mudanças detectadas nos dados
        changes = [
            {
                "field": key,
                "from": last_data_agent[key],
                "to": data[key]
            } for key in last_data_agent.keys()
                if key not in ["last_date", "date_status", "date_now"]
                if last_data_agent[key] != data[key]
        ]
        return changes
    
    def convert_time_to_datetime(self, time_str: str, dt: datetime):
        # Converte a string de tempo no formato HH:MM:SS para um datetime, subtraindo do datetime base
        if time_str != '00:00:00' and not '.' in time_str:
            hours, minutes, seconds = map(int, time_str.split(':'))
            dt -= timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return dt

    def register_updates(self, data: dict, updates: list, dt: datetime):
        # Converte as datas de status e última data para datetime
        date_status_dt = self.convert_time_to_datetime(data['date_status'], dt)
        last_date_dt = self.convert_time_to_datetime(data['last_date'], dt)

        # Atualiza os campos com os valores formatados
        data['date_status_dt'] = date_status_dt.strftime("%d/%m/%Y, %H:%M:%S")
        data['last_date_dt'] = last_date_dt.strftime("%d/%m/%Y, %H:%M:%S")

        # Definindo os metadados (headers) como um dicionário com valores codificados em bytes
        # headers = [
        #         ('changes', json.dumps(updates)),  # Exemplo de metadado com chave "changes"
        #     ]
        try:
            # Envia a mensagem para o Kafka
            self.producer.send(self.topic, key=data['id'].encode('utf-8'), value=data)
        except Exception as e:
            # Se houver erro ao enviar a mensagem para o Kafka, imprime o erro
            print(f"Erro ao enviar para o Kafka: {e}")

    def run(self):
        # Loop para consultar a API periodicamente
        while True:
            now = datetime.now()
            dt_timezone = self.convert_time(now)
            api_data = self.api.get()
            for data in api_data:
                if data['id'] not in self.lasts_api_data:
                    self.lasts_api_data[data['id']] = data  # Se for a primeira vez que vimos esse 'id', adicionamos aos dados
                    self.register_updates(data.copy(), None, dt_timezone)
                    
                # Obtém as atualizações de dados
                updates = self.get_updates(data)
                
                # Se houver alterações, registra no Kafka
                if updates:
                    self.register_updates(data.copy(), updates, dt_timezone)
                    self.lasts_api_data[data['id']] = data  # Atualiza os dados com as últimas informações
            
            # Medindo tempo de execução para fazer uma requisição por segundo
     
            tempo_exec = (datetime.now() - now).total_seconds()
            if tempo_exec < 0.5:
                time.sleep(0.5 - tempo_exec)
            