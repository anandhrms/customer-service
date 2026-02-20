import asyncio
import json

import firebase_admin
from firebase_admin import credentials, firestore, messaging
from google.cloud.firestore import Client
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.watch import Watch

from app.library.entity_service import entity
from core.library import logger


class FireBaseHandler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FireBaseHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, file_path: str):
        if not hasattr(self, "_initialized"):
            cred = credentials.Certificate(file_path)
            self.app = firebase_admin.initialize_app(credential=cred)
            self._initialized = True

    def firestore_client(self) -> Client:
        client = firestore.client(self.app)
        return client

    async def send_fcm_notification(
        self,
        tokens: list,
        data: dict,
        incident_id: int | None,
        notification_img: str | None,
        analytics_label: str,
        alert: bool,
        channel_id: str | None,
        sound_name: str | None,
    ):
        payload = {}
        params = {}
        title = data.get("title")
        body = data.get("body")

        if incident_id:
            payload["initialPageName"] = "IncidentDetails"
            params["inciID"] = incident_id

        else:
            payload["initialPageName"] = "CameraScreen"

        if channel_id:
            payload["channel_id"] = channel_id

        if sound_name:
            payload["sound"] = sound_name

        payload["parameterData"] = json.dumps(params)
        payload["imageurl"] = notification_img

        if alert:
            headers = {"apns-priority": "10"}
            priority = "high"

        else:
            headers = {"apns-priority": "5"}
            priority = "normal"

        fcm_tokens = [token.get("token") for token in tokens]
        messages = messaging.MulticastMessage(
            tokens=fcm_tokens,
            data=payload,
            notification=messaging.Notification(
                title=title,
                body=body,
                image=notification_img,
            ),
            apns=messaging.APNSConfig(
                headers=headers,
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        sound=messaging.CriticalSound(
                            name=f"{sound_name}.caf", critical=True, volume=1
                        ),
                        content_available=1,
                        badge=1,
                    )
                ),
                fcm_options=messaging.APNSFCMOptions(
                    analytics_label=analytics_label,
                ),
            ),
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound=sound_name,
                    channel_id=channel_id,
                ),
                priority=priority,
                fcm_options=messaging.AndroidFCMOptions(
                    analytics_label=analytics_label,
                ),
            ),
        )
        try:
            response = await messaging.send_each_for_multicast_async(messages)

            for i, res in enumerate(response.responses):
                if res.success:
                    continue

                token = messages.tokens[i]

                error = res.exception
                error_message = str(error)

                if (
                    isinstance(error, messaging.UnregisteredError)
                    or "Requested entity was not found" in error_message
                    or "token is not a valid FCM registration token" in error_message
                ):
                    logger.info(f"FCM token {token} is invalid. Deleting the token...")
                    asyncio.create_task(entity.delete_fcm_token(token))

        except Exception as e:
            logger.error(
                f"Error in sending push notification for incident_id {incident_id}: {str(e)}"
            )


class FireStoreHandler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FireStoreHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, client: Client):
        if not hasattr(self, "_initialized"):
            self.firestore_db = client
            self._initialized = True

    def on_snapshot(self, col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == "ADDED":
                pass
            elif change.type.name == "MODIFIED":
                pass
            elif change.type.name == "REMOVED":
                pass

        for doc in col_snapshot:
            pass

    def start_listener(self, collection: str) -> Watch:
        collection_ref = self.firestore_db.collection(collection)
        listener = collection_ref.on_snapshot(self.on_snapshot)
        return listener

    def stop_listener(self, listener: Watch):
        listener.unsubscribe()

    def get_all_documents_from_collection(self, collection: str) -> list[dict]:
        documents = []

        docs = self.firestore_db.collection(collection).stream()
        for doc in docs:
            documents.append({doc.id: doc.to_dict()})

        return documents

    def get_document_reference(
        self, collection: str, document: str
    ) -> DocumentReference:
        return self.firestore_db.collection(collection).document(document)

    def get_document_contents(self, collection: str, document: str) -> dict | None:
        document_reference = self.get_document_reference(collection, document)
        doc_content = document_reference.get()

        if doc_content.exists:
            return doc_content.to_dict()

        return None

    def get_document_subcollections(self, collection: str, document: str) -> list[dict]:
        document_reference = self.get_document_reference(collection, document)
        collections = document_reference.collections()

        sub_collections = []

        for each_collection in collections:
            sub_doc = []

            for doc in each_collection.stream():
                sub_doc.append({doc.id: doc.to_dict()})

            sub_collections.append({each_collection.id: sub_doc})

        return sub_collections

    def create_document(self, collection: str, data: dict):
        return self.firestore_db.collection(collection).add(data)

    def write_to_document(self, collection: str, document: str, data: dict):
        document_reference = self.get_document_reference(collection, document)
        document_reference.set(data)

    def update_document(self, collection: str, document: str, data: dict):
        document_reference = self.get_document_reference(collection, document)
        document_reference.update(data)

    def delete_document(self, collection: str, document: str):
        document_reference = self.get_document_reference(collection, document)
        document_reference.delete()

    def delete_collection(self, collection: str, batch_size: int):
        if batch_size == 0:
            return

        collection_reference = self.firestore_db.collection(collection)

        docs = collection_reference.list_documents(page_size=batch_size)
        deleted = 0

        for doc in docs:
            doc.delete()
            deleted += 1

        if deleted >= batch_size:
            return self.delete_collection(collection_reference, batch_size)
