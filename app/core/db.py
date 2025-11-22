import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_NAME", "ZEKA")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None
fs_bucket: AsyncIOMotorGridFSBucket | None = None


# The function `getclient` returns an AsyncIOMotorClient instance, creating it if it doesn't already
# exist.
# :return: The `getclient` function is returning the `client` object, which is an instance of
# `AsyncIOMotorClient`.


def getclient() -> AsyncIOMotorClient:
    global client
    if client is None:
        if not MONGO_URI:
            raise RuntimeError("MONGODB_URI not set")
        client = AsyncIOMotorClient(MONGO_URI)
    return client


# The function `getdb` returns a reference to a MongoDB database using an asynchronous motor client.
# :return: The function `getdb()` is returning the MongoDB database instance `db`. If `db` is not yet
# initialized, it will be set to the MongoDB client's database specified by the `MONGO_DB` constant
# before being returned.


def getdb() -> AsyncIOMotorDatabase:
    global db
    if db is None:
        db = getclient()[MONGO_DB]
    return db


# The function `get_gridfs_bucket` returns an instance of `AsyncIOMotorGridFSBucket` using a global
# variable `fs_bucket` if it is not already initialized.
# :return: The `get_db_dep()` function is returning an asynchronous generator that yields the result
# of calling the `getdb()` function, which presumably returns an `AsyncIOMotorDatabase` object.

def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:    
    global fs_bucket
    if fs_bucket is None:
        fs_bucket = AsyncIOMotorGridFSBucket(getdb())
    return fs_bucket

async def get_db_dep() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield getdb()
