from pydantic import BaseModel
from typing import List, Optional

# Data model for individual Smartsheet events
class SmartsheetEvent(BaseModel):
    objectType: str
    eventType: str
    id: Optional[int] = None
    userId: Optional[int] = None
    sheetId: Optional[int] = None
    rowId: Optional[int] = None
    columnId: Optional[int] = None
    timestamp: str
