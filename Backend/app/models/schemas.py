
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# The class `ItemIn` defines a data model with attributes for title, description, and metadata.
class ItemIn(BaseModel):
    title: str
    description: Optional[str] = None
    metadata: Optional[dict] = None
    type: Optional[str] = None
    expected_result: Optional[str] = None
    steps: Optional[list[str]] = None


# The `ItemOut` class extends `ItemIn` and includes additional attributes such as `id`, `image_id`,
# and `created_at`.
class ItemOut(ItemIn):
    id: str  # This will be used for the stringified _id
    item_id: Optional[int] = None  # To preserve any original integer 'id' field
    image_id: Optional[str] = None
    created_at: datetime = Field(..., example="2025-11-21T12:34:56+00:00")
