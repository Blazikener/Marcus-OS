# app/crud/crud_items.py

from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo.errors import PyMongoError
from bson import ObjectId



async def Create_item(db:AsyncIOMotorDatabase,item_dict:dict)->dict:
    """
    The `Create_item` function inserts a new item into a MongoDB database collection, ensuring that the
    item has a creation timestamp with timezone information.
    
    :param db: The `db` parameter is an instance of `AsyncIOMotorDatabase`, which is used to interact
    with a MongoDB database asynchronously. It allows you to perform database operations such as
    inserting data, querying data, updating data, and deleting data
    :type db: AsyncIOMotorDatabase
    :param item_dict: The `Create_item` function you provided is an asynchronous function that inserts a
    document into a MongoDB collection using `AsyncIOMotorDatabase`. It takes two parameters:
    :type item_dict: dict
    :return: The `Create_item` function returns a dictionary representing the inserted item in the
    database. The returned dictionary contains the item data with the following modifications:
    - If the item was successfully inserted and found in the database, the returned dictionary will have
    the "_id" field replaced with "id" (converted to a string) and the "created_at" field will have
    timezone information added if it was missing.
    """
    items=dict(item_dict)
    if "created_at" not in items:
        items["created_at"] = datetime.now(timezone.utc)
    
    try:
        res = await db.items.insert_one(items)
    except PyMongoError as e:
        raise RuntimeError(f"DB insert failed: {e}") from e

    inserted = await db.items.find_one({"_id": res.inserted_id})
    if inserted:
        inserted["id"] = str(inserted["_id"])
        inserted.pop("_id", None)
        ca = inserted.get("created_at")
        if isinstance(ca, datetime) and ca.tzinfo is None:
            inserted["created_at"] = ca.replace(tzinfo=timezone.utc)
        item_out = inserted
    else:
        # Use the items dict we inserted and ensure created_at has tzinfo
        ca = items.get("created_at")
        if isinstance(ca, datetime) and ca.tzinfo is None:
            items["created_at"] = ca.replace(tzinfo=timezone.utc)
        item_out = {**items, "id": str(res.inserted_id)}
    
    return item_out





async def Get_item(db:AsyncIOMotorDatabase,item_id:str)->Optional[Dict[str,Any]]:
    """
    The function `Get_item` retrieves an item from a MongoDB database using its ID.
    
    :param db: The `db` parameter is an instance of `AsyncIOMotorDatabase`, which is used to interact
    with a MongoDB database asynchronously. It allows you to perform operations like querying,
    inserting, updating, and deleting data in a non-blocking way. In the provided function `Get_item`,
    the `db
    :type db: AsyncIOMotorDatabase
    :param item_id: The function `Get_item` is an asynchronous function that takes two parameters:
    :type item_id: str
    :return: The function `Get_item` returns an optional dictionary containing information about an item
    from the database. If the item with the specified `item_id` is found in the database, a dictionary
    with the item details is returned. If the item is not found or if there is an exception while trying
    to convert the `item_id` to an `ObjectId`, then `None` is returned.
    """
    try :
         oid=ObjectId(item_id)
    except Exception:
        return  None
    
    doc=await db.items.find_one({"_id":oid})
    if not doc:
        return None
    doc["id"]=str(doc["_id"])
    doc.pop("_id",None)
    return doc
    


async def save_image(fs: AsyncIOMotorGridFSBucket,file_bytes: bytes,filename: str,content_type: str) -> str:
    """
    The function `save_image` asynchronously saves an image file to a MongoDB GridFS bucket and returns
    the file ID.
    
    :parameters fs: AsyncIOMotorGridFSBucket instance for interacting with GridFS in an asynchronous manner
    :type fs: AsyncIOMotorGridFSBucket
    :parameters file_bytes: The `file_bytes` parameter in the `save_image` function represents the actual
    image data in bytes that you want to save to the GridFS bucket. This could be the binary data of an
    image file that you want to store in the database
    :type file_bytes: bytes
    :parameters filename: The `filename` parameter is a string that represents the name of the file you want
    to save in the GridFS bucket
    :type filename: str
    :parameters content_type: The `content_type` parameter in the `save_image` function represents the type
    of content of the image being saved. It specifies the MIME type of the image data, such as
    "image/jpeg", "image/png", etc. This information is important for correctly identifying and handling
    the image data during storage
    :type content_type: str
    :return: The function `save_image` returns a string representation of the `file_id` that is
    generated when the image file is successfully uploaded to the GridFS bucket using the provided
    parameters.
    """
    
    try:
        file_id = await fs.upload_from_stream(filename, file_bytes, metadata={"contentType": content_type})
    except PyMongoError as e:
        raise RuntimeError(f"GridFS upload failed: {e}") from e
    return str(file_id)


#this isnt connectd:-

async def read_image(fs: AsyncIOMotorGridFSBucket, file_id: str) -> bytes:
    """
    This Python async function reads an image file from a MongoDB GridFS bucket using the provided file
    ID.
    
    :param fs: AsyncIOMotorGridFSBucket instance for accessing files stored in MongoDB GridFS
    :type fs: AsyncIOMotorGridFSBucket
    :param file_id: The `file_id` parameter is a string that represents the unique identifier of the
    file stored in the GridFS bucket. It is used to retrieve the file data from the GridFS bucket
    :type file_id: str
    :return: The `read_image` function returns the image data as bytes after reading it from the GridFS
    bucket using the provided file_id.
    """
    
    try:
        oid = ObjectId(file_id)
    except Exception as e:
        raise ValueError("Invalid file_id") from e

    try:
        stream = await fs.open_download_stream(oid)
        data = await stream.read()
    except PyMongoError as e:
        raise RuntimeError(f"GridFS read failed: {e}") from e
    return data




async def get_latest_image_meta(db: AsyncIOMotorDatabase) -> Optional[Dict[str, Any]]:
    """
    The function `get_latest_image_meta` retrieves the metadata of the latest image file (JPEG or JPG)
    from a MongoDB collection.
    
    :param db: AsyncIOMotorDatabase - an asynchronous MongoDB database connection
    :type db: AsyncIOMotorDatabase
    :return: The `get_latest_image_meta` function returns the metadata of the latest image file (JPEG or
    JPG) stored in the MongoDB database collection "fs.files". The metadata of the latest image file is
    retrieved by querying the collection for documents with content type "image/jpeg" or "image/jpg",
    sorted by upload date in descending order. The function returns this metadata as a dictionary, or
    `None`
    """

    files_coll = db["fs.files"]
    latest = await files_coll.find_one(
        {"metadata.contentType": {"$in": ["image/jpeg", "image/jpg"]}},
        sort=[("uploadDate", -1)]
    )
    return latest



async def open_image_stream(fs: AsyncIOMotorGridFSBucket, file_id: str, chunk_size: int = 1024 * 64) -> AsyncGenerator[bytes, None]:
    """
    This Python async function opens an image stream from a MongoDB GridFS bucket and yields image data
    in chunks.
    
    :param fs: AsyncIOMotorGridFSBucket instance - an asynchronous MongoDB GridFS bucket object used for
    file storage and retrieval
    :type fs: AsyncIOMotorGridFSBucket
    :param file_id: The `file_id` parameter is a string that represents the unique identifier of the
    file you want to open for streaming. It is used to retrieve the file from the MongoDB GridFS bucket
    :type file_id: str
    :param chunk_size: The `chunk_size` parameter in the `open_image_stream` function specifies the size
    of each chunk of data that will be read from the image stream. In this case, the default value is
    set to `1024 * 64`, which means each chunk will be 64KB in size
    :type chunk_size: int
    """

    try:
        oid = ObjectId(file_id)
    except Exception as e:
        raise ValueError("Invalid file_id") from e

    # Open download stream
    stream = await fs.open_download_stream(oid)

    # Read in a loop using read() with size hint; motor's stream.read(size) is supported
    try:
        while True:
            chunk = await stream.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        # close the stream explicitly if available
        try:
            await stream.close()
        except Exception:
            pass




async def update_item_fields(db: AsyncIOMotorDatabase, item_id: str, fields: Dict[str, Any]) -> bool:
    try:
        oid = ObjectId(item_id)
    except Exception:
        return False
    res = await db.items.update_one({"_id": oid}, {"$set": fields})
    return res.modified_count > 0