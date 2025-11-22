from celery import Celery

celery = Celery(
    "worker",
    broker="amqp://guest:guest@localhost:5672//",  # RabbitMQ URL
    backend="rpc://"  # For result tracking, or use MongoDB/Redis
)

@celery.task
def process_item(item_id):
    # Place your background task logic (e.g., DB, image work) here
    return {"status": "completed", "item_id": item_id}
