import fastapi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
# from urllib.parse import quote_plus
import os

from dotenv import load_dotenv
load_dotenv()


uri=os.getenv("MONGO_URI")

# username = quote_plus("admin")
# password = quote_plus("Vinay@0905")

# uri = f"mongodb+srv://{username}:{password}@zeka.7ijqrc1.mongodb.net/?appName=ZEKA"

# uri=f"mongodb+srv://vinay:vinay0905@zeka.7ijqrc1.mongodb.net/?appName=ZEKA"

app=fastapi.FastAPI()


# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)



