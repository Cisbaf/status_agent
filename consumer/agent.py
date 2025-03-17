import pymongo
from pymongo.database import Collection
from pymongo.errors import PyMongoError

class AgentController:

    def __init__(self, collection: Collection):
        self.collection = collection
        try:
            last_entry = list(
                self.collection.find()
                .sort([("date_status_dt", pymongo.DESCENDING), ("last_date_dt", pymongo.DESCENDING)])
                .limit(1)
            )
            self.last_register = last_entry[0] if last_entry else None
        except PyMongoError as e:
            print(f"Erro ao recuperar o último registro: {e}")
            self.last_register = None

    def register(self, data: dict):
        """Registra um novo documento no MongoDB."""
        insert = self.collection.insert_one(data)
        self.last_register = self.collection.find_one({"_id": insert.inserted_id})  # Recupera o documento inserido

    def get_updates(self, data: dict):
        """Compara o último registro salvo com os novos dados e retorna um dicionário de mudanças."""
        if not self.last_register:
            return {}

        last_data_agent = self.last_register.copy()
        last_data_agent.pop('_id', None)  # Remove o campo _id, se existir

        changes = {
            key: {"from": last_data_agent[key], "to": data.get(key, None)}
            for key in last_data_agent.keys()
            if key not in ["last_date", "date_status", "date_now"]
            and last_data_agent[key] != data.get(key, None)
        }
        return changes

    def check(self, data: dict):
        """Verifica se há mudanças nos dados e decide se registra um novo ou apenas atualiza."""
        if not self.last_register:
            self.register(data)
            return

        updates = self.get_updates(data)

        if 'status' in updates or any(key.startswith('STATUS_') for key in updates):
            # print("Mudança de Status", data)
            self.register(data)
        elif updates:
            # Atualiza o último registro se houver mudanças que não sejam status
            update_query = {"_id": self.last_register["_id"]}
            update_data = {"$set": {key: value["to"] for key, value in updates.items()}}
            self.collection.update_one(update_query, update_data)
            # print(f"Atualização feita no último registro: {updates}")
            self.last_register.update(update_data["$set"])
