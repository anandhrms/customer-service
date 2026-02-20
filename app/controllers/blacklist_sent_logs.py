from datetime import datetime
from app.models import BlacklistSentLogs
from app.repositories import BlacklistSentLogsRepository
from core.controller import BaseController
from core.database import Propagation, Transactional


class BlacklistSentLogsController(BaseController[BlacklistSentLogs]):
    def __init__(self, blacklist_sent_logs_repository: BlacklistSentLogsRepository):
        super().__init__(
            model=BlacklistSentLogs, repository=blacklist_sent_logs_repository
        )
        self.blacklist_sent_logs_repository = blacklist_sent_logs_repository

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, create_error_log_request: dict) -> BlacklistSentLogs:
        return await self.blacklist_sent_logs_repository.create(
            create_error_log_request
        )
        
    async def get_blacklist_logs(self,branch_id: int, created_at: datetime):
         return await self.blacklist_sent_logs_repository.get_blacklist_log(branch_id=branch_id,created_at=created_at)