import logging
import time
from datetime import datetime, timedelta
from os import environ

from draw import generate_image
from inky.auto import auto
from PIL import Image
from redis.backoff import ExponentialBackoff
from redis.client import Redis
from redis.exceptions import BusyLoadingError, ConnectionError, TimeoutError
from redis.retry import Retry
from schedule_event import ScheduleEvent
from sortedcontainers import SortedDict

from fonts import FontContainer

logging.basicConfig(format="%(levelname)-8s %(message)s")

logger = logging.getLogger(__name__)


def get_redis_items(redis: Redis):
    til = str((datetime.now() + timedelta(hours=1).timestamp()))

    items = redis.zrange(
        "time", str(datetime.now().timestamp()), til, byscore=True, withscores=False
    )

    pipeline = redis.pipeline()
    [pipeline.get(item) for item in items]

    return pipeline.execute(raise_on_error=False)


def select_events(departures: SortedDict[str, ScheduleEvent]):
    now = str(datetime.now().timestamp())
    ret = list[ScheduleEvent]
    for element in departures.irange(minimum=now):
        ret.append(element)
        if len(ret) > 3:
            break
    return ret


def __main__():
    display = auto()

    retry = Retry(ExponentialBackoff(), 3)
    r = Redis(
        host=environ.get("REDIS_HOST"),
        port=environ.get("REDIS_PORT"),
        password=environ.get("REDIS_PASS"),
        retry=retry,
        retry_on_timeout=True,
        retry_on_error=[BusyLoadingError, ConnectionError, TimeoutError],
    )

    departures = SortedDict[str, ScheduleEvent]
    fonts = FontContainer()
    fonts.load()
    sleep_sec = 45

    while True:
        json_events = get_redis_items(r)
        for event in json_events:
            if event:
                schedule_event = ScheduleEvent.model_validate_json(event, strict=False)
                time_to_leave = schedule_event.time - timedelta(
                    minutes=schedule_event.travel_time_min
                )
                departures[str(time_to_leave.timestamp())] = schedule_event

        selected = select_events(departures)
        if len(ScheduleEvent) > 0:
            with Image.open("./backdrop.png").convert("RGBA") as base:
                img = generate_image(base, selected, fonts)
                display.set_image(img)
                display.show()
            sleep_sec = 45
        else:
            sleep_sec = 600

        time.sleep(sleep_sec)


__main__()
