# app/tasks/image_tasks.py
import io
from celery import shared_task
from pymongo import MongoClient
import gridfs
from PIL import Image
from dotenv import load_dotenv
from bson import ObjectId
import os

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGODB_DB", "fastapi_demo")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
fs = gridfs.GridFS(db)

def _make_thumbnail_bytes(image_bytes: bytes, size=(256, 256)) -> bytes:
    im = Image.open(io.BytesIO(image_bytes))
    im = im.convert("RGB")
    im.thumbnail(size)
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=85)
    return out.getvalue()

@shared_task(bind=True, acks_late=True)
def process_image(self, item_id: str):
    try:
        oid = ObjectId(item_id)
    except Exception:
        return {"error": "invalid item_id"}

    # Set processing status
    db.items.update_one({"_id": oid}, {"$set": {"processing_status": "processing"}})

    item = db.items.find_one({"_id": oid})
    if not item:
        db.items.update_one({"_id": oid}, {"$set": {"processing_status": "not_found"}})
        return {"error": "item not found"}

    image_id = item.get("image_id")
    if not image_id:
        db.items.update_one({"_id": oid}, {"$set": {"processing_status": "no_image"}})
        return {"error": "no image"}

    try:
        img_oid = ObjectId(image_id)
        grid_out = fs.get(img_oid)
        image_bytes = grid_out.read()
    except Exception as exc:
        db.items.update_one({"_id": oid}, {"$set": {"processing_status": "read_error"}})
        return {"error": f"gridfs read failed: {exc}"}

    try:
        thumb_bytes = _make_thumbnail_bytes(image_bytes, size=(256, 256))
        thumb_id = fs.put(thumb_bytes, filename=f"thumb_{image_id}.jpg", metadata={"contentType": "image/jpeg"})
    except Exception as exc:
        db.items.update_one({"_id": oid}, {"$set": {"processing_status": "thumb_fail"}})
        return {"error": f"thumbnail creation failed: {exc}"}

    db.items.update_one({"_id": oid}, {"$set": {"thumbnail_id": str(thumb_id), "processing_status": "done"}})
    return {"status": "ok", "thumbnail_id": str(thumb_id)}
