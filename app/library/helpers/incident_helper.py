import time
from datetime import datetime
from functools import partial
from uuid import uuid4

import pytz
from google.cloud.firestore_v1.base_query import FieldFilter

from app.controllers.customer_blacklist import Customers_Blacklist_Controller
from app.controllers.customer_data import CustomerDataController
from app.controllers.incidents import IncidentsController
from app.controllers.incidents_audit import IncidentsAuditController
from app.controllers.incidents_blacklist import Incidents_Blacklist_Controller
from app.controllers.test_watchlist import TestWatchlistedController
from app.library.queue_service import AnalystQueueingService
from app.library.telegram_service import TelegramService

# from app.library.entity_service import entity
from app.models import (
    Customers,
    Incidents,
    Incidents_Audit,
    Incidents_Blacklist,
    TestWatchlistedCustomers,
)
from app.repositories.customer_data import CustomerDataRepository
from app.repositories.incidents import IncidentsRepository
from app.repositories.incidents_audit import IncidentsAuditRepository
from app.repositories.incidents_blacklist import Incidents_Blacklist_Repository
from app.repositories.test_watchlist import TestWatchlistedRepository

# from app.schemas.responses import IncidentResponse
from core.cache import Cache

# from core.cache.redis_backend import RedisBackend
from core.config import config
from core.database.session import (
    get_session,
    reset_session_context,
    set_session_context,
)
from core.library.logging import logger
from core.utils.firebase import CloudDBHandler, get_cloudDB_client

from .entity_helper import entity, get_company_branch_camera_id
from .notification_helper import send_notification

TIMEZONE = config.TIMEZONE

BLACKLIST_GROUP = config.BLACKLISTED

ESCAPE_THEFT_TEMPLATE = config.ESCAPE_THEFT_TEMPLATE
THEFT_STOPPED_TEMPLATE = config.THEFT_STOPPED_TEMPLATE

ESCAPE_THEFT_GROUP = config.ESCAPE_THEFT
THEFT_STOPPED_GROUP = config.THEFT_STOPPED

NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON = (
    config.NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON
)
NOTIFICATION_TYPE_PUSH_NOTIFICATION = config.NOTIFICATION_TYPE_PUSH_NOTIFICATION

FIREBASE_BLACKLIST_INCIDENTS_COLLECTION = config.FIREBASE_BLACKLIST_INCIDENTS_COLLECTION

TEST_INCIDENT_DESCRIPTOR = config.TEST_INCIDENT_DESCRIPTOR


incidents_repository = partial(IncidentsRepository, Incidents)
audit_repository = partial(IncidentsAuditRepository, Incidents_Audit)
blacklist_repository = partial(Incidents_Blacklist_Repository, Incidents_Blacklist)
customer_data_repository = partial(CustomerDataRepository, Customers)
test_watchlist_repository = partial(TestWatchlistedRepository, TestWatchlistedCustomers)
cloudDB_handler = CloudDBHandler(get_cloudDB_client())


async def add_to_firebase_blacklist_collection(
    blacklist_id: int,
    blacklist_controller: Incidents_Blacklist_Controller,
    branch_id: str,
    company_id: str,
    customer_id: str,
    related_incident: Incidents | None = None,
):
    try:
        documents = (
            cloudDB_handler.firestore_db.collection(
                FIREBASE_BLACKLIST_INCIDENTS_COLLECTION
            )
            .where(filter=FieldFilter("customer_id", "==", customer_id))
            .where(filter=FieldFilter("company_id", "==", company_id))
            .where(filter=FieldFilter("branch_id", "==", branch_id))
            .get()
        )

        if len(documents) > 0:
            return

        blacklists = await blacklist_controller.get_by_id(blacklist_id, {"customers"})

        if blacklists is None:
            logger.error(f"Blacklisted incident not found: {blacklist_id}")
            return

        blacklist, incident, customers = blacklists

        incident_time = incident.incident_time
        incident_time = incident_time.strftime("%Y-%m-%d %H:%M:%S")

        if related_incident is None:
            prev_incident_time = None
            prev_incident_id = None

        else:
            prev_incident_time = related_incident.incident_time
            prev_incident_time = prev_incident_time.strftime("%Y-%m-%d %H:%M:%S")

            prev_incident_id = related_incident.incident_id

        data = {
            "incident_id": incident.incident_id,
            "incident_time": incident_time,
            "incident_status": incident.status,
            "customer_id": customers.customer_id if customers else None,
            "is_blacklisted": True,
            "incident_url": incident.photo_url,
            "descriptor_1": customers.descriptor_1 if customers else None,
            "descriptor_2": customers.descriptor_2 if customers else None,
            "prev_incident_id": prev_incident_id,
            "prev_incident_time": prev_incident_time,
            "no_of_visits": incident.no_of_visits,
            "branch_id": branch_id,
            "company_id": company_id,
        }

        collection = (
            f"{FIREBASE_BLACKLIST_INCIDENTS_COLLECTION}/{company_id}/{branch_id}"
        )

        cloudDB_handler.write_to_document(
            collection=collection,
            document=incident.incident_id,
            data=data,
        )

    except Exception as e:
        logger.error(f"Error in adding to firebase blacklist collection: {str(e)}")


async def remove_from_firebase_blacklist_collection(
    document_id: str, branch_id: str, company_id: str
):
    try:
        collection = (
            f"{FIREBASE_BLACKLIST_INCIDENTS_COLLECTION}/{company_id}/{branch_id}"
        )
        cloudDB_handler.delete_document(collection=collection, document=document_id)

    except Exception as e:
        logger.info(f"Error in removing from firebase blacklist collection: {str(e)}")


async def add_incident(data: dict):
    start = time.time()
    logger.info(
        f"Processing starts at {datetime.now(pytz.utc)} for incident id {data.get('inci_id')}"
    )

    try:
        session_id = str(uuid4())
        token = set_session_context(session_id)
        async for db_session in get_session():
            incident_controller = IncidentsController(
                incidents_repository=incidents_repository(db_session=db_session),
            )
            blacklist_controller = Incidents_Blacklist_Controller(
                blacklist_repository=blacklist_repository(db_session=db_session),
            )
            customer_controller = CustomerDataController(
                customer_data_repository=customer_data_repository(
                    db_session=db_session
                ),
            )

            test_watchlist_controller = TestWatchlistedController(
                test_watchlist_repository=test_watchlist_repository(
                    db_session=db_session,
                ),
            )

            # audit_controller = IncidentsAuditController(
            #     audit_repository=audit_repository(db_session=db_session),
            # )

            company_branch_camera_response = await get_company_branch_camera_id(
                company_uuid=data.get("com_id"),
                branch_uuid=data.get("st_id"),
                camera_uuid=data.get("cam_id"),
            )

            if company_branch_camera_response is None:
                logger.error("Error in finding company or branch or camera")
                return

            company_id, branch_id, camera_id = company_branch_camera_response

            data["company_id"] = company_id
            data["branch_id"] = branch_id
            data["camera_id"] = camera_id

            customer_id = data.get("cust_id")
            customer_obj = None

            if customer_id is None:
                data["customer_id"] = None

            else:
                customer_obj = await customer_controller.get_by_customer_id(customer_id)

                if customer_obj is None:
                    logger.error(f"No customer exists with this id: {customer_id}")
                    return

                if customer_obj.is_test:
                    data["is_test"] = True

                data["customer_id"] = customer_obj.id

            if data.get("is_blacklisted"):
                related_incident_id = None
                if data.get("prev_inci_id"):
                    related_incident = (
                        await incident_controller.get_incident_by_incident_id(
                            incident_id=data.get("prev_inci_id")
                        )
                    )
                    if related_incident is None:
                        logger.error(
                            f"No incident exists with this previous incident incident_id {data.get('prev_inci_id')}"
                        )
                        return

                    related_incident_id = related_incident.id

                incident = await incident_controller.register(data)
                logger.info(
                    f"time taken for inserting incident with id: {incident.id} is {time.time() - start}"
                )

                incident_id = incident.id

                except_user_ids = None
                if customer_obj is not None:
                    test_customers = await test_watchlist_controller.get_by_customer_id(
                        customer_obj.id
                    )
                    except_user_ids = [
                        test_customer.user_id for test_customer in test_customers
                    ]

                await send_notification(
                    branch_id=branch_id,
                    except_user_ids=except_user_ids,
                    template=config.PREVIOUSLY_BLACKLISTED_TEMPLATE,
                    incident=incident,
                    group=config.PREVIOUSLY_BLACKLISTED,
                    notification_group_type=NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON,
                    alert=True,
                    channel_id=config.NOTIFICATION_CHANNEL_BLACKLIST_ALERT,
                    sound_name=config.NOTIFICATION_SOUND_BLACKLIST_ALERT,
                )

                await blacklist_controller.register(
                    {
                        "incident_id": incident_id,
                        "related_incident_id": related_incident_id,
                        "created_at": datetime.now(pytz.utc),
                    }
                )
                logger.info(
                    f"time taken for inserting blacklisted incident with id: {incident.id} is {time.time() - start}"
                )

                if (
                    config.TELEGRAM_WAS_ON_WATCHLIST_ENABLED == 1
                    and customer_obj
                    and customer_obj.is_test is not True
                ):
                    telegram_service = TelegramService()

                    response = await telegram_service.send_was_on_watchlist_alert(data)

                    if not response.ok:
                        logger.error(
                            f"Error in sending telegram message: {response.status_code} - {response.text}"
                        )

            else:
                incident = await incident_controller.register(data)
                logger.info(
                    f"time taken for inserting incident with id: {incident.id} is {time.time() - start}"
                )

                await send_notification(
                    branch_id=branch_id,
                    template=config.SENSITIVE_ALERT_TEMPLATE,
                    incident=incident,
                    group=config.SENSITIVE,
                    notification_group_type=config.NOTIFICATION_GROUP_TYPE_SENSITIVE_ALERT,
                    channel_id=config.NOTIFICATION_CHANNEL_SENSITIVE_ALERT,
                    sound_name=config.NOTIFICATION_SOUND_SENSITIVE_ALERT,
                )

                if config.QUEUEING_ENABLED and not (
                    config.ENVIRONMENT.lower() == "production"
                    and data.get("branch_id") == config.TEST_STORE_ID
                ):
                    # send incidents to queueing service for analyst portal
                    queue_service = AnalystQueueingService()
                    await queue_service.add_to_incidents_queue(incident.id)

                if config.TELEGRAM_SENSITIVE_ALERT_ENABLED:
                    # send alert in telegram
                    telegram_service = TelegramService()
                    response = await telegram_service.send_sensitive_incidents_alert(
                        data
                    )

            logger.info(
                f"Processing ends at {datetime.now(pytz.utc)} for incident id {data.get('inci_id')}."
                f"Total processing time: {time.time() - start}"
            )

            # redis_backend = RedisBackend()

            # branch_users = await entity.get_branch_users(branch_id=branch_id)

            # for user in branch_users:
            #     user_id = user["id"]
            #     redis_channel = f"channel_{user_id}"
            #     incident_details: IncidentResponse = (
            #         await incident_controller.get_incident_details(
            #             incident_id=incident.id,
            #             audit_controller=audit_controller,
            #             blacklist_controller=blacklist_controller,
            #         )
            #     )

            #     await redis_backend.publish(
            #         channel=redis_channel,
            #         message=incident_details.model_dump_json(),
            #     )

    except Exception as e:
        logger.log_err_with_line(e)
        logger.error(f"Error in adding incident: {str(e)}")

    finally:
        reset_session_context(token)


async def update_incident(data: dict):
    try:
        session_id = str(uuid4())
        token = set_session_context(session_id)
        async for db_session in get_session():
            incident_controller = IncidentsController(
                incidents_repository=incidents_repository(db_session=db_session),
            )
            audit_controller = IncidentsAuditController(
                audit_repository=audit_repository(db_session=db_session),
            )
            blacklist_controller = Incidents_Blacklist_Controller(
                blacklist_repository=blacklist_repository(db_session=db_session),
            )

            incident_status = data.get("status")
            is_blacklisted = data.get("is_blacklisted")
            is_edited = data.get("is_edited")
            audit_comments = data.get("audit_comments")
            incident_id = data.get("inci_id")

            branch_info = await Cache.get_branch_id(data.get("st_id"))
            if branch_info:
                branch_id = branch_info["branch_id"]

            incident = await incident_controller.get_incident_by_incident_id(
                incident_id=incident_id
            )

            if incident is None:
                return

            # status updated from backend
            if incident_status == Incidents.IncidentStatus.NONE and not is_edited:
                return

            # editing comments
            elif (
                incident.status == incident_status
                and incident.is_blacklisted == is_blacklisted
                and audit_comments is not None
            ):
                incident_audits = await audit_controller.get_incident_audit(incident.id)

                if not incident_audits:
                    pass

                for incident_audit in incident_audits:
                    if incident_audit.comments:
                        incident_audit.comments = audit_comments
                        incident_audit.edited = True
                        incident_audit.updated_at = datetime.now(pytz.utc)
                        await db_session.commit()
                        break

            # added to blacklist
            elif (
                is_blacklisted is True
                and incident.is_blacklisted is False
                and audit_comments
            ):
                await add_to_blacklist(data)

            # remove previously blacklisted incident
            elif (
                incident_status == Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED
                and not is_blacklisted
            ):
                incident.status = Incidents.IncidentStatus.NONE
                incident.is_blacklisted = False
                incident.updated_by = data.get("user_id")
                incident.updated_at = datetime.now(pytz.utc)
                await db_session.commit()

                await audit_controller.register(
                    {
                        "incident_id": incident.id,
                        "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                        "status": Incidents_Audit.AuditStatus.REMOVED,
                        "comments": audit_comments,
                        "created_by": data.get("user_id"),
                        "updated_by": data.get("user_id"),
                        "created_at": datetime.now(pytz.utc),
                        "updated_at": datetime.now(pytz.utc),
                    }
                )

                await blacklist_controller.remove_from_blacklist(incident.id)

                await remove_from_firebase_blacklist_collection(
                    document_id=incident.incident_id,
                    branch_id=data.get("st_id"),
                    company_id=data.get("com_id"),
                )

                return incident_id

            # update incident status
            elif incident.status != incident_status:
                if incident_status == Incidents.IncidentStatus.NO_ACTION:
                    audit_comments = None

                incident.status = incident_status
                incident.updated_by = data.get("user_id")
                incident.updated_at = datetime.now(pytz.utc)
                await db_session.commit()

                await audit_controller.register(
                    {
                        "incident_id": incident.id,
                        "action_type": data.get("status"),
                        "status": Incidents_Audit.AuditStatus.ADDED,
                        "comments": audit_comments,
                        "created_by": data.get("user_id"),
                        "updated_by": data.get("user_id"),
                        "created_at": datetime.now(pytz.utc),
                        "updated_at": datetime.now(pytz.utc),
                    }
                )

                if incident_status == Incidents.IncidentStatus.ESCAPE_THEFT:
                    await send_notification(
                        branch_id=branch_id,
                        template=ESCAPE_THEFT_TEMPLATE,
                        incident=incident,
                        group=ESCAPE_THEFT_GROUP,
                        notification_group_type=NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON,
                        except_user_ids=[data.get("user_id")],
                    )

                elif incident_status == Incidents.IncidentStatus.THEFT_STOPPED:
                    await send_notification(
                        branch_id=branch_id,
                        template=THEFT_STOPPED_TEMPLATE,
                        incident=incident,
                        group=THEFT_STOPPED_GROUP,
                        notification_group_type=NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON,
                        except_user_ids=[data.get("user_id")],
                    )

            # removing from blacklist
            elif not is_blacklisted and incident.is_blacklisted:
                incident.is_blacklisted = False
                incident.updated_by = data.get("user_id")
                incident.updated_at = datetime.now(pytz.utc)
                await db_session.commit()

                await audit_controller.register(
                    {
                        "incident_id": incident.id,
                        "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                        "status": Incidents_Audit.AuditStatus.REMOVED,
                        "comments": audit_comments,
                        "created_by": data.get("user_id"),
                        "updated_by": data.get("user_id"),
                        "created_at": datetime.now(pytz.utc),
                        "updated_at": datetime.now(pytz.utc),
                    }
                )

                await blacklist_controller.remove_from_blacklist(incident.id)

                await remove_from_firebase_blacklist_collection(
                    document_id=incident.incident_id,
                    branch_id=data.get("st_id"),
                    company_id=data.get("com_id"),
                )

    except Exception as e:
        logger.error(f"Error in updating incident: {str(e)}")

    finally:
        reset_session_context(token)


async def add_to_blacklist(data: dict):
    try:
        session_id = str(uuid4())
        token = set_session_context(session_id)
        async for db_session in get_session():
            incident_controller = IncidentsController(
                incidents_repository=incidents_repository(db_session=db_session),
            )
            audit_controller = IncidentsAuditController(
                audit_repository=audit_repository(db_session=db_session),
            )
            blacklist_controller = Incidents_Blacklist_Controller(
                blacklist_repository=blacklist_repository(db_session=db_session),
            )
            incident = await incident_controller.get_incident_by_incident_id(
                incident_id=data.get("inci_id")
            )
            incident_status = data.get("status")
            user_id = data.get("user_id")
            audit_comments = data.get("audit_comments")

            branch_info = await Cache.get_branch_id(data.get("st_id"))
            if branch_info:
                branch_id = branch_info["branch_id"]

            if incident.status != incident_status:
                await audit_controller.register(
                    {
                        "incident_id": incident.id,
                        "action_type": incident_status,
                        "status": Incidents_Audit.AuditStatus.ADDED,
                        "comments": audit_comments,
                        "created_by": user_id,
                        "updated_by": user_id,
                        "created_at": datetime.now(pytz.utc),
                        "updated_at": datetime.now(pytz.utc),
                    }
                )
                audit_comments = None

            incident.is_blacklisted = True
            incident.status = incident_status
            incident.updated_by = user_id
            incident.updated_at = datetime.now(pytz.utc)
            await db_session.commit()

            await audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                    "status": Incidents_Audit.AuditStatus.ADDED,
                    "comments": audit_comments,
                    "created_by": user_id,
                    "updated_by": user_id,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                }
            )

            await send_notification(
                branch_id=branch_id,
                template=config.BLACKLIST_TEMPLATE,
                incident=incident,
                group=BLACKLIST_GROUP,
                notification_group_type=NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON,
                except_user_ids=[data.get("user_id")],
            )

            blacklist_obj = await blacklist_controller.register(
                {
                    "incident_id": incident.id,
                    "created_at": datetime.now(pytz.utc),
                }
            )

            await add_to_firebase_blacklist_collection(
                blacklist_id=blacklist_obj.id,
                blacklist_controller=blacklist_controller,
                company_id=data.get("com_id"),
                branch_id=data.get("st_id"),
            )

    except Exception as e:
        logger.error(f"Error in blacklisting: {str(e)}")

    finally:
        reset_session_context(token)


async def get_blacklist_data(
    blacklist_controller: Incidents_Blacklist_Controller
    | Customers_Blacklist_Controller,
    blacklist_id: int,
    incident_obj: bool,
    customer_obj: bool,
) -> dict:
    if incident_obj:
        blacklists = await blacklist_controller.get_by_id(blacklist_id, {"customers"})

        logger.info(blacklists)

        if blacklists is None:
            logger.error(f"Blacklisted incident not found: {blacklist_id}")
            return

        blacklist, incident, customers = blacklists

        incident_time = incident.incident_time
        incident_time = incident_time.strftime("%Y-%m-%d %H:%M:%S")

        if incident.customer_id is None:
            logger.error(
                f"Customer id not selected for incident: {incident.incident_id}"
            )
            return

        customer_id = customers.customer_id
        descriptor_1 = customers.descriptor_1
        descriptor_2 = customers.descriptor_2

        data = {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "incident_time": incident_time,
            "incident_status": incident.status,
            "customer_id": customer_id,
            "customer_int_id": customers.id,
            "is_blacklisted": True,
            "incident_url": incident.photo_url,
            "descriptor_1": descriptor_1,
            "descriptor_2": descriptor_2,
            "no_of_visits": incident.no_of_visits,
            "prev_incident_id": None,
            "prev_incident_time": None,
        }

        branch_id = str(incident.branch_id)
        company_id = str(incident.company_id)

    elif customer_obj:
        blacklists = await blacklist_controller.get_by_id(blacklist_id, {"customers"})

        if blacklists is None:
            logger.error(f"Blacklisted incident not found: {blacklist_id}")
            return

        blacklist, customers = blacklists

        data = {
            "incident_id": None,
            "incident_time": None,
            "incident_status": None,
            "customer_id": customers.customer_id if customers else None,
            "is_blacklisted": True,
            "incident_url": None,
            "descriptor_1": customers.descriptor_1 if customers else None,
            "descriptor_2": customers.descriptor_2 if customers else None,
            "no_of_visits": customers.no_of_visits if customers else None,
            "prev_incident_id": None,
            "prev_incident_time": None,
        }

        branch_id = str(customers.branch_id)
        company_id = str(customers.company_id)

    branches = await Cache.get_all_branches()

    if branches and branch_id in branches:
        branch_uuid = branches[branch_id]

    else:
        branch_uuid = await entity.get_branch_uuid(branch_id)

        if branch_uuid is None:
            logger.error(f"Error in getting branch uuid: {branch_id}")
            return

    companies = await Cache.get_all_companies()

    if companies and company_id in companies:
        company_uuid = companies[company_id]
    else:
        company_uuid = await entity.get_company_uuid(company_id)

        if company_uuid is None:
            logger.error(f"Error in getting company uuid: {company_id}")
            return

    data["branch_id"] = branch_uuid
    data["company_id"] = company_uuid

    return data
