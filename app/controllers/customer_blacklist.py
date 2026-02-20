from app.models import Customers_Blacklist
from app.repositories import Customers_Blacklist_Repository
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException


class Customers_Blacklist_Controller(BaseController[Customers_Blacklist]):
    def __init__(self, blacklist_repository: Customers_Blacklist_Repository):
        super().__init__(model=Customers_Blacklist, repository=blacklist_repository)
        self.blacklist_repository = blacklist_repository

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Customers_Blacklist | None:
        return await self.blacklist_repository.get_by_id(id=id, join_=join_)

    async def remove_from_blacklist(
        self,
        customer_id: int,
    ):
        blacklist = await self.blacklist_repository.get_by_customer_id(customer_id)

        if blacklist is None:
            raise BadRequestException(message="No such customer exists")

        await self.blacklist_repository.session.delete(blacklist)
        await self.blacklist_repository.session.commit()

        return blacklist

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, register_blacklist_request: dict) -> Customers_Blacklist:
        blacklist = await self.blacklist_repository.get_by_customer_id(
            register_blacklist_request.get("customer_id")
        )

        if blacklist is None:
            return await self.blacklist_repository.create(register_blacklist_request)

        return blacklist
