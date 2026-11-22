#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <ESP32Servo.h>
#include <DHT.h>

namespace {
// OhStem Yolo UNO ESP32-S3 GPIO mapping (see the wiring table).
constexpr uint8_t TFT_CS = 21;   // D10
constexpr uint8_t TFT_DC = 7;    // D4
constexpr uint8_t TFT_RST = 8;   // D5
constexpr uint8_t TFT_MOSI = 38; // D11
constexpr uint8_t TFT_SCK = 18;  // D9
constexpr uint8_t LED_PIN = 17;  // D8
constexpr uint8_t BUZZER_PIN = 6; // D3
constexpr uint8_t SERVO_PIN = 5;  // D2
constexpr int SERVO_OPEN_ANGLE = 0;
constexpr int SERVO_CLOSED_ANGLE = 180;
constexpr uint8_t MQ2_PIN = 1;    // A0
constexpr uint8_t FLAME_PIN = 9;  // D6
constexpr uint8_t DHT_PIN = 10;   // D7
constexpr uint8_t DHT_TYPE = DHT11;
// Threshold is based on the ESP32 ADC reading (0-4095); adjust after checking Serial.
constexpr int MQ2_ALARM_THRESHOLD = 1800;
constexpr int MQ2_CLEAR_THRESHOLD = 1650;  // Hysteresis prevents rapid state changes.
constexpr float TEMP_ALARM_THRESHOLD_C = 30.0f;
constexpr float TEMP_CLEAR_THRESHOLD_C = 29.0f;
constexpr uint32_t SENSOR_SAMPLE_INTERVAL_MS = 100;
constexpr uint32_t SERIAL_REPORT_INTERVAL_MS = 500;
constexpr uint32_t DHT_SAMPLE_INTERVAL_MS = 2000;

Adafruit_ILI9341 tft(TFT_CS, TFT_DC, TFT_RST);
Servo doorServo;
DHT dht(DHT_PIN, DHT_TYPE);
bool showingSafe = true;
bool mq2AlarmActive = false;
bool temperatureAlarmActive = false;
float temperatureC = NAN;
float humidityPercent = NAN;
uint32_t lastSensorSample = 0;
uint32_t lastSerialReport = 0;
uint32_t lastDhtRead = 0;

void drawSensorReading(bool safe, int mq2Value, bool flameDetected,
                       float temperature, float humidity) {
  const uint16_t background = safe ? ILI9341_DARKGREEN : ILI9341_RED;
  tft.fillRect(0, 145, tft.width(), 95, background);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(2);
  tft.setCursor(24, 150);
  tft.printf("MQ-2: %d/4095", mq2Value);
  tft.setCursor(24, 172);
  tft.printf("LUA: %s", flameDetected ? "PHAT HIEN" : "KHONG");
  tft.setCursor(24, 194);
  if (isnan(temperature) || isnan(humidity)) {
    tft.print("T:--.-C RH:--%");
  } else {
    tft.printf("T:%.1fC RH:%.0f%%", temperature, humidity);
  }
  tft.setCursor(24, 216);
  tft.printf("MQ:%d/%d T:%.0fC", MQ2_ALARM_THRESHOLD, MQ2_CLEAR_THRESHOLD,
             TEMP_ALARM_THRESHOLD_C);
}

void showStatus(bool safe, int mq2Value, bool flameDetected,
                float temperature, float humidity) {
  const uint16_t background = safe ? ILI9341_DARKGREEN : ILI9341_RED;

  tft.fillScreen(background);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextWrap(false);

  const char *title = safe ? "HE THONG AN TOAN" : "CANH BAO CHAY!";
  tft.setTextSize(safe ? 2 : 3);
  int16_t x1, y1;
  uint16_t textWidth, textHeight;
  tft.getTextBounds(title, 0, 0, &x1, &y1, &textWidth, &textHeight);
  tft.setCursor((tft.width() - textWidth) / 2 - x1, safe ? 55 : 75);
  tft.print(title);

  drawSensorReading(safe, mq2Value, flameDetected, temperature, humidity);

  digitalWrite(LED_PIN, safe ? LOW : HIGH);
  if (safe) {
    noTone(BUZZER_PIN);
  } else {
    tone(BUZZER_PIN, 500); 
  }
  doorServo.write(safe ? SERVO_OPEN_ANGLE : SERVO_CLOSED_ANGLE);

  Serial.println(safe ? F("[AN TOAN] Servo mo cua")
                      : F("[CANH BAO CHAY] Servo dong cua"));
}
}  // namespace

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(MQ2_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  analogReadResolution(12);
  dht.begin();
  lastDhtRead = millis();
  doorServo.attach(SERVO_PIN, 1000, 2000);
  doorServo.write(0);

  // SPI pins are explicitly routed for Yolo UNO: SCK=GPIO18, MOSI=GPIO38.
  SPI.begin(TFT_SCK, -1, TFT_MOSI, TFT_CS);
  tft.begin();
  tft.setRotation(1);  // Landscape, 320x240.

  const int initialMq2Value = analogRead(MQ2_PIN);
  const bool initialFlameDetected = digitalRead(FLAME_PIN) == LOW;
  mq2AlarmActive = initialMq2Value >= MQ2_ALARM_THRESHOLD;
  showingSafe = !mq2AlarmActive && !initialFlameDetected && !temperatureAlarmActive;
  showStatus(showingSafe, initialMq2Value, initialFlameDetected,
             temperatureC, humidityPercent);
}

void loop() {
  const uint32_t now = millis();
  if (static_cast<uint32_t>(now - lastDhtRead) >= DHT_SAMPLE_INTERVAL_MS) {
    lastDhtRead = now;
    temperatureC = dht.readTemperature();
    humidityPercent = dht.readHumidity();
    if (isnan(temperatureC) || isnan(humidityPercent)) {
      Serial.println(F("DHT11 read failed; check wiring on GPIO10 (D7)."));
    } else if (!temperatureAlarmActive && temperatureC >= TEMP_ALARM_THRESHOLD_C) {
      temperatureAlarmActive = true;
    } else if (temperatureAlarmActive && temperatureC <= TEMP_CLEAR_THRESHOLD_C) {
      temperatureAlarmActive = false;
    }
  }

  if (static_cast<uint32_t>(now - lastSensorSample) >= SENSOR_SAMPLE_INTERVAL_MS) {
    lastSensorSample = now;
    const int mq2Value = analogRead(MQ2_PIN);
    const bool flameDetected = digitalRead(FLAME_PIN) == LOW;
    if (!mq2AlarmActive && mq2Value >= MQ2_ALARM_THRESHOLD) {
      mq2AlarmActive = true;
    } else if (mq2AlarmActive && mq2Value <= MQ2_CLEAR_THRESHOLD) {
      mq2AlarmActive = false;
    }
    const bool nextSafe = !mq2AlarmActive && !flameDetected && !temperatureAlarmActive;

    if (nextSafe != showingSafe) {
      showingSafe = nextSafe;
      showStatus(showingSafe, mq2Value, flameDetected, temperatureC, humidityPercent);
    } else if (static_cast<uint32_t>(now - lastSerialReport) >= SERIAL_REPORT_INTERVAL_MS) {
      drawSensorReading(showingSafe, mq2Value, flameDetected, temperatureC, humidityPercent);
    }

    if (static_cast<uint32_t>(now - lastSerialReport) >= SERIAL_REPORT_INTERVAL_MS) {
      lastSerialReport = now;
      Serial.printf("MQ-2 ADC: %d | Lua: %s | Nhiet do: %.1f C | Do am: %.0f%% | Trang thai: %s\n", mq2Value,
                    flameDetected ? "PHAT HIEN" : "KHONG",
                    temperatureC, humidityPercent,
                    showingSafe ? "AN TOAN" : "CANH BAO");
    }
  }
}
