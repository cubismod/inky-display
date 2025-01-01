import logging
import time
from datetime import UTC, datetime, timedelta
from os import environ
from random import randint

from draw import generate_image
from inky.auto import auto
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from redis.backoff import ExponentialBackoff
from redis.client import Redis
from redis.exceptions import BusyLoadingError, ConnectionError, TimeoutError
from redis.retry import Retry
from schedule_event import ScheduleEvent
from sortedcontainers import SortedDict

logging.basicConfig(format="%(levelname)-8s %(message)s")

logger = logging.getLogger(__name__)


def get_redis_items(redis: Redis):
    til = (datetime.now().astimezone(UTC) + timedelta(hours=1)).timestamp()

    items = redis.zrange(
        "time",
        start=int(datetime.now().astimezone(UTC).timestamp()),
        end=int(til),
        byscore=True,
        withscores=False,
    )

    pipeline = redis.pipeline()
    [pipeline.get(item) for item in items]

    return pipeline.execute(raise_on_error=False)


def select_events(departures: SortedDict[ScheduleEvent]):
    now = str(datetime.now().astimezone(UTC).timestamp())
    ret = list[ScheduleEvent]()
    for k in departures.irange(minimum=now):
        if len(ret) > 2:
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
    sleep_sec = 45

    while True:
        json_events = get_redis_items(r)
        departures = SortedDict[ScheduleEvent]()
        for event in json_events:
            if event:
                try:
                    schedule_event = ScheduleEvent.model_validate_json(
                        event, strict=False
                    )
                    time_to_leave = schedule_event.time - timedelta(
                        minutes=schedule_event.transit_time_min
                    )
                    departures[str(time_to_leave.timestamp())] = schedule_event
                except ValidationError as err:
                    logger.error("unable to load json_event", exc_info=err)

        selected = select_events(departures)
        if len(selected) > 0:
            try:
                with Image.open("./backdrop.png").convert("RGBA") as base:
                    img = generate_image(base, selected)
                    display.set_image(img)
                    display.show()
            except (
                FileNotFoundError | UnidentifiedImageError | ValueError | TypeError
            ) as err:
                logger.error("unable to load backdrop image", exc_info=err)
            sleep_sec = randint(60, 300)
        else:
            sleep_sec = 600
            try:
                with Image.open("./mbta_eepy.png").convert("RGBA") as img:
                    display.set_image(img)
                    display.show()
            except (
                FileNotFoundError | UnidentifiedImageError | ValueError | TypeError
            ) as err:
                logger.error("unable to load backdrop image", exc_info=err)

        time.sleep(sleep_sec)


__main__()
