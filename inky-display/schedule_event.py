from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScheduleEvent(BaseModel):
    time: datetime
    route_id: str
    route_type: Optional[int] = None
    headsign: Optional[str] = None
    stop: Optional[str] = None
    trip_id: Optional[str] = None
    alerting: bool = False
    bikes_allowed: bool = False
    transit_time_min: int = 0
    show_on_display: bool = True
    time_til: Optional[str] = None
