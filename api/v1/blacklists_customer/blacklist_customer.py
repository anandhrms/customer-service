from datetime import date, datetime,timedelta, timezone
from typing import Annotated

import pytz
import requests
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
    ErrorLogsController,
    Incidents_Blacklist_Controller,
    IncidentsAuditController,
    IncidentsController,
    BlacklistSentLogsController
)
from app.controllers.blacklist_sent_logs import BlacklistSentLogsController
from app.library.helpers.entity_helper import get_company_branch_camera_id
from app.library.helpers import get_blacklist_data
from app.library.websocket_service.blacklist import BlacklistWebsocketService
from app.models import Customers_Audit, Incidents, Incidents_Audit
from app.models.incidents import BlacklistSentLogs
from app.schemas.requests import (
    BlacklistIncidentRequest,
    DbHardwareSyncRequest,
    RemoveBlacklistRequest,
    TelegramBlacklistIncidentRequest,
)
from app.schemas.responses import AddToBlacklistResponse, RemoveBlacklistResponse
from core.config import config
from core.exceptions import BadRequestException, NotFoundException
from core.factory import Factory
from core.fastapi.dependencies import AuthenticationRequired
from core.library import logger

blacklist_router = APIRouter()

controller_factory = Factory()

BLACKLIST_TEMPLATE = config.BLACKLIST_TEMPLATE
BLACKLIST_GROUP = config.BLACKLISTED

NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON = (
    config.NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON
)
NOTIFICATION_TYPE_PUSH_NOTIFICATION = config.NOTIFICATION_TYPE_PUSH_NOTIFICATION


@blacklist_router.get(
    "/{branch_id}",
    status_code=200,
    tags=["Blacklists"],
    dependencies=[Depends(AuthenticationRequired)],
    # response_model=list[BlacklistIncidentResponse],
)
async def get_blacklisted_customers(
    request: Request,
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
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    customer_audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
):
    try:
        is_test_user = (
            False if request.user.role_id != config.SUPER_USER_ROLE_ID else True
        )

        return await blacklist_controller.get_blacklists(
            audit_controller=audit_controller,
            incidents_controller=incidents_controller,
            customer_data_controller=customer_data_controller,
            customer_audit_controller=customer_audit_controller,
            from_date=from_date,
            to_date=to_date,
            skip=offset,
            limit=limit,
            branch_id=branch_id,
            is_test_user=is_test_user,
        )

    except Exception as e:
        logger.error(f"GET /blacklists/{branch_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@blacklist_router.get(
    "/{branch_id}/count",
    tags=["Blacklists"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_blacklists_count(
    request: Request,
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
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
):
    try:
        is_test_user = (
            False if request.user.role_id != config.SUPER_USER_ROLE_ID else True
        )

        count = await blacklist_controller.get_blacklists_count(
            branch_id=branch_id,
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
        )
        return {"count": count}

    except Exception as e:
        logger.error(f"GET /blacklists/{branch_id}/count : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@blacklist_router.post(
    "/",
    tags=["Blacklists"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def blacklist_incident(
    background_tasks: BackgroundTasks,
    request: Request,
    blacklist_request: BlacklistIncidentRequest,
    blacklistsentlogs_contoller: BlacklistSentLogsController = Depends(
        controller_factory.get_blacklist_sent_logs_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
):
    try:
        incident, update_status = await incidents_controller.update_blacklist_status(
            user_id=request.user.id, update_incident_request=blacklist_request
        )

        comments = blacklist_request.comments

        if update_status is True:
            await audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": blacklist_request.status,
                    "status": Incidents_Audit.AuditStatus.ADDED,
                    "comments": comments,
                    "created_by": request.user.id,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": request.user.id,
                }
            )

            comments = None

        await audit_controller.register(
            {
                "incident_id": incident.id,
                "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                "status": Incidents_Audit.AuditStatus.ADDED,
                "comments": comments,
                "created_by": request.user.id,
                "updated_by": request.user.id,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        blacklist_obj = await blacklist_controller.register(
            {
                "incident_id": incident.id,
                "created_at": datetime.now(pytz.utc),
            }
        )

        url = f"{config.CUSTOMER_ANALYST_SERVICE_URL}/api/video_analyst/customer_black_list"
        payload = {
            "incident_id": incident.incident_id,
            "is_blacklist": 3,
            "pending": 1,
        }
        response = requests.post(
            url=url,
            json=payload,
            timeout=5,
        )

        if not response.ok:
            logger.error(f"Failed to update customer analyst service: {response.text}")

        if incident.analyst_blacklisted:
            if config.BLACKLIST_FIREBASE_ENABLED:
                await cloudDB_controller.add_to_firebase_blacklist_collection(
                    blacklist_controller,
                    customer_data_controller,
                    blacklist_obj.id,
                    True,
                    False,
                )
            if config.BLACKLIST_WEBSOCKET_ENABLED:
                await BlacklistWebsocketService.push_to_blacklist(
                    blacklist_sent_logs_controller=blacklistsentlogs_contoller,
                    blacklist_controller=blacklist_controller,
                    blacklist_id=blacklist_obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )
                logger.info(f"incident {incident.id} added to watchlist")

        return AddToBlacklistResponse().model_dump()

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /blacklists/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@blacklist_router.post(
    "/telegram",
    tags=["Blacklists"],
)
async def telegram_blacklist_incident(
    blacklist_request: TelegramBlacklistIncidentRequest,
    blacklistsentlogs_contoller: BlacklistSentLogsController = Depends(
        controller_factory.get_blacklist_sent_logs_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    error_logs_controller: ErrorLogsController = Depends(
        controller_factory.get_error_logs_controller
    ),
):
    try:
        incident_obj = await incidents_controller.get_incident_by_incident_id(
            incident_id=blacklist_request.incident_id
        )

        if incident_obj is None:
            raise NotFoundException("No incident exists with this id")

        blacklist_request.id = incident_obj.id
        incident, update_status = await incidents_controller.update_blacklist_status(
            user_id=1, update_incident_request=blacklist_request
        )

        comments = blacklist_request.comments

        if update_status is True:
            await audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": blacklist_request.status,
                    "status": Incidents_Audit.AuditStatus.ADDED,
                    "comments": comments,
                    "created_by": 1,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": 1,
                }
            )

            comments = None

        await audit_controller.register(
            {
                "incident_id": incident.id,
                "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                "status": Incidents_Audit.AuditStatus.ADDED,
                "comments": comments,
                "created_by": 1,
                "updated_by": 1,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        blacklist_obj = await blacklist_controller.register(
            {
                "incident_id": incident.id,
                "created_at": datetime.now(pytz.utc),
            }
        )

        url = f"{config.CUSTOMER_ANALYST_SERVICE_URL}/api/video_analyst/customer_black_list"
        payload = {
            "incident_id": incident.incident_id,
            "is_blacklist": 3,
            "pending": 1,
        }
        response = requests.post(url=url, json=payload, timeout=5)

        if not response.ok:
            logger.error(f"Failed to update customer analyst service: {response.text}")

        if incident.analyst_blacklisted:
            if config.BLACKLIST_FIREBASE_ENABLED:
                await cloudDB_controller.add_to_firebase_blacklist_collection(
                    blacklist_controller=blacklist_controller,
                    blacklist_id=blacklist_obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )

            if config.BLACKLIST_WEBSOCKET_ENABLED:
                await BlacklistWebsocketService.push_to_blacklist(
                    blacklist_sent_logs_controller=blacklistsentlogs_contoller,
                    blacklist_controller=blacklist_controller,
                    blacklist_id=blacklist_obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )
                logger.info(f"incident {incident.id} added to watchlist")

        return {"status": "success"}

    except NotFoundException as e:
        await error_logs_controller.register(
            {
                "incident_id": blacklist_request.incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except BadRequestException as e:
        await error_logs_controller.register(
            {
                "incident_id": blacklist_request.incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /blacklists/telegram : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@blacklist_router.post(
    "/firebase/{incident_id}",
    tags=["Blacklists"],
)
async def add_watchlisted_incident_to_firebase(
    request: Request,
    incident_id: int,
    blacklistsentlogs_contoller: BlacklistSentLogsController = Depends(
        controller_factory.get_blacklist_sent_logs_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    error_logs_controller: ErrorLogsController = Depends(
        controller_factory.get_error_logs_controller
    ),
):
    try:
        blacklist_obj = await blacklist_controller.get_by_incident_id(
            incident_id=incident_id,
        )

        if blacklist_obj:
            if config.BLACKLIST_FIREBASE_ENABLED:
                await cloudDB_controller.add_to_firebase_blacklist_collection(
                    blacklist_controller=blacklist_controller,
                    blacklist_id=blacklist_obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )

            if config.BLACKLIST_WEBSOCKET_ENABLED:
                await BlacklistWebsocketService.push_to_blacklist(
                    blacklist_sent_logs_controller=blacklistsentlogs_contoller,
                    blacklist_controller=blacklist_controller,
                    blacklist_id=blacklist_obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )
                logger.info(f"incident {blacklist_obj.incident_id} added to watchlist")

            return {"status": "success", "message": "Added to firebase collection"}

        return {"status": "failed", "message": "Not a blacklisted incident"}

    except Exception as e:
        await error_logs_controller.register(
            {
                "incident_id": incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        logger.error(f"{request.method} {request.url} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@blacklist_router.delete(
    "/{incident_id}",
    status_code=200,
    tags=["Blacklists"],
    dependencies=[Depends(AuthenticationRequired)],
    # response_model=RemoveBlacklistResponse,
)
async def remove_from_blacklist(
    request: Request,
    background_tasks: BackgroundTasks,
    incident_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    remove_blacklist_request: RemoveBlacklistRequest,
    blacklistsentlogs_contoller: BlacklistSentLogsController = Depends(
        controller_factory.get_blacklist_sent_logs_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    customer_audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
    customer_blacklist_controller: Customers_Blacklist_Controller = Depends(
        controller_factory.get_customer_blacklist_controller
    ),
):
    try:
        obj = await incidents_controller.remove_from_blacklists(
            user_id=request.user.id,
            incident_id=incident_id,
        )

        if isinstance(obj, Incidents):
            await audit_controller.register(
                {
                    "incident_id": obj.id,
                    "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                    "status": Incidents_Audit.AuditStatus.REMOVED,
                    "comments": remove_blacklist_request.comments,
                    "created_by": request.user.id,
                    "updated_by": request.user.id,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                }
            )
            
            blacklist_obj = await blacklist_controller.get_by_incident_id(incident_id=obj.id)
            
            incident_id = await blacklist_controller.remove_from_blacklist(obj.id)
            
            if config.BLACKLIST_FIREBASE_ENABLED:
                await cloudDB_controller.remove_from_firebase_blacklist_collection(
                    controller=incidents_controller,
                    id_=obj.id,
                    incident_obj=True,
                    customer_obj=False,
                )

            if config.BLACKLIST_WEBSOCKET_ENABLED:
                customer_obj = await customer_controller.get_by_id(obj.customer_id)

                await BlacklistWebsocketService.remove_from_blacklist(
                    blacklist_sent_logs_controller=blacklistsentlogs_contoller,
                    company_id=obj.company_id,
                    incident_id=obj.incident_id,
                    blacklist_id=blacklist_obj.id,
                    incident_int_id=obj.id,
                    branch_id=obj.branch_id,
                    customer_uuid_id=customer_obj.customer_id,
                    customer_id=customer_obj.id if customer_obj else None,
                )
                logger.info(f"incident {obj.id} removed from watchlist")

        elif isinstance(obj, int):
            customer_obj = await customer_controller.get_by_id(obj)

            if not customer_obj:
                logger.error(f"Customer does not exist with this id: {obj}")
                raise NotFoundException("Customer does not exist with this id")

            if not customer_obj.app_blacklisted:
                raise BadRequestException(
                    "Customer is not watchlisted or removed from watchlist"
                )

            customer_obj.app_blacklisted = False
            await customer_controller.customer_data_repository.session.commit()

            await customer_audit_controller.register(
                {
                    "customer_id": customer_obj.id,
                    "action_type": Customers_Audit.AuditAction.BLACKLISTED,
                    "status": Customers_Audit.AuditStatus.REMOVED,
                    "comments": remove_blacklist_request.comments,
                    "created_by": request.user.id,
                    "updated_by": request.user.id,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                }
            )

            await customer_blacklist_controller.remove_from_blacklist(customer_obj.id)

            if config.BLACKLIST_FIREBASE_ENABLED:
                await cloudDB_controller.remove_from_firebase_blacklist_collection(
                    controller=customer_controller,
                    id_=customer_obj.id,
                    incident_obj=False,
                    customer_obj=True,
                )

            if config.BLACKLIST_WEBSOCKET_ENABLED:
                await BlacklistWebsocketService.remove_from_blacklist(
                    blacklist_sent_logs_controller=blacklistsentlogs_contoller,
                    customer_id=customer_obj.customer_id,
                    branch_id=customer_obj.branch_id,
                )
                logger.info(
                    f"customer {customer_obj.customer_id} removed from watchlist"
                )

        else:
            return {"status": "failed", "message": "Customer or Incident not found"}

        return RemoveBlacklistResponse().model_dump()

    except (BadRequestException, NotFoundException) as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"GET /blacklists/{incident_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



@blacklist_router.post(
    "/hardware",
    status_code=200,
    tags=["Blacklists"],
)
async def db_hardware_sync(
    db_hardware_sync_request: DbHardwareSyncRequest,
    blacklistsentlogs_contoller: BlacklistSentLogsController = Depends(
        controller_factory.get_blacklist_sent_logs_controller
    ),
    incidents_blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        remove_incident_ids = []
        add_incident_data = []

        company_id, branch_id, _ = await get_company_branch_camera_id(
            company_uuid=db_hardware_sync_request.company_id,
            branch_uuid=db_hardware_sync_request.branch_id,
            camera_uuid=None
        )

        if company_id is None or branch_id is None:
            message = f"Invalid company or branch - company: {db_hardware_sync_request.company_id}, branch: {db_hardware_sync_request.branch_id}"
            logger.error(message)
            raise NotFoundException(message)

        print(f"Processing for branch_id: {branch_id}")
        
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        logs = await blacklistsentlogs_contoller.get_blacklist_logs(
            branch_id=branch_id,
            created_at=one_hour_ago
        )

        add_incident_data = []
        remove_incident_ids = []

        for log in logs:
            #  ADD
            if log.action_type == BlacklistSentLogs.ActionTypes.ADD:
                blacklist_data = await get_blacklist_data(
                    blacklist_controller=incidents_blacklist_controller,
                    blacklist_id=log.blacklist_id,
                    incident_obj=True,
                    customer_obj=False,
                )
                # append only if not null
                if blacklist_data is not None:
                    add_incident_data.append(blacklist_data)

            #  REMOVE
            elif log.action_type == BlacklistSentLogs.ActionTypes.REMOVE:
                incident = await incidents_controller.get_by_id(log.incident_id)
                customer = await customer_controller.get_by_id(incident.customer_id)
                data= {
                    "incident_id": incident.incident_id,
                    "customer_id": customer.customer_id
                }
                remove_incident_ids.append(data)

        return {
            "add": add_incident_data,
            "remove": remove_incident_ids,
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e: 
        logger.log_err_with_line(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
