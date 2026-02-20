from functools import partial
from uuid import uuid4

from google.cloud.firestore_v1.document import DocumentReference

from app.controllers.customer_data import CustomerDataController
from app.models import Customers
from app.repositories.customer_data import CustomerDataRepository
from core.config import config
from core.database.session import (
    get_session,
    reset_session_context,
    set_session_context,
)
from core.library.logging import logger
from core.utils.firebase import CloudDBHandler, get_cloudDB_client

FIREBASE_CUSTOMER_DATA_COLLECTION = config.FIREBASE_CUSTOMER_DATA_COLLECTION

customer_data_repository = partial(CustomerDataRepository, Customers)

cloudDB_handler = CloudDBHandler(get_cloudDB_client())


async def add_customer_data(doc: DocumentReference | dict):
    try:
        if isinstance(doc, DocumentReference):
            data = doc.to_dict()
        elif isinstance(doc, dict):
            data = doc

        session_id = str(uuid4())
        token = set_session_context(session_id)
        async for db_session in get_session():
            customer_data_contoller = CustomerDataController(
                customer_data_repository=customer_data_repository(db_session=db_session)
            )
            customer_id = data.get("cust_id")
            customer_obj = await customer_data_contoller.get_by_customer_id(
                customer_id=customer_id
            )

            if customer_obj is None:
                data["existsInDB"] = True
                customer_response = await customer_data_contoller.register(data)

                if (
                    customer_response is not None
                    and config.ENVIRONMENT == "production"
                    and isinstance(doc, DocumentReference)
                ):
                    cloudDB_handler.update_document(
                        collection=FIREBASE_CUSTOMER_DATA_COLLECTION,
                        document=doc.id,
                        data=data,
                    )

    except Exception as e:
        logger.error(f"Error in adding customer: {str(e)}")

    finally:
        reset_session_context(token)
