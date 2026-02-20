from datetime import date, datetime, timedelta

import pytz

from app.library.helpers.entity_helper import get_company_branch_camera_id
from app.models import Customers
from app.repositories import CustomerDataRepository
from app.schemas.responses import CustomerData, GetCustomersResponse
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.library.logging import logger


def modify_time_range(date_obj: date, hour: int, minute: int, second: int = 0):
    datetime_obj = datetime.strptime(date_obj.isoformat(), "%Y-%m-%d")
    datetime_obj = datetime_obj.replace(
        hour=hour,
        minute=minute,
        second=second,
    )

    return datetime_obj


time_intervals = {
    "12:00 AM - 1:00 AM": ((0, 0), (1, 0)),
    "1:00 AM - 2:00 AM": ((1, 0), (2, 0)),
    "2:00 AM - 3:00 AM": ((2, 0), (3, 0)),
    "3:00 AM - 4:00 AM": ((3, 0), (4, 0)),
    "4:00 AM - 5:00 AM": ((4, 0), (5, 0)),
    "5:00 AM - 6:00 AM": ((5, 0), (6, 0)),
    "6:00 AM - 7:00 AM": ((6, 0), (7, 0)),
    "7:00 AM - 8:00 AM": ((7, 0), (8, 0)),
    "8:00 AM - 9:00 AM": ((8, 0), (9, 0)),
    "9:00 AM - 10:00 AM": ((9, 0), (10, 0)),
    "10:00 AM - 11:00 AM": ((10, 0), (11, 0)),
    "11:00 AM - 12:00 PM": ((11, 0), (12, 0)),
    "12:00 PM - 1:00 PM": ((12, 0), (13, 0)),
    "1:00 PM - 2:00 PM": ((13, 0), (14, 0)),
    "2:00 PM - 3:00 PM": ((14, 0), (15, 0)),
    "3:00 PM - 4:00 PM": ((15, 0), (16, 0)),
    "4:00 PM - 5:00 PM": ((16, 0), (17, 0)),
    "5:00 PM - 6:00 PM": ((17, 0), (18, 0)),
    "6:00 PM - 7:00 PM": ((18, 0), (19, 0)),
    "7:00 PM - 8:00 PM": ((19, 0), (20, 0)),
    "8:00 PM - 9:00 PM": ((20, 0), (21, 0)),
    "9:00 PM - 10:00 PM": ((21, 0), (22, 0)),
    "10:00 PM - 11:00 PM": ((22, 0), (23, 0)),
    "11:00 PM - 12:00 AM": ((23, 0), (23, 59)),
}


class CustomerDataController(BaseController[Customers]):
    def __init__(self, customer_data_repository: CustomerDataRepository):
        super().__init__(model=Customers, repository=customer_data_repository)
        self.customer_data_repository = customer_data_repository

    async def get_by_id(self, id: int) -> Customers | None:
        return await self.customer_data_repository.get_by_id(id)

    async def get_by_customer_url(self, url: str) -> Customers | None:
        return await self.customer_data_repository.get_by_customer_url(url)

    async def get_by_customer_id(self, customer_id: str) -> Customers | None:
        return await self.customer_data_repository.get_by_customer_id(customer_id)

    async def get_branch_customers(
        self,
        branch_id: int,
        from_datetime: datetime | None,
        to_datetime: datetime | None,
        is_blacklisted: bool | None,
        offset: int | None,
        limit: int | None,
    ):
        customers = await self.customer_data_repository.get_customers(
            branch_id=branch_id,
            from_date=from_datetime,
            to_date=to_datetime,
            is_blacklisted=is_blacklisted,
            offset=offset,
            limit=limit,
        )

        customer_data = []
        for (
            id,
            pic_url,
            analyst_blacklisted,
            app_blacklisted,
            visited_time,
        ) in customers:
            visited_time = visited_time.strftime("%Y-%m-%d %H:%M:%S")

            customer_data.append(
                CustomerData(
                    customer_id=id,
                    pic_url=pic_url,
                    analyst_blacklisted=analyst_blacklisted,
                    app_blacklisted=app_blacklisted,
                    created_at=visited_time,
                )
            )

        return customer_data

    async def get_customers_by_date_and_branch(
        self,
        branch_id: int,
        from_date: date | None,
        to_date: date | None,
        from_hour: int,
        from_minute: int,
        to_hour: int,
        to_minute: int,
        is_blacklisted: bool | None,
        offset: int,
        limit: int,
    ):
        from_datetime = modify_time_range(
            date_obj=from_date,
            hour=from_hour,
            minute=from_minute,
        )

        to_datetime = modify_time_range(
            date_obj=to_date,
            hour=to_hour,
            minute=to_minute,
        )

        customer_data = await self.get_branch_customers(
            branch_id=branch_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            is_blacklisted=is_blacklisted,
            offset=offset,
            limit=limit,
        )

        return customer_data

    async def get_customers_count(
        self,
        branch_id: int,
        to_date: date | None,
        from_date: date | None,
        is_blacklisted: bool | None,
    ):
        from_datetime = modify_time_range(
            date_obj=from_date,
            hour=0,
            minute=0,
        )

        to_datetime = modify_time_range(
            date_obj=to_date,
            hour=23,
            minute=59,
            second=59,
        )

        return await self.customer_data_repository.get_customers_count(
            branch_id=branch_id,
            from_date=from_datetime,
            to_date=to_datetime,
            is_blacklisted=is_blacklisted,
        )

    async def get_customers(
        self,
        branch_id: int,
        from_date: date | None,
        to_date: date | None,
        from_time: str | None,
        to_time: str | None,
        type: int,
        offset: int | None,
        limit: int | None,
        is_blacklisted: bool | None,
    ):
        if from_time == "" or from_time == "null" or from_time is None:
            from_time = None

        else:
            from_time = datetime.strptime(from_time, "%H:%M:%S").time()

        if to_time == "" or to_time == "null" or to_time is None:
            to_time = None

        else:
            to_time = datetime.strptime(to_time, "%H:%M:%S").time()

        response = []

        # if single day is selected
        if from_date == to_date:
            # if no lazy load (initial request)
            if type == 0:
                for key, value in time_intervals.items():
                    customer_data = await self.get_customers_by_date_and_branch(
                        branch_id=branch_id,
                        from_date=from_date,
                        to_date=to_date,
                        from_hour=value[0][0],
                        from_minute=value[0][1],
                        to_hour=value[1][0],
                        to_minute=value[1][1],
                        is_blacklisted=is_blacklisted,
                        offset=offset,
                        limit=limit,
                    )

                    if customer_data:
                        response.append(
                            GetCustomersResponse(
                                interval="Time: ",
                                label=key,
                                data=customer_data,
                            )
                        )

                return response

            # for lazy load
            else:
                # for time specific card
                if from_time and to_time:
                    customer_data = await self.get_customers_by_date_and_branch(
                        branch_id=branch_id,
                        from_date=from_date,
                        to_date=to_date,
                        from_hour=from_time.hour,
                        from_minute=from_time.minute,
                        to_hour=to_time.hour,
                        to_minute=to_time.minute,
                        is_blacklisted=is_blacklisted,
                        offset=offset,
                        limit=limit,
                    )

                    if customer_data:
                        response.append(
                            GetCustomersResponse(
                                data=customer_data,
                            )
                        )

                    return response

                # for date specific card
                else:
                    customer_data = await self.get_customers_by_date_and_branch(
                        branch_id=branch_id,
                        from_date=from_date,
                        to_date=to_date,
                        from_hour=0,
                        from_minute=0,
                        to_hour=23,
                        to_minute=59,
                        is_blacklisted=is_blacklisted,
                        offset=offset,
                        limit=limit,
                    )

                    if customer_data:
                        response.append(
                            GetCustomersResponse(
                                data=customer_data,
                            )
                        )

                    return response

        # if multiple days are selected
        else:
            response = []
            current_date = to_date

            while current_date >= from_date:
                customer_data = await self.get_customers_by_date_and_branch(
                    branch_id=branch_id,
                    from_date=current_date,
                    to_date=current_date,
                    from_hour=0,
                    from_minute=0,
                    to_hour=23,
                    to_minute=59,
                    is_blacklisted=is_blacklisted,
                    offset=offset,
                    limit=limit,
                )

                if customer_data:
                    response.append(
                        GetCustomersResponse(
                            interval="Date: ",
                            label=current_date.strftime("%d %b, %Y"),
                            data=customer_data,
                        )
                    )

                current_date -= timedelta(days=1)

            return response

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, add_customer_request: dict) -> Customers:
        company_branch_camera_response = await get_company_branch_camera_id(
            company_uuid=add_customer_request.get("com_id"),
            branch_uuid=add_customer_request.get("st_id"),
            camera_uuid=add_customer_request.get("cam_id"),
        )

        if company_branch_camera_response is None:
            logger.error("Error in finding company or branch or camera")
            return

        company_id, branch_id, camera_id = company_branch_camera_response

        if add_customer_request.get("created_at"):
            try:
                visited_time = datetime.strptime(
                    add_customer_request["created_at"], "%Y-%m-%d %H:%M:%S"
                )

            except Exception:
                visited_time = datetime.now()

        else:
            visited_time = datetime.now()

        customer_data = {
            "customer_id": add_customer_request.get("cust_id"),
            "company_id": company_id,
            "branch_id": branch_id,
            "camera_id": camera_id,
            "descriptor_1": add_customer_request.get("descriptor_1"),
            "descriptor_2": add_customer_request.get("descriptor_2"),
            "pic_url": add_customer_request.get("pic_url"),
            "no_of_visits": add_customer_request.get("no_of_visits"),
            "visited_time": visited_time,
            "created_at": datetime.now(pytz.utc),
        }

        return await self.customer_data_repository.create(customer_data)
