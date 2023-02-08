#include "esphome.h"
#include <Wire.h>

class UltrasonicSensor : public PollingComponent, public Sensor
{
public:
    UltrasonicSensor() : PollingComponent(2000) {}
    float get_setup_priority() const override { return esphome::setup_priority::BUS; }
    void setup() override
    {
        // This will be called by App.setup()
    }
    void update() override
    {
        uint32_t data;
        Wire.beginTransmission(0x57);
        Wire.write(0x01);
        Wire.endTransmission();
        delay(120);
        Wire.requestFrom(0x57, 3);
        data = Wire.read();
        data <<= 8;
        data |= Wire.read();
        data <<= 8;
        data |= Wire.read();
        float distance = float(data) / 1000;
        if (distance > 20 && distance < 1500)
        {
            publish_state(distance);
        }
    }
};
