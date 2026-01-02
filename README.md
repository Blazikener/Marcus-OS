# FastAPI + Celery + MongoDB (Local Starter)

This project is a powerful web application backend. It is designed to be a "starter kit" that you can run purely on your local machine without needing complex tools like Docker.

## 🌟 What Does This Project Do? (In Simple Terms)

Imagine this application as a restaurant kitchen:

1.  **The Waiter (FastAPI)**: This is the web server. It takes orders (requests) from customers (users). It checks if the order makes sense (validation) and sends it to the kitchen.
2.  **The Kitchen (MongoDB)**: This is the database. It stores all the "recipes" (data) and "prepared dishes" (saved items). We use a special freezer called **GridFS** to store big items like pictures.
3.  **The Short-Term Memory (Cache)**: Often, customers ask for the same thing over and over. Instead of cooking it from scratch every time, we check our "short-term memory" (Cache). If it's there (a **HIT**), we serve it instantly. If not (a **MISS**), we have to cook it.
    - _Note: We use a special "Mock Redis" system so you don't need to install any extra software for this to work!_
4.  **The Background Chef (Celery)**: Sometimes, a dish takes a long time to cook (like "computing" a heavy value). The Waiter doesn't want to keep the customer waiting at the table. So, the Waiter gives the order to the Background Chef and tells the customer, "We started working on it, here is your ticket number (Task ID)." The Chef cooks it in the background, and when it's done, puts it in the Cache.

## 🚀 Features

- **Web API (FastAPI)**: Fast and modern Python web framework.
- **Database (MongoDB)**: Stores flexible data (like our Test Cases).
- **Image Storage (GridFS)**: specialized storage for image files.
- **Background Tasks (Celery)**: Runs heavy jobs in the background so the website stays fast.
- **No-Install Cache (MockRedis)**: A custom system that acts like a professional Redis cache but saves to a simple local file (`local_cache.json`).
- **Test Case Schema**: Designed to store test steps, expected results, and types.

## 📂 Project Structure

```
.
├── app
│   ├── Celery
│   │   ├── Celery_worker.py  # Configures the Background Chef
│   │   └── image_tasks.py    # The recipes (code) the Chef cooks
│   ├── core
│   │   └── db.py             # Database connection logic
│   ├── crud
│   │   └── crud_items.py     # Functions to Create, Read, Update data
│   ├── models
│   │   └── schemas.py        # Defines what our data looks like (Validation)
│   ├── routers
│   │   └── items.py          # The Waiter (API Endpoints)
│   ├── utils
│   │   └── mock_redis.py     # Our local caching tool
│   └── main.py               # The entry point that starts the app
├── requirements.txt          # List of Python ingredients needed
├── verify_cache.py           # A script to test if everything is working
└── local_cache.json          # File where cache data is stored
```

## 🛠️ How to Run (Step-by-Step)

You will need **two separate terminal windows** open.

### 1. Install Ingredients (Dependencies)

First, make sure you have all the necessary Python libraries installed.

```bash
pip install -r requirements.txt
```

### 2. Start the Background Chef (Celery Worker)

In your **first terminal**, run this command. This wakes up the chef who will listen for new cooking orders.

```bash
celery -A app.Celery.Celery_worker.celery worker --loglevel=info -P solo
```

_Note: We use `-P solo` which works best on Windows._

### 3. Start the Waiter (FastAPI Server)

In your **second terminal**, run this command. This opens the restaurant doors.

```bash
uvicorn app.main:app --reload
```

The app is now running at `http://127.0.0.1:8000`.

## 🧪 How to Test

### Using the Interactive UI (Swagger)

Go to **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** in your browser. This is a magical page that lets you press buttons to send requests without writing code.

#### 1. Test the Cache Flow

1.  **Check Cache (`GET /items/cache/{key}`)**: Type a key like `demo`. It will say **MISS** because it's new.
2.  **Order Computation (`POST /items/cache/compute/{key}`)**: Type the same key `demo` and a value `MyResult`. This sends the order to the Chef (Celery).
3.  **Wait**: Count to 5 seconds.
4.  **Check Cache Again**: usage `GET /cache/demo` again. Now it will say **HIT** and show `MyResult`!

### Using the Script

We also made a script that does all the above automatically:

```bash
python verify_cache.py
```

## 📝 API Endpoints Summary

### Items (Test Cases)

- `POST /items/`: Create a new Item (Test Case).
  - **Fields**: `title`, `description`, `type` (positive/negative), `expected_result`, `steps` (JSON list), and an optional `image`.

### Caching

- `GET /items/cache/{key}`: Check if a value exists in our short-term memory.
- `POST /items/cache/compute/{key}`: Ask the background worker to compute and save a value.
