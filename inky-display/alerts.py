import logging
from os import environ

import aiohttp
from config import Config
from pydantic import BaseModel

logger = logging.getLogger(__name__)

ALERTS_PATH = "/alerts"


class AlertEvent(BaseModel):
    header: str
    severity: int = 0
    effect: str | None = None


def build_params(stops: list[str], routes: list[str] | None = None) -> dict[str, str]:
    params: dict[str, str] = {
        "filter[stop]": ",".join(stops),
        "filter[datetime]": "NOW",
        "sort": "-severity",
    }
    if routes:
        params["filter[route]"] = ",".join(routes)
    return params


def api_headers() -> dict[str, str]:
    api_key = environ.get("MBTA_API_KEY")
    if api_key:
        return {"x-api-key": api_key}
    return {}


def parse_alerts(payload: dict) -> list[AlertEvent]:
    alerts: list[AlertEvent] = []
    for alert in payload.get("data", []):
        attributes = alert.get("attributes") or {}
        header = attributes.get("header")
        if not header:
            continue
        alerts.append(
            AlertEvent(
                header=header,
                severity=attributes.get("severity", 0),
                effect=attributes.get("effect"),
            )
        )
    return alerts


async def fetch_alerts(
    session: aiohttp.ClientSession, config: Config
) -> AlertEvent | None:
    stop_ids = [stop.stop_id for stop in config.stops]
    url = f"{config.alerts_url.rstrip('/')}{ALERTS_PATH}"
    alerts: list[AlertEvent] = []
    try:
        async with session.get(
            url, params=build_params(stop_ids), headers=api_headers()
        ) as response:
            if response.status != 200:
                logger.error("alerts request failed: %s %s", response.status, url)
                return None
            payload = await response.json()
        alerts.extend(parse_alerts(payload))
    except (aiohttp.ClientError, TimeoutError) as err:
        logger.error("unable to fetch alerts", exc_info=err)
        return None

    route_ids = [stop.route_filter for stop in config.stops if stop.route_filter]
    if route_ids:
        try:
            async with session.get(
                url,
                params=build_params(stop_ids, routes=route_ids),
                headers=api_headers(),
            ) as response:
                if response.status == 200:
                    alerts.extend(parse_alerts(await response.json()))
        except (aiohttp.ClientError, TimeoutError) as err:
            logger.error("unable to fetch route alerts", exc_info=err)

    if not alerts:
        return None
    return max(alerts, key=lambda alert: alert.severity)
