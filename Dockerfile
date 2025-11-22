# Base image
FROM python:3.11-slim

# system deps for Pillow and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user (optional)
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy only requirements first (for caching)
COPY requirements.txt .

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY ./app ./app
COPY .env .env

# Set user
USER appuser

ENV PYTHONUNBUFFERED=1

# Default command is to run uvicorn (overridden in docker-compose for worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
