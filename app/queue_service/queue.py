import requests

from core.config import config


class AnalystQueueingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AnalystQueueingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.url = config.QUEUEING_SERVICE_URL
            self._initialized = True

    async def add_to_incidents_queue(self, incident_id: int):
        url = self.url + "/v1/customer-service/incidents-queue/"
        payload = {"incident_ids": [incident_id]}
        return requests.post(url=url, json=payload, timeout=10)
