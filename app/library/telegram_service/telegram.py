import requests

from core.config import config


class TelegramService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TelegramService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.url = config.TELEGRAM_SERVICE_URL
            self._initialized = True

    async def send_was_on_watchlist_alert(self, data: dict):
        url = self.url + "/send_message_previous_blacklist"
        payload = {
            "incident_id": data.get("inci_id"),
            "incident_time": data.get("inci_time"),
            "branch_id": data.get("st_id"),
            "file_url": data.get("pic_url"),
            "video_url": data.get("video_url"),
        }
        return requests.post(url=url, json=payload, timeout=10)

    async def send_sensitive_incidents_alert(self, data: dict):
        url = self.url + "/send_message"
        payload = {
            "incident_id": data.get("inci_id"),
            "incident_time": data.get("inci_time"),
            "branch_id": data.get("st_id"),
            "file_url": data.get("video_url"),
            "video_url": data.get("video_url"),
        }
        return requests.post(url=url, json=payload, timeout=10)
