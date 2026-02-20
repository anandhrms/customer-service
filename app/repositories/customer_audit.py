from app.models import Customers_Audit
from core.repository import BaseRepository


class CustomersAuditRepository(BaseRepository[Customers_Audit]):
    """
    Customers_Audit repository provides all the database operations for the Customers_Audit model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Customers_Audit | None:
        """
        Get Customers_Audit by id.
        :param int: Customers_Audit id.
        :param join_: Join relations.
        :return: Customers_Audit.
        """
        query = await self._query(join_)
        query = query.filter(Customers_Audit.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_customer_audit(self, customer_id: int, join_: set[str] | None = None):
        query = await self._query(join_)
        query = query.filter(Customers_Audit.customer_id == customer_id)
        query = query.order_by(Customers_Audit.created_at.desc())

        if join_ is not None:
            return await self._all_unique(query)

        return await self._all(query)
