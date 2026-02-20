import secrets
from datetime import datetime
from uuid import uuid4

import psycopg2
import pytz

from core.config import config
from core.library.logging import logger

visu_customer_analyst_dsn = {
    "dbname": config.ANALYST_DATABASE_NAME,
    "user": config.ANALYST_DATABASE_USER,
    "password": config.ANALYST_DATABASE_PASSWORD,
    "host": config.ANALYST_DATABASE_HOST,
    "port": config.ANALYST_DATABASE_PORT,
}


def create_incident(incident_id: str):
    try:
        conn = psycopg2.connect(**visu_customer_analyst_dsn)
        cur = conn.cursor()

        cashier_id = datetime.now().strftime("%Y%m%d%H%M%S")
        cashier_id = (
            cashier_id + secrets.choice("0123456789") + secrets.choice("0123456789")
        )

        create_incident_query = """
                    INSERT INTO incidents
                    (
                        id, company_id, branch_id, camera_id, name, branchname, companyname,
                        empcode, cashier_id, incident_type, type, subtype, category, sub_category, shift, incident_id,
                        pos_deleted_items_price, pos_currency, device, actionee, incident_time,
                        created_at, video_url, screenshot_url, priority, status, posterminal_id, is_read, analystread,
                        is_valid, pricemismatchstatus, validatorstatus, validatedby, qcstatus, analystrawvideo_url,
                        analystprevvideo_url, analystnextvideo_url, potentialloss_percent, updated_at,
                        pos_reference_info, is_blacklist, probable_customers
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );

            """

        create_incidents_params = (
            uuid4().__str__(),
            config.TEST_COMPANY_ID,
            config.TEST_STORE_ID,
            config.TEST_CAMERA_ID,
            "Customer Event",
            "Test Branch",
            "Test Company",
            "null",
            cashier_id,
            "Product put in Jacket or Pocket",
            "Suspicious Gesture",
            "Suspicious Gesture",
            "Incidents",
            "Suspicious Activity",
            "night",
            incident_id,
            0,
            "pounds",
            "DemoCam",
            "null",
            datetime.now(pytz.utc),
            datetime.now(),
            "6859f044-da0f-4eea-b3d2-8a1ae40370c1_camera2_20250424231729_converted.mp4",
            "6859f044-da0f-4eea-b3d2-8a1ae40370c1_camera2_20250424231729_converted.jpg",
            "high",
            "unresolved",
            2,
            False,
            False,
            None,
            False,
            "Pending",
            None,
            "nil",
            "6859f044-da0f-4eea-b3d2-8a1ae40370c1_camera2_20250424231729_converted.gif",
            "null",
            "null",
            None,
            datetime.now(pytz.utc),
            "null",
            0,
            (
                "['https://customer-cdn.visu.ai/3e6d396d-56af-475c-a02a-82c8d171abff_camera10_2025-04-24_5.jpg',"
                "'https://customer-cdn.visu.ai/3e6d396d-56af-475c-a02a-82c8d171abff_camera10_2025-04-24_7.jpg']"
            ),
        )

        cur.execute(create_incident_query, create_incidents_params)

        conn.commit()

    except Exception as e:
        logger.error(f"Error creating incident: {str(e)}")
        cur.close()
        conn.close()
