# app/celery_app.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

RABBIT_URI = os.getenv("RABBIT_URI", "amqp://rabbit:rabbit@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

celery = Celery(
    "worker",
    broker=RABBIT_URI,
    backend=CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="pickle",
    accept_content=["pickle", "json"],
    result_serializer="pickle",
    timezone="UTC",
    enable_utc=True,
)
@celery.task
def process_item(item_id):
    # Place your background task logic (e.g., DB, image work) here
    return {"status": "completed", "item_id": item_id}
