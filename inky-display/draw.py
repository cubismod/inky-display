from datetime import datetime

from PIL import Image, ImageColor, ImageDraw
from schedule_event import ScheduleEvent

from fonts import FontContainer

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
    {"pos": (223, 79), "style": "Medium", "size": 24, "color": "black", "anchor": "ms"},
    {"pos": (223, 33), "style": "Medium", "size": 24, "color": "black", "anchor": "ms"},
]
y_offsets = [0, 102, 206]
properties = ["route_id", "time_til", "stop", "headsign"]


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
    schedule_event.headsign = schedule_event.headsign[:24]
    schedule_event.stop = schedule_event.stop[:24]
    schedule_event.time_til = (
        f"{round((schedule_event.time.timestamp() - datetime.now().timestamp()) / 60)}m"
    )


def add_text(
    layer: ImageDraw,
    pos: tuple[float, float],
    style: str,
    size: float,
    fonts: FontContainer,
    color: str,
    text: str,
    anchor: str = "la",
):
    layer.text(
        xy=pos,
        font=fonts.retrieve(style=style, size=size),
        fill=ImageColor.getrgb(color),
        text=text,
        anchor=anchor,
    )


def generate_image(image: Image, events: list[ScheduleEvent], fonts: FontContainer):
    txt = Image.new("RGBA", image.size, (255, 255, 255, 0))
    txt_layer = ImageDraw.Draw(txt)

    i = 0
    for event in events:
        truncate_text(event)
        j = 0
        for _ in base_font_info:
            offset = y_offsets[i]
            x = base_font_info[j]["pos"][0]
            y = base_font_info[j]["pos"][1] + offset
            prop = properties[j]
            body = event.model_dump()[prop]
            add_text(
                txt_layer,
                (x, y),
                base_font_info[j]["style"],
                base_font_info[j]["size"],
                fonts,
                base_font_info[j]["color"],
                body,
                base_font_info[j]["anchor"],
            )
            j += 1
        i += 1

    return Image.alpha_composite(image, txt)
