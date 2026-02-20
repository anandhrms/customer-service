from app.models import TestWatchlistedCustomers
from app.repositories import TestWatchlistedRepository
from core.controller import BaseController


class TestWatchlistedController(BaseController[TestWatchlistedCustomers]):
    def __init__(self, test_watchlist_repository: TestWatchlistedRepository):
        super().__init__(
            model=TestWatchlistedCustomers, repository=test_watchlist_repository
        )
        self.test_watchlist_repository = test_watchlist_repository

    async def get_by_customer_id(
        self, customer_id: int
    ) -> TestWatchlistedCustomers | None:
        return await self.test_watchlist_repository.get_by_customer_id(customer_id)
