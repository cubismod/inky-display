import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageColor, ImageDraw, ImageFont
from schedule_event import ScheduleEvent

logger = logging.getLogger("draw")
# offsets & fonts
# 6, 14     bold, 18
# 61, 14    bold, 20
# 6, 63     semi-bold, 16
# 61, 14    bold, 20

# 6, 116    bold, 18
# 61, 116   bold, 20
# 6, 179    semi-bold, 16
# 61, 179   bold, 20

# 6, 220    bold, 18
# 61, 220   bold, 20
# 6, 269    semi-bold, 16
# 61, 269   bold, 20

base_font_info = [
    {"pos": (26, 23), "style": "Bold", "size": 20, "color": "black", "anchor": "mm"},
    {
        "pos": (30, 68),
        "style": "Bold",
        "size": 20,
        "color": "yellow",
        "anchor": "mm",
    },
    {"pos": (223, 79), "style": "Medium", "size": 22, "color": "black", "anchor": "ms"},
    {
        "pos": (223, 33),
        "style": "Bold",
        "size": 22,
        "color": "black",
        "anchor": "ms",
    },
]
y_offsets = [0, 102, 204]
properties = ["route_id", "time_til", "stop", "headsign"]


def create_font(style: str, size: float, icon: bool = False):
    try:
        if icon:
            return ImageFont.truetype("./fonts/fa-solid-900.ttf", size)
        else:
            return ImageFont.truetype(f"./fonts/IBMPlexSans-{style}.ttf", size)
    except OSError as err:
        logger.error("unable to load font", exc_info=err)
        return None


def truncate_text(schedule_event: ScheduleEvent):
    match schedule_event.route_id:
        case "Red":
            schedule_event.route_id = "RL"
        case "Orange":
            schedule_event.route_id = "OL"
        case "Blue":
            schedule_event.route_id = "BL"
    if schedule_event.route_id.startswith("CR"):
        schedule_event.route_id = "CR"
    if schedule_event.route_id.startswith("Green"):
        schedule_event.route_id = "GL"
    schedule_event.route_id = schedule_event.route_id[:3]
    schedule_event.headsign = schedule_event.headsign[:18]
    schedule_event.stop = schedule_event.stop[:26]
    # subtract a minute since it will take close to that for the display to draw
    schedule_event.time_til = f"{round((schedule_event.time.timestamp() - datetime.now().astimezone(UTC).timestamp()) / 60) - 1}m"


def add_text(
    layer: ImageDraw,
    pos: tuple[float, float],
    style: str,
    size: float,
    font: ImageFont,
    color: str,
    text: str,
    anchor: str = "la",
):
    layer.text(
        xy=pos,
        font=font,
        fill=ImageColor.getrgb(color),
        text=text,
        anchor=anchor,
    )


def get_icon(event: ScheduleEvent):
    match event.route_type:
        case 0:
            return "\ue5b4"  # tram
        case 1:
            return "\uf239"  # subway
        case 2:
            return "\uf238"  # train
        case 3:
            return "\uf55e"  # bus-simple
        case 4:
            return "\ue4ea"  # ferry


def generate_image(image: Image, events: list[ScheduleEvent]):
    txt = Image.new("RGBA", image.size, (255, 255, 255, 0))
    txt_layer = ImageDraw.Draw(txt)

    for i, event in enumerate(events):
        truncate_text(event)
        vehicle_icon_x = 75
        vehicle_icon_y = 25 + y_offsets[i]
        add_text(
            txt_layer,
            (vehicle_icon_x, vehicle_icon_y),
            "bold",
            32,
            create_font(style="thin", size=32, icon=True),
            "yellow",
            get_icon(event),
            "mm",
        )
        if event.id.startswith("prediction"):
            live_icon_x = 378
            live_icon_y = 70 + y_offsets[i]

            add_text(
                txt_layer,
                (live_icon_x, live_icon_y),
                "bold",
                30,
                create_font(style="thin", size=30, icon=True),
                "yellow",
                "\uf09e",  # rss
                "mm",
            )
        if event.bikes_allowed:
            bike_icon_x = 375
            bike_icon_y = 24 + y_offsets[i]

            add_text(
                txt_layer,
                (bike_icon_x, bike_icon_y),
                "bold",
                28,
                create_font(style="thin", size=30, icon=True),
                "yellow",
                "\uf206",  # bike
                "mm",
            )
        if event.alerting:
            alert_icon_x = 110
            alert_icon_y = 24 + y_offsets[i]

            add_text(
                txt_layer,
                (alert_icon_x, alert_icon_y),
                "bold",
                32,
                create_font(style="bold", size=32, icon=True),
                "yellow",
                "\uf06a",  # circle-exclamation
                "mm",
            )
        # display time in bottom corner
        now = datetime.now().astimezone(ZoneInfo("US/Eastern")).strftime("%I:%M %p")
        add_text(
            txt_layer,
            (27, 295),
            "Regular",
            11,
            create_font(style="Regular", size=11),
            "yellow",
            now,
            "mb",
        )
        for j, _ in enumerate(base_font_info):
            offset = y_offsets[i]
            x = base_font_info[j]["pos"][0]
            y = base_font_info[j]["pos"][1] + offset
            style = base_font_info[j]["style"]
            size = base_font_info[j]["size"]
            prop = properties[j]
            body = event.model_dump()[prop]
            add_text(
                txt_layer,
                (x, y),
                style,
                size,
                create_font(style=style, size=size),
                base_font_info[j]["color"],
                body,
                base_font_info[j]["anchor"],
            )

    return Image.alpha_composite(image, txt)
