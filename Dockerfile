# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

# Copy the dependency requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./app /app/app

# Run the application
# Gunicorn is a production-ready WSGI server. We use it to run 4 Uvicorn workers.
# It listens on all network interfaces (0.0.0.0) on port 8000.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
