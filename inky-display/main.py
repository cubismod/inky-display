import asyncio
import logging
from datetime import UTC, datetime, timedelta
from os import environ
from random import randint

import aiohttp
from alerts import fetch_alerts
from async_lru import alru_cache
from config import Config, StopSetup, load_config
from draw import generate_alert_image, generate_image
from inky.auto import auto
from PIL import Image, UnidentifiedImageError
from schedule_event import ScheduleEvent
from sortedcontainers import SortedDict

logging.basicConfig(format="%(levelname)-8s %(message)s")

logger = logging.getLogger(__name__)

DEPARTURES_PATH = "/predictions/departures"
STOP_PATH = "/stop"
QUERY_LIMIT = 10
ALERT_CHECK_INTERVAL = 60 * 60


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
        time_to_leave = datetime.fromisoformat(event_time) - timedelta(
            minutes=stop.transit_time_min
        )
        if time_to_leave < datetime.now().astimezone(UTC):
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
    trip_ids = list[str]()
    for k in departures.irange(minimum=now):
        item = departures[k]
        if item.route_id not in routes and item.trip_id not in trip_ids:
            ret.append(item)
            if item.trip_id:
                trip_ids.append(item.trip_id)
            if item.route_type and item.route_type == 1:
                routes.append(item.route_id)
        if len(ret) > 2:
            break
    return ret


@alru_cache(maxsize=32)
async def get_stop_name(
    session: aiohttp.ClientSession, stop_id: str, api_url: str
) -> str:
    url = f"{api_url.rstrip('/')}{STOP_PATH}"
    try:
        async with session.get(url, params={"id": stop_id}) as response:
            if response.status != 200:
                return stop_id
            data = await response.json()
            return data["stop_id"]
    except (aiohttp.ClientError, TimeoutError) as err:
        logger.error("unable to fetch stop name for %s", stop_id, exc_info=err)
        return stop_id


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
            stop_name = await get_stop_name(session, stop.stop_id, config.api_url)
            event.stop = stop_name
            departures[str(event.time.timestamp())] = event
    return select_events(departures)


async def run() -> None:
    config = load_config()
    text_only = bool(environ.get("MBTA_ALERT_TEXT_ONLY"))
    display = None if text_only else auto()

    show_sleepy = False
    last_alert_check = datetime.now().astimezone(UTC) - timedelta(
        seconds=ALERT_CHECK_INTERVAL
    )

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        while True:
            alert = None
            if config.show_alerts and datetime.now().astimezone(
                UTC
            ) - last_alert_check >= timedelta(seconds=ALERT_CHECK_INTERVAL):
                last_alert_check = datetime.now().astimezone(UTC)
                alert = await fetch_alerts(session, config)

            if alert is not None:
                show_sleepy = False
                if text_only:
                    logger.info("alert: %s", alert.header)
                else:
                    try:
                        with Image.open("./backdrop_alerts.png").convert("RGBA") as base:
                            img = generate_alert_image(base, alert)
                            display.set_image(img)
                            display.show()
                    except (
                        FileNotFoundError
                        | UnidentifiedImageError
                        | ValueError
                        | TypeError
                    ) as err:
                        logger.error("unable to render alert display", exc_info=err)
                await asyncio.sleep(90 + randint(1, 15))
                continue

            if text_only:
                await asyncio.sleep(90 + randint(1, 15))
                continue

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

            await asyncio.sleep(90 + randint(1, 15))


asyncio.run(run())
