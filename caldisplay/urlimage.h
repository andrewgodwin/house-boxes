#include "esphome.h"

#include <HTTPClient.h>

using display::DisplayBuffer;

void show_url_bitmap(DisplayBuffer *display, char *url, int left, int top, int width, int height)
{
    HTTPClient http;
    http.setTimeout(30000);
    http.setConnectTimeout(30000);
    http.setReuse(false);

    ESP_LOGD("url_bitmap", "Creating client for %s", url);
    int begin_status = http.begin(url);
    if (!begin_status)
    {
        ESP_LOGE("url_bitmap", "Could not download image from %s. Connection failed: %i", url, begin_status);
        return;
    }

    ESP_LOGD("url_bitmap", "Beginning download");
    int http_code = http.GET();
    ESP_LOGD("url_bitmap", "Got response");
    if (http_code != HTTP_CODE_OK)
    {
        ESP_LOGE("url_bitmap", "Could not download image from %s. Error code: %i", url, http_code);
        http.end();
        return;
    }

    // Prepare the stream for reading
    WiFiClient *stream = http.getStreamPtr();
    ESP_LOGD("url_bitmap", "Reading stream");
    uint8_t buff[256] = {0};
    int offset = 0;
    int total_pixels = (height * width);
    bool blanked = false;
    ESP_LOGD("url_bitmap", "Downloading image from %s, expecting %d pixels", url, total_pixels);
    while (http.connected() && offset < total_pixels)
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
                if (!blanked)
                {
                    blanked = true;
                    display->fill(COLOR_ON);
                }
                uint8_t byte1 = (buff[i] >> 4) * 16;
                uint8_t byte2 = (buff[i] & 15) * 16;
                int x = offset % width;
                int y = offset / width;
                display->draw_pixel_at(left + x, top + y, Color(byte1, byte1, byte1, byte1));
                offset++;
                display->draw_pixel_at(left + x + 1, top + y, Color(byte2, byte2, byte2, byte2));
                offset++;
            }
        }
        delay(1);
    }
    ESP_LOGD("url_bitmap", "Downloaded %d pixels", offset);
    http.end();
}
