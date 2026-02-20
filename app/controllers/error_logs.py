from app.models import ErrorLogs
from app.repositories import ErrorLogsRepository
from core.controller import BaseController
from core.database import Propagation, Transactional


class ErrorLogsController(BaseController[ErrorLogs]):
    def __init__(self, error_logs_repository: ErrorLogsRepository):
        super().__init__(model=ErrorLogs, repository=error_logs_repository)
        self.error_logs_repository = error_logs_repository

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, create_error_log_request: dict) -> ErrorLogs:
        return await self.error_logs_repository.create(create_error_log_request)
