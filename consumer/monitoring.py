from agent import AgentController
from pymongo.database import Database
from typing import Dict

class MonitoringController:

    def __init__(self, database: Database):
        self.database = database
        self.controlers: Dict[str, AgentController] = {}

    def check(self, data: dict):
        if not data['id'] in self.controlers:
            self.controlers[data['id']] = AgentController(self.database[data['id']])
        self.controlers[data['id']].check(data)