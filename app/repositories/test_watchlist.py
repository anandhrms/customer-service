from app.models import TestWatchlistedCustomers
from core.repository import BaseRepository


class TestWatchlistedRepository(BaseRepository[TestWatchlistedCustomers]):
    """
    TestWatchlistedRepository provides all the database operations for the TestWatchlistedCustomers model.
    """

    async def get_by_customer_id(
        self, customer_id: int, join_: set[str] | None = None
    ) -> list[TestWatchlistedCustomers] | None:
        """
        Get TestWatchlistedCustomers by customer_id.
        :param customer_id: Customers id.
        :param join_: Join relations.
        :return: list[TestWatchlistedCustomers].
        """
        query = await self._query(join_)
        query = query.filter(TestWatchlistedCustomers.customer_id == customer_id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._all(query)
