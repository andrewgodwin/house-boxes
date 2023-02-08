import arrow
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, send_file, request

app = Flask(__name__)


class Colours:
    BLACK = 0
    DARK_GREY = 63
    GREY = 127
    LIGHT_GREY = 191
    WHITE = 255


@app.route("/")
def index():
    # Get API key
    png_mode = request.args.get("png")
    # Render
    image = CalendarRenderer({}).render()
    output = BytesIO()
    if png_mode:
        image.save(output, "PNG")
    else:
        # Custom 2 pixels per byte mode
        raw_bytes = image.tobytes()
        for i in range(len(raw_bytes) // 2):
            offset = i * 2
            byte1 = raw_bytes[offset] // 16
            byte2 = raw_bytes[offset + 1] // 16
            output.write(bytes([(byte1 << 4) | byte2]))
    # Send to client
    output.seek(0)
    return send_file(
        output, mimetype="image/png" if png_mode else "application/octet-stream"
    )


class CalendarRenderer:
    def __init__(self, calendar_urls: dict[str, str], timezone="US/Mountain"):
        self.calendar_urls = calendar_urls
        self.size = (1100, 725)
        self.timezone = timezone
        self.now: arrow.Arrow = arrow.utcnow().to(self.timezone)
        self.fonts = {}

    def render(self) -> Image.Image:
        # Prepare image
        self.image = Image.new("L", self.size, 0)
        self.draw = ImageDraw.ImageDraw(self.image)
        self.image.paste(255, (0, 0, self.size[0], self.size[1]))
        # Draw the date
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
            (dw + 40, 17), self.now.strftime("%B %Y"), Colours.GREY, ("medium", 30)
        )
        # Draw some test rects
        self.draw.rectangle((0, 200, 200, 230), Colours.BLACK)
        self.draw.rectangle((0, 230, 200, 260), Colours.DARK_GREY)
        self.draw.rectangle((0, 260, 200, 290), Colours.GREY)
        self.draw.rectangle((0, 290, 200, 320), Colours.LIGHT_GREY)
        return self.image

    def draw_text(self, pos, text, colour, font, align="left") -> tuple[int, int]:
        """
        Draws text and returns its size
        """
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
        self.draw.text((x, y), str(text), fill=colour, font=self.fonts[font])
        return size
