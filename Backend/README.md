# FastAPI + Celery + MongoDB (Local Starter)

This project is a powerful web application backend. It is designed to be a "starter kit" that you can run purely on your local machine without needing complex tools like Docker.

## 🌟 What Does This Project Do? (In Simple Terms)

Imagine this application as a restaurant kitchen:

1.  **The Waiter (FastAPI)**: This is the web server. It takes orders (requests) from customers (users). It checks if the order makes sense (validation) and sends it to the kitchen.
2.  **The Kitchen (MongoDB)**: This is the database. It stores all the "recipes" (data) and "prepared dishes" (saved items). We use a special freezer called **GridFS** to store big items like pictures.
3.  **The Smart Cache**: To keep everything lightning fast, we use a "Cache-Aside" pattern. When you ask for a test case by its ID, we first check our local memory (MockRedis). If it's there (**HIT**), you get it instantly. If not (**MISS**), we pull it from the database and save it in memory for the next person.

    - _Synchronization_: When a new item is created or uploaded via PDF, it's instantly seeded into the cache. If a background worker updates the item (like adding a thumbnail), it automatically clears the old cache to ensure you never see stale data.

4.  **The PDF Inspector**: You can now upload large PDF files filled with test cases. Our parser automatically scans the text, extracts the structured data, and even "guesses" if a test case is positive or negative based on the language used.

## 🚀 Features

- **Web API (FastAPI)**: Fast and modern Python web framework.
- **PDF Parser & Classifier**: Automatically extracts test cases from PDFs and classifies them as "positive" or "negative" using smart heuristics.
- **Smart Caching (MockRedis)**: A custom system that acts like a professional Redis cache but saves to a local file (`local_cache.json`).
- **Background Tasks (Celery)**: Handles image processing and thumbnail generation without slowing down the user.
- **Image Storage (GridFS)**: Specialized storage for high-quality images and their thumbnails.
- **Database (MongoDB)**: Stores flexible data (like our Test Cases).

## 📂 Project Structure

```
.
├── app
│   ├── Celery
│   │   ├── Celery_worker.py  # Configures the Background Chef
│   │   └── image_tasks.py    # Background tasks & cache invalidation logic
│   ├── core
│   │   └── db.py             # Database connection logic
│   ├── crud
│   │   └── crud_items.py     # Functions to Create, Read, Update data
│   ├── models
│   │   └── schemas.py        # Data models for Test Cases
│   ├── routers
│   │   └── items.py          # API Endpoints (Creation, PDF Upload, Cached GET)
│   ├── utils
│   │   ├── pdf_handler.py    # PDF Extraction & Heuristic Classification
│   │   ├── cache_manager.py  # Centralized logic for caching Items
│   │   └── mock_redis.py     # Local file-based caching tool
│   └── main.py               # The entry point that starts the app
├── requirements.txt          # Project dependencies (includes pypdf)
├── verify_cache.py           # A script to test if everything is working
└── local_cache.json          # Persistent file for cache storage
```

## 🛠️ How to Run

1.  **Install Dependencies**: `pip install -r requirements.txt`
2.  **Start Celery Worker**: `celery -A app.Celery.Celery_worker.celery worker --loglevel=info -P solo`
3.  **Start FastAPI**: `uvicorn app.main:app --reload`

## 🧪 Testing the New Workflow

### 1. PDF Upload & Auto-Classification

1.  Go to `/docs`.
2.  Use the `POST /items/upload-pdf` endpoint.
3.  Upload a PDF containing text like: `{"title": "Check Login", "steps": ["Open page", "Enter user"]}`.
4.  The system will extract the block, classify it as **positive**, and return the saved item with a new ID.

### 2. Verified Caching Flow

1.  **Get Item by ID (`GET /items/{id}`)**: Use the ID from the previous step.
2.  **Observe Logs**:
    - The first time, your terminal will show `Cache MISS` (if not already seeded).
    - The second time, it will show `Cache HIT`, and the response will be significantly faster.
3.  **Automatic Invalidation**: If you upload an image, the background worker will update the item and automatically clear the cache, ensuring the next `GET` request shows the latest data.

## 📝 API Endpoints Summary

### Test Items

- `POST /items/`: Create a single test case manually (with optional image).
- `POST /items/upload-pdf`: Bulk import test cases from a PDF file.
- `GET /items/{item_id}`: Retrieve a test case (Uses **Smart Cache**).

### Legacy/Internal (Optional)

- `GET /items/cache/{key}`: Direct access to raw cache keys.
- `POST /items/cache/compute/{key}`: Trigger a manual background computation task.
