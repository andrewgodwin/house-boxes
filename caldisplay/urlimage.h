#include "esphome.h"

#include <HTTPClient.h>

using display::DisplayBuffer;

void show_url_bitmap(DisplayBuffer *display, char *url, int left, int top, int width, int height)
{
    HTTPClient http;

    int begin_status = http.begin(url);
    if (!begin_status)
    {
        ESP_LOGE("url_bitmap", "Could not download image from %s. Connection failed: %i", url, begin_status);
        return;
    }

    int http_code = http.GET();
    if (http_code != HTTP_CODE_OK)
    {
        App.feed_wdt();
        ESP_LOGE("url_bitmap", "Could not download image from %s. Error code: %i", url, http_code);
        http.end();
        return;
    }

    // Prepare the stream for reading
    WiFiClient *stream = http.getStreamPtr();
    uint8_t buff[1024] = {0};
    int offset = 0;
    int total_bytes = height * width;
    ESP_LOGD("url_bitmap", "Downloading image from %s, expecting %d bytes", url, total_bytes);
    while (http.connected() && offset < total_bytes)
    {
        // get available data size
        size_t size = stream->available();

        if (size)
        {
            // read up to width bytes
            int c = stream->readBytes(buff, ((size > sizeof(buff)) ? sizeof(buff) : size));

            // Write them to the display
            for (int i = 0; i < c; i++)
            {
                uint8_t value = buff[i];
                int x = offset % width;
                int y = offset / width;
                display->draw_pixel_at(left + x, top + y, Color(value, value, value, value));
                offset++;
            }
        }
        delay(1);
    }
    ESP_LOGD("url_bitmap", "Downloaded %d bytes", offset);
    http.end();
}
