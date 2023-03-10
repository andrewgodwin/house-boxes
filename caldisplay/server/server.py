import arrow
import datetime
import os
import requests
from icalevents import icalevents
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, send_file, request

app = Flask(__name__)


class Colours:
    BLACK = 0
    DARK_GREY = 31
    GREY = 65
    LIGHT_GREY = 127
    VERY_LIGHT_GREY = 223
    WHITE = 255


@app.route("/generate/")
def generate():
    # Get API key
    api_key = request.args.get("key")
    if os.environ.get("API_KEY"):
        if api_key != os.environ["API_KEY"]:
            return "Invalid API key", 403
    # Get calendar URLs
    calendar_urls = {}
    for entry in os.environ["CALENDARS"].split("|"):
        name, url = entry.split(":", 1)
        calendar_urls[name.strip()] = url.strip()
    # Render
    image = CalendarRenderer(calendar_urls).render()
    # Save PNG
    with open("/tmp/output.png", "wb") as file:
        image.save(file, "PNG")
    # Save raw
    with open("/tmp/output.raw", "wb") as file:
        # Custom 2 pixels per byte mode
        raw_bytes = image.tobytes()
        for i in range(len(raw_bytes) // 2):
            offset = i * 2
            byte1 = raw_bytes[offset] // 16
            byte2 = raw_bytes[offset + 1] // 16
            file.write(bytes([(byte1 << 4) | byte2]))
    if request.args.get("png"):
        return send_file("/tmp/output.png", mimetype="image/png")
    return "OK"


@app.route("/serve/")
def serve():
    # Get API key and PNG mode
    png_mode = request.args.get("png")
    api_key = request.args.get("key")
    if os.environ.get("API_KEY"):
        if api_key != os.environ["API_KEY"]:
            return "Invalid API key", 403
    # Work out which to serve
    file_path = "/tmp/output.png" if png_mode else "/tmp/output.raw"
    if not os.path.exists(file_path):
        return ""
    # Send to client
    return send_file(
        file_path, mimetype="image/png" if png_mode else "application/octet-stream"
    )


class CalendarRenderer:
    def __init__(self, calendar_urls: dict[str, str], timezone="US/Mountain"):
        self.calendar_urls = calendar_urls
        self.size = (1150, 800)
        self.timezone = timezone
        self.now: arrow.Arrow = arrow.utcnow().to(self.timezone)
        self.tomorrow: arrow.Arrow = self.now.shift(days=1).floor("day")
        self.events = []
        for name, url in self.calendar_urls.items():
            print("Downloading " + url)
            data = requests.get(url).text.encode("utf8")
            print("Parsing " + url)
            for event in icalevents.events(
                string_content=data,
                start=self.now.floor("day"),
                end=self.now.shift(days=4),
            ):
                event.source = name
                self.events.append(event)
        self.events.sort(key=lambda e: e.start)
        self.fonts = {}

    def render(self) -> Image.Image:
        # Prepare image
        self.image = Image.new("L", self.size, 0)
        self.draw = ImageDraw.ImageDraw(self.image)
        self.image.paste(255, (0, 0, self.size[0], self.size[1]))
        # Draw the date/time
        dw, _ = self.draw_text(
            (0, 0), self.now.strftime("%A %-d"), Colours.BLACK, ("medium", 50)
        )
        self.draw_text(
            (dw + 3, 4),
            {1: "st", 2: "nd", 3: "rd"}.get(self.now.day, "th"),
            Colours.BLACK,
            ("medium", 25),
        )
        self.draw_text(
            (dw + 38, 19), self.now.strftime("%B %Y"), Colours.GREY, ("medium", 30)
        )
        self.draw_text(
            (1145, 0),
            self.now.strftime("%H:%M"),
            Colours.GREY,
            ("medium", 20),
            align="right",
        )
        # Draw the columns
        self.draw_cal_column(0, 80, "Today", self.now, self.tomorrow)
        self.draw_cal_column(
            400, 80, "Tomorrow", self.tomorrow, self.tomorrow.shift(days=1)
        )
        self.draw_cal_column(
            800,
            80,
            self.tomorrow.shift(days=1).strftime("%A"),
            self.tomorrow.shift(days=1),
            self.tomorrow.shift(days=2),
        )
        return self.image

    def draw_cal_column(
        self, x: int, y: int, title: str, start_time, end_time, width=350
    ):
        self.draw.rounded_rectangle(
            (x, y, x + width, y + 40), 5, fill=Colours.DARK_GREY
        )
        self.draw.rectangle((x, y + 15, x + width, y + 40), fill=Colours.DARK_GREY)
        self.draw_text((x + 10, y + 3), title, Colours.WHITE, ("bold", 30))
        top = y + 50
        last_end: datetime.datetime | None = None
        for event in self.events:
            # Skip events outside the window
            if event.end < start_time or event.start > end_time:
                continue
            # Skip events that were declined
            attendee = event.attendee
            if isinstance(attendee, list):
                for person in attendee:
                    if "godwin" in person.lower():
                        attendee = person
            if (
                hasattr(attendee, "params")
                and attendee.params.get("PARTSTAT", "").lower() == "declined"
            ):
                continue
            # Skip lunch and generic busy events
            if event.summary.lower() in ["busy", "lunch", "out", "ooo"]:
                continue
            # Maybe add a gap indicator
            if last_end:
                gap = event.start - last_end
                if gap.total_seconds() > 300:
                    top = self.draw_cal_gap(
                        x, top, width, self.format_duration(gap) + " gap"
                    )
            # Draw the actual event
            top = self.draw_cal_event(
                x,
                top,
                width,
                self.format_short_time(event.start),
                self.format_duration(event.end - event.start, short=True),
                event.summary,
            )
            last_end = event.end
        # If there were no events, show a placeholder
        if top == y + 40:
            self.draw_cal_gap(x, top + 10, width, "No events")
        # Cheaply clip the right hand side
        self.draw.rectangle((x + width, y, x + 1000, top), fill=Colours.WHITE)

    def draw_cal_event(
        self, x: int, y: int, width: int, time: str, duration: str, title: str
    ) -> int:
        self.draw_text((x, y - 3), time, Colours.BLACK, ("bold", 30))
        self.draw.rounded_rectangle(
            (x + width - 60, y, x + width, y + 30), 3, Colours.GREY
        )
        self.draw_text(
            (x + width - 30, y),
            duration,
            Colours.WHITE,
            ("bold", 23),
            align="centre",
        )
        self.draw_text((x, y + 35), title, Colours.BLACK, ("medium", 26))
        return y + 85

    def draw_cal_gap(self, x: int, y: int, width: int, duration: str) -> int:
        self.draw.rounded_rectangle(
            (x + 20, y, x + width - 20, y + 30), 3, Colours.LIGHT_GREY
        )
        self.draw_text(
            (x + (width / 2), y),
            duration,
            Colours.WHITE,
            ("bold", 23),
            align="centre",
        )
        return y + 45

    def draw_text(self, pos, text, colour, font, align="left") -> tuple[int, int]:
        """
        Draws text and returns its size
        """
        # Remove any emoji
        text = ("".join(c for c in text if ord(c) < 255)).strip()
        # Get font
        if font not in self.fonts:
            self.fonts[font] = ImageFont.truetype(
                "fonts/Raleway-%s.ttf" % font[0].title(), size=font[1]
            )
        # Calculate size
        size = self.draw.textsize(str(text), font=self.fonts[font])
        # Draw
        x, y = pos
        if align == "right":
            x -= size[0]
        elif align.startswith("cent"):
            x -= size[0] / 2
        self.draw.multiline_text((x, y), str(text), fill=colour, font=self.fonts[font])
        return size

    def format_short_time(self, time: datetime.datetime) -> str:
        if time.minute == 0:
            return arrow.get(time).to(self.timezone).strftime("%-I%p").lower()
        else:
            return arrow.get(time).to(self.timezone).strftime("%-I:%M%p").lower()

    def format_duration(self, duration: datetime.timedelta, short=False) -> str:
        seconds = duration.total_seconds()
        if seconds < 3600:
            value = seconds // 60
            suffix = "min"
        elif seconds < 86400:
            value = seconds // 3600
            suffix = "hour"
        else:
            value = seconds // 86400
            suffix = "day"
        if int(value) == value:
            value_str = f"{int(value)}"
        else:
            value_str = f"{value:.1f}"
        if short:
            return value_str + suffix[0]
        else:
            return value_str + " " + suffix
