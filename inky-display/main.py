import logging
from inky import YELLOW
from inky.auto import auto
from PIL import Image, ImageDraw
from os import environ
from datetime import datetime, timedelta
from redis.backoff import ExponentialBackoff
from sortedcontainers import SortedDict
from redis.retry import Retry
from schedule_event import ScheduleEvent
from redis.client import Redis
from redis.exceptions import (
   BusyLoadingError,
   ConnectionError,
   TimeoutError
)

logging.basicConfig(
    format="%(levelname)-8s %(message)s"
)

logger = logging.getLogger(__name__)


def get_redis_items(redis: Redis):
   til = str((datetime.now() + timedelta.min(60)).timestamp())

   items = redis.zrange('time', str(datetime.now().timestamp()), til, byscore=True, withscores=False)

   pipeline = redis.pipeline()
   [pipeline.get(item) for item in items]

   return pipeline.execute(raise_on_error=False)



def __main__():
    display = auto()

    retry = Retry(ExponentialBackoff(), 3)
    r = Redis(
        host=environ.get("REDIS_HOST"),
        port=environ.get("REDIS_PORT"),
        password=environ.get("REDIS_PASS"),
        retry=retry,
        retry_on_timeout=True,
        retry_on_error=[BusyLoadingError, ConnectionError, TimeoutError]
    )

    departures = SortedDict[str, ScheduleEvent]
    
    while True:
        json_events = get_redis_items(r)
        for event in json_events:
            if event:
                schedule_event = ScheduleEvent.model_validate_json(event, strict=False)
                # factor in travel time to the departure
                departure = 
                departures[str(schedule_event.time.timestamp())] = schedule_event



        


__main__()
