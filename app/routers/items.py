# app/routers/items.py
# mainly for createing the basic fast api endpoints for file modularity its been shifter to items.py

# app/routers/items.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from typing import Optional
from app.core.db import get_db_dep, get_gridfs_bucket
from app.models.schemas import ItemIn, ItemOut
from app.crud.crud_items import Create_item, save_image, get_latest_image_meta, open_image_stream, update_item_fields
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from app.Celery.image_tasks import process_image
import json
from typing import List
from app.utils.pdf_handler import parse_pdf_test_cases
from app.utils.cache_manager import cache_manager
from app.crud.crud_items import Get_item

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=ItemOut)
async def create_item_endpoint(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    expected_result: Optional[str] = Form(None),
    steps: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dep),
    fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_bucket),
):
    """
    The `create_item_endpoint` function in Python handles the creation of items with optional title,
    description, metadata, and image upload, saving the image to a database and returning the saved
    item.
    
    :param title: The `title` parameter in the `create_item_endpoint` function represents the title of
    the item being created. It is a required parameter and is expected to be a string
    :type title: str
    :param description: The `description` parameter in the `create_item_endpoint` function is a string
    that represents the description of an item. It is an optional parameter, meaning it can be provided
    but is not required. If provided, it will be included in the JSON document that is created for the
    item data
    :type description: Optional[str]
    :param metadata: The `metadata` parameter in the `create_item_endpoint` function is an optional
    field that allows the user to provide additional information about the item being created. This
    information is expected to be in JSON format. If provided, the function attempts to parse the
    metadata string into a JSON object. If parsing fails
    :type metadata: Optional[str]
    :param image: The `image` parameter in the `create_item_endpoint` function is of type `UploadFile`,
    which is used to handle file uploads in FastAPI. When a file is uploaded through this parameter, it
    can be accessed as an `UploadFile` object containing information such as the file contents, filename
    :type image: Optional[UploadFile]
    :param db: The `db` parameter in the `create_item_endpoint` function is of type
    `AsyncIOMotorDatabase` and is obtained as a dependency using the `getdb` function. This parameter
    represents the connection to the MongoDB database that will be used to store the item data
    :type db: AsyncIOMotorDatabase
    :param fs: The `fs` parameter in the `create_item_endpoint` function is an instance of
    `AsyncIOMotorGridFSBucket`. It is used to interact with a GridFS bucket in a MongoDB database
    asynchronously. GridFS is a specification for storing and retrieving large files in MongoDB
    :type fs: AsyncIOMotorGridFSBucket
    :return: The `create_item_endpoint` function is returning an `ItemOut` object created from the data
    saved in the database after creating a new item. The `ItemOut` object likely contains information
    about the newly created item, such as its title, description, metadata, and image ID.
    """
    # build json document
    item_data = {
        "title": title,
        "description": description,
        "type": type,
        "expected_result": expected_result,
        # "steps": steps, # handled below
    }
    
    if steps:
        try:
           item_data["steps"] = json.loads(steps)
        except Exception:
             # Fallback: treat as a single step string or raw value
             item_data["steps"] = [steps]
             
    if metadata:
        try:
            item_data["metadata"] = json.loads(metadata)
        except Exception:
            item_data["metadata"] = {"raw": metadata}

    # save image first (if present)
    image_id = None
    if image:
        contents = await image.read()
        if image.content_type not in ("image/jpeg", "image/jpg"):
            raise HTTPException(status_code=400, detail="Only JPEG images allowed")
        image_id = await save_image(fs, contents, image.filename, image.content_type)
        item_data["image_id"] = image_id

    # create DB document (ensure Create_item in crud sets created_at)
    saved = await Create_item(db, item_data)

    # enqueue Celery task (fire-and-forget)
    try:
        async_result = process_image.delay(saved["id"])
        # store task id and status optionally
        if async_result and async_result.id:
            task_id = async_result.id
            status = "queued"
            await update_item_fields(db, saved["id"], {"task_id": task_id, "processing_status": status})
            # Sync local dict for immediate caching
            saved["task_id"] = task_id
            saved["processing_status"] = status
    except Exception as e:
        # log enqueue error but don't fail the request
        print("Failed to enqueue image processing task:", e)

    # Initial cache (will be invalidated later by Celery task completion)
    cache_manager.set_item(saved["id"], saved)

    return ItemOut(**saved)


# @router.get("/latest-image-stream")
# async def latest_image_stream(db: AsyncIOMotorDatabase = Depends(get_db_dep), fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_bucket)):
#     
#     """
#     The function `latest_image_stream` retrieves the latest image from a MongoDB database and streams it
#     as a response with the appropriate content type.
#     
#     :param db: The `db` parameter is an instance of `AsyncIOMotorDatabase`, which is used to interact
#     with a MongoDB database asynchronously. It is typically used for executing database operations like
#     querying, inserting, updating, and deleting data in a non-blocking manner. In this case, it is being
#     used to
#     :type db: AsyncIOMotorDatabase
#     :param fs: The `fs` parameter in the function `latest_image_stream` is an instance of
#     `AsyncIOMotorGridFSBucket`, which is used for interacting with a GridFS bucket in MongoDB. It allows
#     you to perform operations like uploading, downloading, and deleting files in a GridFS bucket
#     asynchronously
#     :type fs: AsyncIOMotorGridFSBucket
#     :return: A StreamingResponse object is being returned, which streams the content of the latest image
#     file stored in the MongoDB GridFS bucket. The media type of the content is determined based on the
#     metadata of the image file, defaulting to "image/jpeg" if not specified.
#     """
#     latest = await get_latest_image_meta(db)
#     if not latest:
#         return Response(status_code=404, content=b"No JPEG found")
# 
#     file_id = str(latest["_id"])
#     content_type = latest.get("metadata", {}).get("contentType", "image/jpeg")
#     generator = open_image_stream(fs, file_id)
#     return StreamingResponse(generator, media_type=content_type)



# Redis Cache Testing Endpoints
from app.utils.mock_redis import MockRedis
from app.Celery.image_tasks import cache_task

@router.get("/cache/{key}")
async def get_cache(key: str):
    # Connect to Mock Redis directory
    r = MockRedis.from_url("local")
    value = r.get(key)
    if value:
        return {"key": key, "value": value.decode("utf-8"), "status": "HIT"}
    return {"key": key, "value": None, "status": "MISS", "message": "Use POST /items/cache/compute/{key} to calculate value."}

@router.post("/cache/compute/{key}")
async def compute_cache(key: str, value: str = Form(...)):
    # Trigger Celery task
    task = cache_task.delay(key, value)
    return {"key": key, "task_id": task.id, "status": "Processing triggered"}

@router.post("/upload-pdf", response_model=List[ItemOut])
async def upload_pdf_endpoint(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dep)
):
    """
    Upload a PDF file containing test cases in JSON-like blocks.
    The parser will extract the test cases, classify them, and save them to the database.
    """
    if file.content_type != "application/pdf" and not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    try:
        contents = await file.read()
        test_cases = parse_pdf_test_cases(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")
        
    if not test_cases:
        raise HTTPException(status_code=404, detail="No valid test cases found in PDF")
        
    saved_items = []
    for case in test_cases:
        # Each case is already classified by parse_pdf_test_cases
        saved = await Create_item(db, case)
        cache_manager.set_item(saved["id"], saved)
        saved_items.append(ItemOut(**saved))
        
    return saved_items

@router.get("/{item_id}", response_model=ItemOut)
async def get_item_endpoint(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dep)
):
    """
    Get an item by ID. 
    First checks the cache, then falls back to the database.
    """
    # Try cache first
    cached_item = cache_manager.get_item(item_id)
    if cached_item:
        print(f"Cache HIT for item {item_id}")
        return ItemOut(**cached_item)
    
    print(f"Cache MISS for item {item_id}")
    # Fallback to DB
    item = await Get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Store in cache for next time
    cache_manager.set_item(item_id, item)
    return ItemOut(**item)