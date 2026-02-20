from sqlalchemy import Select
from sqlalchemy.sql.expression import select

from app.models import Customers, Customers_Blacklist
from core.repository import BaseRepository


class Customers_Blacklist_Repository(BaseRepository[Customers_Blacklist]):
    """
    Customers_Blacklist repository provides all the database operations for the Customers_Blacklist model.
    """

    def _join_customers(self, query: Select) -> Select:
        """
        Joins the Customers table with the Customers_Blacklist table.
        """
        query = query.join(Customers, Customers.id == Customers_Blacklist.customer_id)
        return query

    async def get_by_id(
        self,
        id: int,
        join_: set[str] | None = None,
    ) -> Customers_Blacklist | None:
        """
        Get Customers_Blacklist
        :param id: Customers_Blacklist id.
        :param join_: Join relations.
        :return: Customers_Blacklist
        """
        if join_:
            query = select(self.model_class, Customers)
        else:
            query = select(self.model_class)

        query = self._maybe_join(query, join_)
        query = query.filter(Customers_Blacklist.id == id)

        result = await self.session.execute(query)
        return result.fetchone()

    async def get_by_customer_id(
        self, customer_id: int, join_: set[str] | None = None
    ) -> Customers_Blacklist | None:
        """
        Get Customers_Blacklist
        :param incident_id: Customers_Blacklist id.
        :param join_: Join relations.
        :return: Customers_Blacklist
        """

        query = await self._query(join_)
        query = query.filter(Customers_Blacklist.customer_id == customer_id)

        if join_ is not None:
            return await self._all_unique(query)

        return await self._one_or_none(query)
