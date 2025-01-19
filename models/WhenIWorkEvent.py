from pydantic import BaseModel
from typing import Dict, Any

# Data model for WhenIWork webhook payload
class WhenIWorkEvent(BaseModel):
    uuid: str
    type: str
    userId: str
    createdAt: str
    sentAt: str
    data: Dict[str, Any]