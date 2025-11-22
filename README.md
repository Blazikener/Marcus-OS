# FastAPI Celery MongoDB Starter

This project is a minimal, production-ready starter for a FastAPI application with Celery for background tasks and MongoDB for data storage.

## Features

- FastAPI for the web framework
- Celery for background processing
- MongoDB with `motor` for asynchronous database operations
- GridFS for storing large files like images
- Redis as the Celery broker
- Pydantic for data validation
- Environment variable management with `.env` file

## Project Structure

```
.
├── app
│   ├── __init__.py
│   ├── celery_app.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   └── tasks.py
├── .env.example
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Environment Variables

Copy the `.env.example` file to `.env` and update the values if necessary.

```bash
cp .env.example .env
```

### 3. Run MongoDB and Redis

You can use Docker to easily run MongoDB and Redis:

```bash
docker run -d -p 27017:27017 --name mongodb mongo
docker run -d -p 6379:6379 --name redis redis
```

## Running the Application

### 1. Start the FastAPI Server

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

### 2. Start the Celery Worker

```bash
celery -A app.celery_app.celery worker --loglevel=info
```

## API Endpoints

- `POST /upload`: Uploads a JSON data and a JPEG image.
- `GET /status/{id}`: Retrieves the status of an upload.
