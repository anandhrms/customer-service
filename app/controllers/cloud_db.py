import asyncio
import uuid
from datetime import datetime, timezone

import pytz
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.watch import Watch

from app.controllers.customer_blacklist import Customers_Blacklist_Controller
from app.controllers.incidents_blacklist import Incidents_Blacklist_Controller
from app.library.entity_service import entity
from app.library.helpers import (
    add_camera_incident,
    add_customer_data,
    add_incident,
    get_blacklist_data,
    update_incident,
)
from app.models import Incidents
from core.cache import Cache
from core.config import config
from core.library import logger
from core.utils.firebase import CloudDBHandler

FIREBASE_INCIDENTS_COLLECTION = config.FIREBASE_INCIDENTS_COLLECTION
FIREBASE_CAMERA_COLLECTION = config.FIREBASE_CAMERA_COLLECTION
FIREBASE_BLACKLIST_INCIDENTS_COLLECTION = config.FIREBASE_BLACKLIST_INCIDENTS_COLLECTION
FIREBASE_CUSTOMER_DATA_COLLECTION = config.FIREBASE_CUSTOMER_DATA_COLLECTION

incident_listener_ref = None
camera_listener_ref = None
customer_data_listener_ref = None


TIMEZONE = config.TIMEZONE


class CloudDBController:
    def __init__(self, cloudDB_handler: CloudDBHandler):
        self.cloudDB_handler = cloudDB_handler
        self.event_loop = None

    def create_incident_snapshot_callback(self):
        incident_first_snapshot = True

        def incident_on_snapshot(col_snapshot, changes, read_time):
            nonlocal incident_first_snapshot

            if incident_first_snapshot:
                incident_first_snapshot = False
                return

            try:
                for change in changes:
                    if change.type.name == "ADDED":
                        data = change.document.to_dict()
                        asyncio.run_coroutine_threadsafe(
                            add_incident(data),
                            self.event_loop,
                        )

                    elif change.type.name == "MODIFIED":
                        data = change.document.to_dict()
                        document = asyncio.run_coroutine_threadsafe(
                            update_incident(data),
                            self.event_loop,
                        )

                        document_id = document.result()

                        if document_id:
                            self.cloudDB_handler.update_document(
                                collection=FIREBASE_INCIDENTS_COLLECTION,
                                document=f"inci_id-{document_id}",
                                data={"status": Incidents.IncidentStatus.NONE},
                            )

                    elif change.type.name == "REMOVED":
                        pass

            except Exception as e:
                logger.info(f"Error while processing incident snapshot: {str(e)}")

        return incident_on_snapshot

    def create_camera_snapshot_callback(self):
        camera_first_snapshot = True

        def camera_on_snapshot(col_snapshot, changes, read_time):
            nonlocal camera_first_snapshot

            if camera_first_snapshot:
                camera_first_snapshot = False
                return

            try:
                for change in changes:
                    if change.type.name == "ADDED":
                        data = change.document.to_dict()
                        asyncio.run_coroutine_threadsafe(
                            add_camera_incident(data),
                            self.event_loop,
                        )

                    elif change.type.name == "MODIFIED":
                        pass

                    elif change.type.name == "REMOVED":
                        pass

            except Exception as e:
                logger.info(f"Error while processing camera snapshot: {str(e)}")

        return camera_on_snapshot

    def create_customer_data_snapshot_callback(self):
        customer_data_first_snapshot = True

        def customer_data_on_snapshot(col_snapshot, changes, read_time):
            nonlocal customer_data_first_snapshot

            if customer_data_first_snapshot:
                customer_data_first_snapshot = False
                return

            try:
                for change in changes:
                    if change.type.name == "ADDED":
                        data = change.document.to_dict()
                        data = change.document
                        asyncio.run_coroutine_threadsafe(
                            add_customer_data(data),
                            self.event_loop,
                        )

                    elif change.type.name == "MODIFIED":
                        pass

                    elif change.type.name == "REMOVED":
                        pass

            except Exception as e:
                logger.info(f"Error while processing customer data snapshot: {str(e)}")

        return customer_data_on_snapshot

    async def start_listener(self, collection: str, event_loop) -> Watch:
        global incident_listener_ref, camera_listener_ref, customer_data_listener_ref

        self.event_loop = event_loop
        collection_ref = self.cloudDB_handler.firestore_db.collection(collection)

        if collection == FIREBASE_INCIDENTS_COLLECTION:
            incident_listener_ref = collection_ref.on_snapshot(
                self.create_incident_snapshot_callback(),
            )

        elif collection == FIREBASE_CAMERA_COLLECTION:
            camera_listener_ref = collection_ref.on_snapshot(
                self.create_camera_snapshot_callback()
            )

        elif collection == FIREBASE_CUSTOMER_DATA_COLLECTION:
            collection_ref = collection_ref.where(
                filter=FieldFilter("existsInDB", "==", False)
            )
            customer_data_listener_ref = collection_ref.on_snapshot(
                self.create_customer_data_snapshot_callback(),
            )

    def stop_incident_listener(self):
        global incident_listener_ref
        if incident_listener_ref:
            incident_listener_ref.unsubscribe()
            incident_listener_ref = None
            return {"status": "Incident Listener stopped"}

        return {"status": "No active listeners"}

    def stop_camera_listener(self):
        global camera_listener_ref
        if camera_listener_ref:
            camera_listener_ref.unsubscribe()
            camera_listener_ref = None
            return {"status": "Camera Listener stopped"}

        return {"status": "No active listeners"}

    def stop_customer_data_listener(self):
        global customer_data_listener_ref
        if customer_data_listener_ref:
            customer_data_listener_ref.unsubscribe()
            customer_data_listener_ref = None
            return {"status": "Customer data Listener stopped"}

        return {"status": "No active listeners"}

    def publish_incident(self, incident_request: dict):
        test_company_id = config.TEST_COMPANY_ID
        test_store_id = config.TEST_STORE_ID
        camera_id = config.TEST_CAMERA_ID

        incident_id = uuid.uuid4().__str__()

        if incident_request.get("inci_type") == 1:
            incident_request["status"] = config.BLACKLISTED

            if incident_request.get("previous_incident_id"):
                incident_request["prev_inci_id"] = incident_request.get(
                    "previous_incident_id"
                )

            else:
                incident_request["prev_inci_id"] = config.TEST_PREV_INCI_ID

            if incident_request.get("match_score"):
                incident_request["match_score"] = incident_request.get("match_score")
            else:
                incident_request["match_score"] = 0

            incident_request["cust_id"] = config.TEST_CUSTOMER_ID
            incident_request["is_blacklisted"] = True
            incident_request["user_id"] = None

        else:
            incident_request["status"] = config.STATUS_NONE
            incident_request["prev_inci_id"] = None
            incident_request["is_blacklisted"] = False
            incident_request["user_id"] = None
            incident_request["cust_id"] = None

        incident_request["com_id"] = test_company_id
        incident_request["st_id"] = test_store_id
        incident_request["inci_id"] = incident_id
        incident_request["cam_id"] = camera_id
        incident_request["probable_cust_ids"] = []

        incident_request["pic_url"] = config.TEST_FACE_URL
        incident_request["comments"] = incident_request.get("comments")

        incident_time = datetime.now().astimezone(pytz.timezone(TIMEZONE))
        incident_time = incident_time.strftime("%B %d, %Y %H:%M:%S")

        incident_request["inci_time"] = incident_time
        incident_request["created_at"] = datetime.now(timezone.utc).strftime(
            "%B %d, %Y %I:%M:%S %p UTC%z"
        )
        incident_request["firestore_created_at"] = firestore.SERVER_TIMESTAMP

        self.cloudDB_handler.write_to_document(
            collection=FIREBASE_INCIDENTS_COLLECTION,
            document=f"inci_id-{incident_id}",
            data=incident_request,
        )

        return incident_request

    def publish_camera_incident(self, camera_incident_request: dict):
        test_store_id = config.TEST_STORE_ID
        test_company_id = config.TEST_COMPANY_ID

        incident_time = datetime.now().astimezone(pytz.timezone(TIMEZONE))
        incident_time = incident_time.strftime("%B %d, %Y %H:%M:%S")

        collection_path = "camera_incidents"
        document_id = uuid.uuid4().__str__()

        camera_incident_request["cam_inci_time"] = incident_time
        camera_incident_request["name"] = "Camera Incident"
        camera_incident_request["st_id"] = test_store_id
        camera_incident_request["com_id"] = test_company_id
        camera_incident_request["created_at"] = datetime.now(timezone.utc)
        camera_incident_request["cam_id"] = config.TEST_CAMERA_ID
        camera_incident_request["cam_inci_id"] = uuid.uuid4().__str__()

        self.cloudDB_handler.write_to_document(
            collection=collection_path,
            document=document_id,
            data=camera_incident_request,
        )

        return document_id

    async def add_to_firebase_blacklist_collection(
        self,
        blacklist_controller: Incidents_Blacklist_Controller
        | Customers_Blacklist_Controller,
        blacklist_id: int,
        incident_obj: bool,
        customer_obj: bool,
    ):
        try:
            blacklist_data = await get_blacklist_data(
                blacklist_controller=blacklist_controller,
                blacklist_id=blacklist_id,
                incident_obj=incident_obj,
                customer_obj=customer_obj,
            )

            if blacklist_data.get("incident_id"):
                document = f"incident_{blacklist_data.get('incident_id')}"
            else:
                document = f"incident_{blacklist_data.get('customer_id')}"

            company_uuid = blacklist_data["company_id"]
            branch_uuid = blacklist_data["branch_id"]

            collection = f"{FIREBASE_BLACKLIST_INCIDENTS_COLLECTION}/{company_uuid}/{branch_uuid}"

            self.cloudDB_handler.write_to_document(
                collection=collection,
                document=document,
                data=blacklist_data,
            )

            logger.info(f"Inserted into firebase: {blacklist_data}, {collection}")

        except Exception as e:
            logger.error(str(e))

    async def remove_from_firebase_blacklist_collection(
        self,
        controller,
        id_: int,
        incident_obj: bool,
        customer_obj: bool,
    ):
        try:
            if incident_obj:
                incident_obj = await controller.get_incident_by_id(id_)
                branch_id = str(incident_obj.branch_id)
                company_id = str(incident_obj.company_id)
                document = f"incident_{incident_obj.incident_id}"

            elif customer_obj:
                customer_obj = await controller.get_by_id(id_)
                branch_id = str(customer_obj.branch_id)
                company_id = str(customer_obj.company_id)
                document = f"customer_{customer_obj.customer_id}"

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

            collection = f"{FIREBASE_BLACKLIST_INCIDENTS_COLLECTION}/{company_uuid}/{branch_uuid}"

            self.cloudDB_handler.delete_document(
                collection=collection,
                document=document,
            )

        except Exception as e:
            logger.error(str(e))
