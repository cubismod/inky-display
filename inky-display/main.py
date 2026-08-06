import asyncio
import logging
from datetime import UTC, datetime, timedelta
from random import randint

import aiohttp
from config import Config, StopSetup, load_config
from draw import generate_image
from inky.auto import auto
from PIL import Image, UnidentifiedImageError
from schedule_event import ScheduleEvent
from sortedcontainers import SortedDict

logging.basicConfig(format="%(levelname)-8s %(message)s")

logger = logging.getLogger(__name__)

DEPARTURES_PATH = "/predictions/departures"
QUERY_LIMIT = 10


def build_params(stop: StopSetup) -> dict[str, str]:
    params: dict[str, str] = {
        "stop": stop.stop_id,
        "limit": str(QUERY_LIMIT),
    }
    if stop.route_filter:
        params["route"] = stop.route_filter
    if stop.direction_filter >= 0:
        params["direction"] = str(stop.direction_filter)
    return params


def parse_departures(payload: dict, stop: StopSetup) -> list[ScheduleEvent]:
    stop_name = (payload.get("stop") or {}).get("name") or stop.stop_id
    events: list[ScheduleEvent] = []
    for dep in payload.get("departures", []):
        event_time = dep.get("arrival_time") or dep.get("departure_time")
        if not event_time:
            continue
        events.append(
            ScheduleEvent(
                time=event_time,
                route_id=dep.get("route_id", ""),
                route_type=dep.get("route_type"),
                headsign=dep.get("headsign"),
                stop=stop_name,
                trip_id=dep.get("trip_id"),
                alerting=dep.get("alerting", False),
                bikes_allowed=dep.get("bikes_allowed", False),
                transit_time_min=stop.transit_time_min,
                show_on_display=stop.show_on_display,
            )
        )
    return events


def select_events(departures: SortedDict[ScheduleEvent]):
    now = str(datetime.now().astimezone(UTC).timestamp())
    ret = list[ScheduleEvent]()
    routes = list[str]()
    for k in departures.irange(minimum=now):
        item = departures[k]
        if not item.show_on_display:
            continue
        if item.route_id not in routes:
            ret.append(item)
            routes.append(item.route_id)
        if len(ret) > 2:
            break
    return ret


async def refresh(
    session: aiohttp.ClientSession, config: Config
) -> list[ScheduleEvent]:
    departures = SortedDict[ScheduleEvent]()
    for stop in config.stops:
        url = f"{config.api_url.rstrip('/')}{DEPARTURES_PATH}"
        try:
            async with session.get(url, params=build_params(stop)) as response:
                if response.status != 200:
                    logger.error(
                        "departures request failed: %s %s", response.status, url
                    )
                    continue
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            logger.error(
                "unable to fetch departures for %s", stop.stop_id, exc_info=err
            )
            continue
        for event in parse_departures(payload, stop):
            time_to_leave = event.time - timedelta(minutes=event.transit_time_min)
            departures[str(time_to_leave.timestamp())] = event
    return select_events(departures)


async def run() -> None:
    display = auto()
    config = load_config()

    sleep_sec = 45
    show_sleepy = False

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        while True:
            selected = await refresh(session, config)
            if len(selected) > 0:
                show_sleepy = False
                try:
                    with Image.open("./backdrop.png").convert("RGBA") as base:
                        img = generate_image(base, selected)
                        display.set_image(img)
                        display.show()
                except (
                    FileNotFoundError | UnidentifiedImageError | ValueError | TypeError
                ) as err:
                    logger.error("unable to render departure display", exc_info=err)
                sleep_sec = randint(60, 300)
            else:
                if not show_sleepy:
                    show_sleepy = True
                    try:
                        with Image.open("./mbta_eepy.png").convert("RGBA") as img:
                            display.set_image(img)
                            display.show()
                    except (
                        FileNotFoundError
                        | UnidentifiedImageError
                        | ValueError
                        | TypeError
                    ) as err:
                        logger.error("unable to render departure display", exc_info=err)
                sleep_sec = 600

            await asyncio.sleep(sleep_sec)


asyncio.run(run())
