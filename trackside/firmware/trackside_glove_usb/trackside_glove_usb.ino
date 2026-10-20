/*
  TRACKSIDE - GLOVE UNIT (USB DIRECT, LEDs ONLY)
  ----------------------------------------------
  Use this when the glove ESP32 is plugged straight into the laptop by USB.
  No bridge board and no radio needed. The Python simulator
  (demo/virtual_lap_simulator.py) writes lines like
        1.25,MONITORING
  to this board's COM port and the LED strip reacts live:
        NOMINAL    -> 2 LEDs  (green, green)
        MONITORING -> 4 LEDs  (green, green, amber, amber)
        INTERVENE  -> 5 LEDs  (... + red, which blinks)

  Wiring:
     LED strip  5V  -> VIN / 5V
     LED strip  GND -> GND
     LED strip  DIN -> GPIO 18   (optional 330 ohm resistor)

  Test by hand: Serial Monitor, 115200 baud, "Newline", type  1.3  or  1.3,INTERVENE
  (close the Serial Monitor before running the Python simulator - only one
   program can use the COM port at a time).

  Libraries needed: Adafruit NeoPixel.
*/

#include <Adafruit_NeoPixel.h>
#include <ctype.h>
#include "trackside_radio_protocol.h"

#define LED_PIN    18
#define NUM_LEDS   10    // strip has 10 LEDs; only the first 5 are used
#define MOTOR_PIN  26
#define ENABLE_MOTOR false   // set to true once a vibration motor is wired up

const float FALLBACK_THRESHOLD = 1.15;   // used only for plain "1.25" lines

const uint8_t NOMINAL = TRACKSIDE_STAGE_NOMINAL;
const uint8_t MONITORING = TRACKSIDE_STAGE_MONITORING;
const uint8_t INTERVENE = TRACKSIDE_STAGE_INTERVENE;
const uint8_t WAITING = TRACKSIDE_STAGE_WAITING;

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

const uint32_t SEG_COLOR[5] = {
  Adafruit_NeoPixel::Color(0, 255, 0),
  Adafruit_NeoPixel::Color(0, 255, 0),
  Adafruit_NeoPixel::Color(255, 110, 0),
  Adafruit_NeoPixel::Color(255, 110, 0),
  Adafruit_NeoPixel::Color(255, 0, 0)
};

uint8_t  gStage      = WAITING;
float    gLastG      = 0;
uint32_t gLastPacket = 0;
uint8_t  shownStage  = 254;
bool     redOn       = true;

char    lineBuf[48];
uint8_t lineLen = 0;

int litSegments(uint8_t s) {
  if (s == NOMINAL)    return 2;
  if (s == MONITORING) return 4;
  if (s == INTERVENE)  return 5;
  return 0;
}

// redVisible lets the red LED blink during INTERVENE
void drawStage(uint8_t stage, bool redVisible) {
  strip.clear();
  if (stage == WAITING) {
    strip.setPixelColor(0, Adafruit_NeoPixel::Color(0, 0, 40));   // dim blue = waiting
  } else {
    int lit = litSegments(stage);
    for (int i = 0; i < lit; i++) {
      if (i == 4 && !redVisible) continue;
      strip.setPixelColor(i, SEG_COLOR[i]);
    }
  }
  strip.show();
}

// Handles one complete serial line from USB with strict shared validation (G5, G6).
// Discards lines with malformed numbers, out-of-range g, or unrecognized stage words.
void handleLine(char* line) {
  float   g     = 0.0f;
  uint8_t stage = NOMINAL;

  if (!trackside_parse_serial_line(line, FALLBACK_THRESHOLD, &g, &stage)) {
    Serial.println("Ignored invalid line. Expected number or number,STAGE (0.0..10.0, NOMINAL/MONITORING/INTERVENE).");
    return;
  }

  gLastG      = g;
  gStage      = stage;
  gLastPacket = millis();
}

void selfTest() {
  for (int i = 0; i < 5; i++) {
    strip.clear();
    strip.setPixelColor(i, SEG_COLOR[i]);
    strip.show();
    delay(200);
  }
  drawStage(INTERVENE, true);
  delay(400);
  drawStage(WAITING, true);
}

void setup() {
  Serial.begin(115200);
  if (ENABLE_MOTOR) {
    pinMode(MOTOR_PIN, OUTPUT);
    digitalWrite(MOTOR_PIN, LOW);
  }
  strip.begin();
  strip.setBrightness(50);
  strip.clear();
  strip.show();
  selfTest();
  Serial.println();
  Serial.println("=== TRACKSIDE GLOVE (USB direct) ready ===");
}

void loop() {
  uint32_t now = millis();

  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
    } else if (c != '\r' && lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    }
  }

  // No data for 1.5 s -> back to the waiting state
  if (gStage != WAITING && (now - gLastPacket) > 1500) gStage = WAITING;

  // Red LED blinks (4 Hz) while intervening
  bool wantRed = (gStage != INTERVENE) || ((now % 250) < 150);

  if (gStage != shownStage || (gStage == INTERVENE && wantRed != redOn)) {
    if (gStage != shownStage) {
      const char* names[] = {"NOMINAL", "MONITORING", "INTERVENE"};
      if (gStage == WAITING) Serial.println("Stage: WAITING");
      else Serial.printf("Stage: %s (g=%.2f)\n", names[gStage], gLastG);
    }
    drawStage(gStage, wantRed);
    shownStage = gStage;
    redOn = wantRed;
  }

  if (ENABLE_MOTOR) {
    bool on = (gStage == INTERVENE) || (gStage == MONITORING && (now % 600) < 120);
    digitalWrite(MOTOR_PIN, on ? HIGH : LOW);
  }
  delay(5);
}
