# app/celery_app.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Use Filesystem for local dev without infrastructure
# Create directories for filesystem broker/backend
BASE_DIR = os.getcwd()
BROKER_FOLDER = os.path.join(BASE_DIR, ".celery", "broker")
BACKEND_FOLDER = os.path.join(BASE_DIR, ".celery", "results")

os.makedirs(BROKER_FOLDER, exist_ok=True)
os.makedirs(BACKEND_FOLDER, exist_ok=True)

celery = Celery(
    "worker",
    broker=f"filesystem://",
    broker_transport_options={
        "data_folder_in": BROKER_FOLDER,
        "data_folder_out": BROKER_FOLDER,
        "data_folder_processed": BROKER_FOLDER,
    },
    backend=f"file:///{BACKEND_FOLDER}",
)

celery.conf.update(
    task_serializer="pickle",
    accept_content=["pickle", "json"],
    result_serializer="pickle",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Import tasks to register them
from app.Celery import image_tasks

@celery.task
def process_item(item_id):
    # Place your background task logic (e.g., DB, image work) here
    return {"status": "completed", "item_id": item_id}
