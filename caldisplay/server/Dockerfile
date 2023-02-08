FROM python:3.11-alpine

# Copy and install requirements
RUN apk update && apk add \
    gcc \
    g++ \
    freetype-dev \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    libjpeg \
    python3-dev \
    cairo-dev

# Codebase setup
RUN mkdir /srv/caldisplay/
WORKDIR /srv/caldisplay/
RUN pip3 install gunicorn

# Add code
ENV PYTHONPATH /srv/caldisplay/server/
ADD . /srv/caldisplay/
RUN pip install -r requirements.txt

# Runtime
ENV PORT 80
CMD ["/bin/sh", "-c", "exec gunicorn --bind :$PORT --workers 1 --threads 8 server:app"]
