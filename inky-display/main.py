import logging
from datetime import datetime, timedelta
from os import environ

from inky.auto import auto
from redis.backoff import ExponentialBackoff
from redis.client import Redis
from redis.exceptions import BusyLoadingError, ConnectionError, TimeoutError
from redis.retry import Retry
from schedule_event import ScheduleEvent
from sortedcontainers import SortedDict

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

    while True:
        json_events = get_redis_items(r)
        for event in json_events:
            if event:
                schedule_event = ScheduleEvent.model_validate_json(event, strict=False)
                # factor in time to leave with departure
                departure = schedule_event.time - timedelta(
                    minutes=schedule_event.travel_time_min
                )
                departures[str(departure.timestamp())] = schedule_event

        selected = select_events(departures)


__main__()
