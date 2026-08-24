import logging
from os import environ

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StopSetup(BaseModel):
    stop_id: str
    route_filter: str = Field(default="")
    direction_filter: int = Field(default=-1)
    transit_time_min: int
    show_on_display: bool = Field(default=True)


class Config(BaseModel):
    api_url: str
    stops: list[StopSetup]
    alerts_url: str = Field(default="https://api-v3.mbta.com/alerts")
    show_alerts: bool = Field(default=True)


def load_config(path: str | None = None) -> Config:
    config_path = path or environ.get("IMT_CONFIG", "./config.json")
    with open(config_path) as f:
        return Config.model_validate_json(f.read())
