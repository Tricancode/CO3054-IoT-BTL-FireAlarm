#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Arduino.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <SPI.h>
#include "tinyml_fire_model.h"

namespace {
// OhStem Yolo UNO ESP32-S3 GPIO mapping (see the wiring table).
constexpr uint8_t TFT_CS = 21;    // D10
constexpr uint8_t TFT_DC = 7;     // D4
constexpr uint8_t TFT_RST = 8;    // D5
constexpr uint8_t TFT_MOSI = 38;  // D11
constexpr uint8_t TFT_SCK = 18;   // D9
constexpr uint8_t LED_PIN = 17;   // D8
constexpr uint8_t BUZZER_PIN = 6; // D3
constexpr uint8_t SERVO_PIN = 5;  // D2
constexpr int SERVO_OPEN_ANGLE = 0;
constexpr int SERVO_CLOSED_ANGLE = 180;
constexpr uint8_t MQ2_PIN = 1;   // A0
constexpr uint8_t FLAME_PIN = 9; // D6
constexpr uint8_t DHT_PIN = 10;  // D7
constexpr uint8_t DHT_TYPE = DHT11;
// Threshold is based on the ESP32 ADC reading (0-4095); adjust after checking
// Serial.
constexpr int MQ2_ALARM_THRESHOLD = 1800;
constexpr int MQ2_CLEAR_THRESHOLD =
    1650; // Hysteresis prevents rapid state changes.
constexpr float TEMP_ALARM_THRESHOLD_C = 35.0f;
constexpr float TEMP_CLEAR_THRESHOLD_C = 34.0f;
constexpr uint32_t SENSOR_SAMPLE_INTERVAL_MS = 100;
constexpr uint32_t SERIAL_REPORT_INTERVAL_MS = 500;
constexpr uint32_t DHT_SAMPLE_INTERVAL_MS = 2000;

Adafruit_ILI9341 tft(TFT_CS, TFT_DC, TFT_RST);
Servo doorServo;
DHT dht(DHT_PIN, DHT_TYPE);
bool showingSafe = true;
bool mq2AlarmActive = false;
bool temperatureAlarmActive = false;
bool masterAlarmOverride = false;
float temperatureC = NAN;
float humidityPercent = NAN;
uint32_t lastSensorSample = 0;
uint32_t lastSerialReport = 0;
uint32_t lastDhtRead = 0;

bool sensorAlarmActive() {
  return mq2AlarmActive || temperatureAlarmActive ||
         digitalRead(FLAME_PIN) == LOW;
}

void applyActuatorOutputs(bool alarmActive) {
  const bool forceAlarm = alarmActive || masterAlarmOverride;
  digitalWrite(LED_PIN, forceAlarm ? HIGH : LOW);
  if (forceAlarm) {
    tone(BUZZER_PIN, 500);
  } else {
    noTone(BUZZER_PIN);
  }
  doorServo.write(forceAlarm ? SERVO_CLOSED_ANGLE : SERVO_OPEN_ANGLE);
}

void drawSensorReading(bool safe, int mq2Value, bool flameDetected,
                       float temperature, float humidity, float aiRisk = 0.0f) {
  const uint16_t background = safe ? ILI9341_DARKGREEN : ILI9341_RED;
  tft.fillRect(0, 140, tft.width(), 100, background);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(2);
  tft.setCursor(24, 145);
  tft.printf("MQ-2: %d/4095", mq2Value);
  tft.setCursor(24, 168);
  tft.printf("LUA: %s", flameDetected ? "PHAT HIEN" : "KHONG");
  tft.setCursor(24, 191);
  if (isnan(temperature) || isnan(humidity)) {
    tft.print("T:--.-C RH:--%");
  } else {
    tft.printf("T:%.1fC RH:%.0f%%", temperature, humidity);
  }
  tft.setCursor(24, 214);
  tft.printf("TinyML: %.1f%% (%s)", aiRisk * 100.0f, tinyml_get_risk_label(aiRisk));
}

void showStatus(bool safe, int mq2Value, bool flameDetected, float temperature,
                float humidity, float aiRisk = 0.0f) {
  const bool displaySafe = safe && !masterAlarmOverride;
  const uint16_t background = displaySafe ? ILI9341_DARKGREEN : ILI9341_RED;

  tft.fillScreen(background);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextWrap(false);

  const char *title = displaySafe ? "HE THONG AN TOAN" : "CANH BAO CHAY!";
  tft.setTextSize(displaySafe ? 2 : 3);
  int16_t x1, y1;
  uint16_t textWidth, textHeight;
  tft.getTextBounds(title, 0, 0, &x1, &y1, &textWidth, &textHeight);
  tft.setCursor((tft.width() - textWidth) / 2 - x1, displaySafe ? 55 : 75);
  tft.print(title);

  drawSensorReading(displaySafe, mq2Value, flameDetected, temperature,
                    humidity, aiRisk);
  applyActuatorOutputs(!safe);

  Serial.println(safe ? F("[AN TOAN] Servo mo cua")
                      : F("[CANH BAO CHAY] Servo dong cua"));
}

char cmdBuffer[128];
size_t cmdIndex = 0;
uint32_t manualOverrideUntil = 0;

void handleCommand(const char *cmd) {
  manualOverrideUntil = millis() + 5000;

  const char *pOverride = strstr(cmd, "alarm_override");
  if (pOverride) {
    const char *colon = strchr(pOverride, ':');
    if (colon) {
      masterAlarmOverride = atoi(colon + 1) == 1 || strstr(colon, "true");
      const int mq2Value = analogRead(MQ2_PIN);
      const bool flameDetected = digitalRead(FLAME_PIN) == LOW;
      showingSafe = !sensorAlarmActive();
      showStatus(showingSafe, mq2Value, flameDetected, temperatureC,
                 humidityPercent);
      Serial.println(masterAlarmOverride
                         ? F("[ACK] Master override ON: all actuators forced")
                         : F("[ACK] Master override OFF: automatic mode"));
    }
  }

  // 1. Servo command (handles {"servo": 90} or {"method": "setServo", "params":
  // 90})
  const char *pServo = strstr(cmd, "servo");
  if (!pServo)
    pServo = strstr(cmd, "Servo");
  if (pServo) {
    const char *colon = strchr(pServo, ':');
    if (colon) {
      int angle = atoi(colon + 1);
      if (angle >= 0 && angle <= 180) {
        doorServo.write(angle);
        Serial.printf("[ACK] Servo set to %d deg\n", angle);
      }
    }
  }

  // 2. Buzzer command (handles {"buzzer": 1} or {"method": "setBuzzer",
  // "params": 1})
  const char *pBuzzer = strstr(cmd, "buzzer");
  if (!pBuzzer)
    pBuzzer = strstr(cmd, "Buzzer");
  if (pBuzzer) {
    const char *colon = strchr(pBuzzer, ':');
    if (colon) {
      int bVal = atoi(colon + 1);
      if (bVal == 1 || strstr(colon, "true")) {
        tone(BUZZER_PIN, 500);
        Serial.println(F("[ACK] Buzzer ACTIVATED"));
      } else {
        noTone(BUZZER_PIN);
        Serial.println(F("[ACK] Buzzer SILENCED"));
      }
    }
  }

  // 3. LED command (handles {"led": 1} or {"method": "setLed", "params": 1})
  const char *pLed = strstr(cmd, "led");
  if (!pLed)
    pLed = strstr(cmd, "Led");
  if (pLed) {
    const char *colon = strchr(pLed, ':');
    if (colon) {
      int lVal = atoi(colon + 1);
      if (lVal == 1 || strstr(colon, "true")) {
        digitalWrite(LED_PIN, HIGH);
        Serial.println(F("[ACK] LED ACTIVATED"));
      } else {
        digitalWrite(LED_PIN, LOW);
        Serial.println(F("[ACK] LED TURNED OFF"));
      }
    }
  }

  if (masterAlarmOverride) {
    applyActuatorOutputs(true);
  }
}

void processSerialCommands() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (cmdIndex > 0) {
        cmdBuffer[cmdIndex] = '\0';
        handleCommand(cmdBuffer);
        cmdIndex = 0;
      }
    } else if (cmdIndex < sizeof(cmdBuffer) - 1) {
      cmdBuffer[cmdIndex++] = c;
    }
  }
}
} // namespace

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
  tft.setRotation(1); // Landscape, 320x240.

  const int initialMq2Value = analogRead(MQ2_PIN);
  const bool initialFlameDetected = digitalRead(FLAME_PIN) == LOW;
  mq2AlarmActive = initialMq2Value >= MQ2_ALARM_THRESHOLD;
  showingSafe =
      !mq2AlarmActive && !initialFlameDetected && !temperatureAlarmActive;
  showStatus(showingSafe, initialMq2Value, initialFlameDetected, temperatureC,
             humidityPercent);
}

void loop() {
  processSerialCommands();

  const uint32_t now = millis();
  if (static_cast<uint32_t>(now - lastDhtRead) >= DHT_SAMPLE_INTERVAL_MS) {
    lastDhtRead = now;
    temperatureC = dht.readTemperature();
    humidityPercent = dht.readHumidity();
    if (isnan(temperatureC) || isnan(humidityPercent)) {
      Serial.println(F("DHT11 read failed; check wiring on GPIO10 (D7)."));
    } else if (!temperatureAlarmActive &&
               temperatureC >= TEMP_ALARM_THRESHOLD_C) {
      temperatureAlarmActive = true;
    } else if (temperatureAlarmActive &&
               temperatureC <= TEMP_CLEAR_THRESHOLD_C) {
      temperatureAlarmActive = false;
    }
  }

  if (static_cast<uint32_t>(now - lastSensorSample) >=
      SENSOR_SAMPLE_INTERVAL_MS) {
    lastSensorSample = now;
    const int mq2Value = analogRead(MQ2_PIN);
    const bool flameDetected = digitalRead(FLAME_PIN) == LOW;
    if (!mq2AlarmActive && mq2Value >= MQ2_ALARM_THRESHOLD) {
      mq2AlarmActive = true;
    } else if (mq2AlarmActive && mq2Value <= MQ2_CLEAR_THRESHOLD) {
      mq2AlarmActive = false;
    }
    const bool nextSafe =
        !mq2AlarmActive && !flameDetected && !temperatureAlarmActive;

    const float curTemp = isnan(temperatureC) ? 28.0f : temperatureC;
    const float curHum = isnan(humidityPercent) ? 65.0f : humidityPercent;
    const float aiRisk = tinyml_predict_fire_risk(static_cast<float>(mq2Value), curTemp, flameDetected ? 1.0f : 0.0f, curHum);

    if (nextSafe != showingSafe) {
      if (!nextSafe) {
        manualOverrideUntil =
            0; // Real danger overrides any manual remote state
      }
      if (!nextSafe || now >= manualOverrideUntil) {
        showingSafe = nextSafe;
        showStatus(showingSafe, mq2Value, flameDetected, temperatureC,
                   humidityPercent, aiRisk);
      }
    } else if (static_cast<uint32_t>(now - lastSerialReport) >=
               SERIAL_REPORT_INTERVAL_MS) {
      drawSensorReading(showingSafe, mq2Value, flameDetected, temperatureC,
                        humidityPercent, aiRisk);
    }

    if (static_cast<uint32_t>(now - lastSerialReport) >=
        SERIAL_REPORT_INTERVAL_MS) {
      lastSerialReport = now;
      Serial.printf("MQ-2 ADC: %d | Lua: %s | Nhiet do: %.1f C | Do am: %.0f%% | AI Risk: %.1f%% | Trang thai: %s\n",
                    mq2Value, flameDetected ? "PHAT HIEN" : "KHONG",
                    temperatureC, humidityPercent, aiRisk * 100.0f,
                    showingSafe ? "AN TOAN" : "CANH BAO");
    }
  }
}
