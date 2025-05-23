from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScheduleEvent(BaseModel):
    action: str
    time: datetime
    route_id: str
    route_type: int
    headsign: str
    stop: str
    id: str
    transit_time_min: int
    time_til: Optional[str] = None
    alerting: bool
    bikes_allowed: bool = False
