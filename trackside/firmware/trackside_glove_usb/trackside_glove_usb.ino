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

#define LED_PIN    18
#define NUM_LEDS   10    // strip has 10 LEDs; only the first 5 are used
#define MOTOR_PIN  26
#define ENABLE_MOTOR false   // set to true once a vibration motor is wired up

const float FALLBACK_THRESHOLD = 1.15;   // used only for plain "1.25" lines

const uint8_t NOMINAL = 0, MONITORING = 1, INTERVENE = 2, WAITING = 255;

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

// Decides the stage from a plain g-force number using fallback threshold.
// Input: g (float). Output: NOMINAL, MONITORING, or INTERVENE.
uint8_t classify(float g) {
  if (g >= FALLBACK_THRESHOLD)         return INTERVENE;
  if (g >= FALLBACK_THRESHOLD * 0.82f) return MONITORING;
  return NOMINAL;
}

// Validates that g-force reading is finite and within physical bounds (0.0 to 10.0 g).
// Input: g (float). Output: true if valid, false if NaN, inf, or out-of-range (G5).
bool isValidG(float g) {
  if (isnan(g) || isinf(g)) return false;
  if (g < 0.0f || g > 10.0f) return false;
  return true;
}

// Parses stage word strictly against allowed names (case-insensitive).
// Input: text (const char*), outStage (uint8_t*). Output: true on match, false otherwise (G5).
// Security: Never defaults unknown words to NOMINAL.
bool parseStageWord(const char* text, uint8_t* outStage) {
  while (*text == ' ' || *text == '\t') text++;
  char word[16];
  size_t idx = 0;
  while (*text != '\0' && !isspace((unsigned char)*text) && *text != '\r' && *text != '\n') {
    if (idx + 1 < sizeof(word)) {
      word[idx++] = (char)toupper((unsigned char)*text);
    } else {
      return false;
    }
    text++;
  }
  word[idx] = '\0';

  if (strcmp(word, "NOMINAL") == 0) {
    *outStage = NOMINAL;
    return true;
  }
  if (strcmp(word, "MONITORING") == 0) {
    *outStage = MONITORING;
    return true;
  }
  if (strcmp(word, "INTERVENE") == 0) {
    *outStage = INTERVENE;
    return true;
  }
  return false;
}

// Handles one complete serial line from USB with strict validation (G5).
// Discards lines with malformed numbers, out-of-range g, or unrecognized stage words.
void handleLine(char* line) {
  while (*line == ' ' || *line == '\t') line++;
  if (*line == '\0') return;

  // A real line must start with a digit, a dot or a minus sign
  if (!(isdigit((unsigned char)*line) || *line == '.' || *line == '-')) {
    Serial.println("Ignored invalid line. Expected number or number,STAGE.");
    return;
  }

  uint8_t stage = NOMINAL;
  float   g     = 0.0f;
  char* comma = strchr(line, ',');
  if (comma) {
    *comma = '\0';
    char* endPtr = NULL;
    g = (float)strtod(line, &endPtr);
    if (endPtr == line || !isValidG(g)) {
      Serial.println("Ignored invalid line: g-force must be between 0.0 and 10.0.");
      return;
    }
    if (!parseStageWord(comma + 1, &stage)) {
      Serial.println("Ignored invalid line: unknown stage word (allowed: NOMINAL, MONITORING, INTERVENE).");
      return;
    }
  } else {
    char* endPtr = NULL;
    g = (float)strtod(line, &endPtr);
    if (endPtr == line || !isValidG(g)) {
      Serial.println("Ignored invalid line: g-force must be between 0.0 and 10.0.");
      return;
    }
    stage = classify(g);
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
