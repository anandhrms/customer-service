from datetime import date, datetime
from typing import Annotated
from uuid import uuid4

import pytz
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
)

from app.controllers import (
    CloudDBController,
    CustomerDataController,
    Customers_Blacklist_Controller,
    CustomersAuditController,
)
from app.library.helpers import add_customer_data
from app.library.websocket_service.blacklist import BlacklistWebsocketService
from app.models import Customers_Audit
from app.schemas.requests import (
    BlacklistCustomerRequest,
    CreateCustomerRequest,
    RemoveBlacklistRequest,
)
from app.schemas.responses import AddToBlacklistResponse, RemoveBlacklistResponse
from core.config import config
from core.exceptions import BadRequestException
from core.factory import Factory
from core.fastapi.dependencies import AuthenticationRequired
from core.library import logger

customer_router = APIRouter()

controller_factory = Factory()


@customer_router.post(
    "/",
    status_code=200,
    tags=["Customers"],
)
async def add_customer_from_ds(
    create_customer_request: CreateCustomerRequest,
):
    try:
        logger.info(f"Received customer: {create_customer_request.model_dump()}")
        await add_customer_data(create_customer_request.model_dump())
        return {"status": "success"}

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /customers/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@customer_router.post(
    "/test",
    status_code=200,
    tags=["Customers"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def create_customers_test(
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
):
    try:
        created_at = datetime.now().astimezone(pytz.timezone(config.TIMEZONE))
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        customer_data = {
            "cust_id": uuid4().__str__(),
            "com_id": config.TEST_COMPANY_ID,
            "st_id": config.TEST_STORE_ID,
            "created_at": created_at,
            "cam_id": config.TEST_CAMERA_ID,
            "descriptor_1": config.TEST_INCIDENT_DESCRIPTOR,
            "descriptor_2": config.TEST_INCIDENT_DESCRIPTOR,
            "pic_url": "https://framerusercontent.com/images/Kxy5umKOVuZJbcPsE7rre5Aq6M.png?scale-down-to=1024",
            "no_of_visits": 1,
        }

        return await customer_controller.register(customer_data)

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /customers/test : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@customer_router.get(
    "/{branch_id}",
    status_code=200,
    tags=["Customers"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_customers(
    branch_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    from_date: Annotated[
        date | None,
        Query(
            description="Mention the start date in YYYY-MM-DD format",
            example="2024-09-27",
        ),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(
            description="Mention the end date in YYYY-MM-DD format",
            example="2024-09-30",
        ),
    ] = None,
    from_time: Annotated[
        str | None,
        Query(
            description="Mention the start date in HH:MM:SS format",
            example="09:00:00",
        ),
    ] = None,
    to_time: Annotated[
        str | None,
        Query(
            description="Mention the end date in HH:MM:SS format",
            example="09:30:00",
        ),
    ] = None,
    type: Annotated[
        int,
        Query(
            description="Mention whether lazy load or not",
            ge=0,
            le=1,
        ),
    ] = 0,
    offset: Annotated[
        int | None,
        Query(
            description="Mention number of data to be skipped",
            ge=0,
            le=9223372036854775807,
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Query(
            description="Mention number of data to be received",
            ge=0,
            le=9223372036854775807,
        ),
    ] = None,
    is_blacklisted: Annotated[
        int,
        Query(
            description="""
                No filter : 0,
                Blacklisted: 1,
                Not Blacklisted: 2,
            """,
            ge=0,
            le=2,
        ),
    ] = 0,
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
):
    try:
        if is_blacklisted == 0:
            is_blacklisted = None

        elif is_blacklisted == 1:
            is_blacklisted = True

        elif is_blacklisted == 2:
            is_blacklisted = False

        return await customer_controller.get_customers(
            branch_id=branch_id,
            from_date=from_date,
            to_date=to_date,
            from_time=from_time,
            to_time=to_time,
            type=type,
            offset=offset,
            limit=limit,
            is_blacklisted=is_blacklisted,
        )

    except Exception as e:
        logger.error(f"GET /customers/{branch_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@customer_router.get(
    "/{branch_id}/count",
    status_code=200,
    tags=["Customers"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_customers_count(
    branch_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    from_date: Annotated[
        date | None,
        Query(
            description="Mention the start date in YYYY-MM-DD format",
            example="2024-09-27",
        ),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(
            description="Mention the end date in YYYY-MM-DD format",
            example="2024-09-30",
        ),
    ] = None,
    is_blacklisted: Annotated[
        int,
        Query(
            description="""
                No filter : 0,
                Blacklisted: 1,
                Not Blacklisted: 2,
            """,
            ge=0,
            le=2,
        ),
    ] = 0,
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
):
    try:
        if is_blacklisted == 0:
            is_blacklisted = None

        elif is_blacklisted == 1:
            is_blacklisted = True

        elif is_blacklisted == 2:
            is_blacklisted = False

        count = await customer_controller.get_customers_count(
            branch_id=branch_id,
            from_date=from_date,
            to_date=to_date,
            is_blacklisted=is_blacklisted,
        )

        return {"count": count}

    except Exception as e:
        logger.error(f"GET /customers/{branch_id}/count : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@customer_router.post(
    "/blacklists",
    tags=["Customers"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def blacklist_customer(
    background_tasks: BackgroundTasks,
    request: Request,
    blacklist_request: BlacklistCustomerRequest,
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
    blacklist_controller: Customers_Blacklist_Controller = Depends(
        controller_factory.get_customer_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        customer_obj = await customer_controller.get_by_id(blacklist_request.id)

        if customer_obj is None:
            raise BadRequestException("No customer exists")

        if customer_obj.app_blacklisted:
            raise BadRequestException("Customer is already blacklisted")

        customer_obj.app_blacklisted = True
        await customer_controller.customer_data_repository.session.commit()

        await audit_controller.register(
            {
                "customer_id": customer_obj.id,
                "action_type": Customers_Audit.AuditAction.BLACKLISTED,
                "status": Customers_Audit.AuditStatus.ADDED,
                "comments": blacklist_request.comments,
                "created_by": request.user.id,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
                "updated_by": request.user.id,
            }
        )

        blacklist_obj = await blacklist_controller.register(
            {
                "customer_id": customer_obj.id,
                "created_at": datetime.now(pytz.utc),
            }
        )

        if config.BLACKLIST_FIREBASE_ENABLED:
            await cloudDB_controller.add_to_firebase_blacklist_collection(
                blacklist_controller=blacklist_controller,
                blacklist_id=blacklist_obj.id,
                incident_obj=False,
                customer_obj=True,
            )

        if config.BLACKLIST_WEBSOCKET_ENABLED:
            await BlacklistWebsocketService.push_to_blacklist(
                blacklist_controller=blacklist_controller,
                blacklist_id=blacklist_obj.id,
                incident_obj=False,
                customer_obj=True,
            )
            logger.info(f"customer {customer_obj.id} added to watchlist")

        return AddToBlacklistResponse().model_dump()

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /blacklists/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@customer_router.delete(
    "/blacklists/{customer_id}",
    status_code=200,
    tags=["Customers"],
    dependencies=[Depends(AuthenticationRequired)],
    # response_model=RemoveBlacklistResponse,
)
async def remove_from_blacklist(
    request: Request,
    background_tasks: BackgroundTasks,
    customer_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    remove_blacklist_request: RemoveBlacklistRequest,
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
    blacklist_controller: Customers_Blacklist_Controller = Depends(
        controller_factory.get_customer_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        customer_obj = await customer_controller.get_by_id(customer_id)

        if customer_obj.app_blacklisted is False:
            raise BadRequestException("Customer is not blacklisted")

        customer_obj.app_blacklisted = False
        await customer_controller.customer_data_repository.session.commit()

        if customer_obj is None:
            raise BadRequestException("No customer exists")

        await audit_controller.register(
            {
                "customer_id": customer_id,
                "action_type": Customers_Audit.AuditAction.BLACKLISTED,
                "status": Customers_Audit.AuditStatus.REMOVED,
                "comments": remove_blacklist_request.comments,
                "created_by": request.user.id,
                "updated_by": request.user.id,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        await blacklist_controller.remove_from_blacklist(customer_id)

        if config.BLACKLIST_FIREBASE_ENABLED:
            await cloudDB_controller.remove_from_firebase_blacklist_collection(
                controller=customer_controller,
                id_=customer_id,
                incident_obj=False,
                customer_obj=True,
            )

        if config.BLACKLIST_WEBSOCKET_ENABLED:
            await BlacklistWebsocketService.remove_from_blacklist(
                customer_id=customer_obj.customer_id,
                branch_id=customer_obj.branch_id,
            )
            logger.info(f"customer {customer_obj.id} removed from watchlist")

        return RemoveBlacklistResponse().model_dump()

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"DELETE /blacklists/{customer_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
