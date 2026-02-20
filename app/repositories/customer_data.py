from datetime import datetime

from sqlalchemy import select

from app.models import Customers
from core.repository import BaseRepository


class CustomerDataRepository(BaseRepository[Customers]):
    """
    CustomerData repository provides all the database operations for the Customers model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Customers | None:
        """
        Get Customer by id.
        :param int: Customer id.
        :param join_: Join relations.
        :return: Customers.
        """
        query = await self._query(join_)
        query = query.filter(Customers.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_by_customer_url(
        self, url: str, join_: set[str] | None = None
    ) -> Customers | None:
        """
        Get Customer by url.
        :param int: Customer url.
        :param join_: Join relations.
        :return: Customers.
        """
        query = await self._query(join_)
        query = query.filter(Customers.pic_url == url)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_by_customer_id(
        self, customer_id: str, join_: set[str] | None = None
    ) -> Customers | None:
        """
        Get Customer by customer_id.
        :param str: Customer customer_id.
        :param join_: Join relations.
        :return: Customers.
        """
        query = await self._query(join_)
        query = query.filter(Customers.customer_id == customer_id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_customers(
        self,
        branch_id: int,
        from_date: datetime | None,
        to_date: datetime | None,
        is_blacklisted: bool | None,
        offset: int | None,
        limit: int | None,
    ):
        query = select(
            Customers.id,
            Customers.pic_url,
            Customers.analyst_blacklisted,
            Customers.app_blacklisted,
            Customers.visited_time,
        )

        query = query.filter(
            Customers.branch_id == branch_id,
            Customers.visited_time >= from_date,
            Customers.visited_time < to_date,
        )

        if is_blacklisted is not None:
            query = query.filter(
                Customers.app_blacklisted == is_blacklisted,
            )

        query = query.offset(offset)
        query = query.limit(limit)

        query = query.order_by(Customers.visited_time.asc())

        result = await self.session.execute(query)
        return result.fetchall()

    async def get_customers_count(
        self,
        branch_id: int,
        from_date: datetime | None,
        to_date: datetime | None,
        is_blacklisted: bool | None,
    ):
        query = select(self.model_class)

        query = query.filter(
            Customers.branch_id == branch_id,
            Customers.visited_time >= from_date,
            Customers.visited_time <= to_date,
        )

        if is_blacklisted is not None:
            query = query.filter(Customers.app_blacklisted == is_blacklisted)

        return await self._count(query)
