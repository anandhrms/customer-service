import os

from core.config import config
from core.library import logger

from .firebase import FireBaseHandler, FireStoreHandler

FIREBASE_ENV = os.getenv("FIREBASE_ENV", "dev").lower()


if FIREBASE_ENV == "production":
    SERVICE_ACCOUNT_FILE_PATH = config.FIREBASE_CONFIG_FILE_PATH_PROD

elif FIREBASE_ENV == "dev":
    SERVICE_ACCOUNT_FILE_PATH = config.FIREBASE_CONFIG_FILE_PATH_DEV

else:
    logger.error(f"Unknown FIREBASE_ENV value: {FIREBASE_ENV}")


class CloudDBHandler(FireStoreHandler):
    pass


def get_firebase_handler():
    firebase = FireBaseHandler(SERVICE_ACCOUNT_FILE_PATH)
    return firebase


def get_cloudDB_client():
    firebase = get_firebase_handler()
    client = firebase.firestore_client()
    return client
