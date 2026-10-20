/*
 * TRACKSIDE RADIO PROTOCOL & PARSING LIBRARY
 * ------------------------------------------
 * Pure C/C++ implementation of packet structure, replay validation,
 * stage keyword parsing, and g-force boundary checks.
 *
 * Designed with zero Arduino dependencies to allow host-side unit testing.
 * Synchronized to sketches using firmware/tools/sync_shared.py.
 */

#ifndef TRACKSIDE_RADIO_PROTOCOL_H
#define TRACKSIDE_RADIO_PROTOCOL_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <math.h>
#include <ctype.h>
#include <string.h>
#include <stdlib.h>

// Protocol version constant (G3)
#define TRACKSIDE_RADIO_VERSION    1

// Warning stage codes matching visual indicator segments
#define TRACKSIDE_STAGE_NOMINAL    0
#define TRACKSIDE_STAGE_MONITORING 1
#define TRACKSIDE_STAGE_INTERVENE  2
#define TRACKSIDE_STAGE_WAITING    255

// Strict binary packet structure transmitted over encrypted ESP-NOW (G3)
typedef struct __attribute__((packed)) {
  uint8_t  version;  // Protocol version (must equal TRACKSIDE_RADIO_VERSION = 1)
  uint8_t  stage;    // Warning stage: 0 = NOMINAL, 1 = MONITORING, 2 = INTERVENE
  float    g;        // Lateral acceleration in g (must be finite, 0.0 .. 10.0)
  uint32_t counter;  // Monotonically increasing sequence number for replay guard
} RadioPacket;

/**
 * Validates that a lateral acceleration value is finite and within physical kart bounds.
 * Input: g (float value).
 * Output: true if valid (0.0 <= g <= 10.0 and not NaN/inf), false otherwise.
 * Security: Prevents NaN/inf arithmetic errors and out-of-range sensor corruptions.
 */
static inline bool trackside_validate_g(float g) {
  if (isnan(g) || isinf(g)) {
    return false;
  }
  if (g < 0.0f || g > 10.0f) {
    return false;
  }
  return true;
}

/**
 * Validates raw packet buffer against strict protocol length, version, stage, and g range.
 * Input: buffer (byte pointer), length (size in bytes), outPacket (destination pointer).
 * Output: true if valid, false if rejected.
 * Security: Enforces exact length (10 bytes), version 1, stage <= 2, finite g 0..10.
 * A rejected packet must never update receiver state or refresh keep-alive timers.
 */
static inline bool trackside_validate_packet(const uint8_t* buffer, size_t length, RadioPacket* outPacket) {
  if (buffer == NULL || length != sizeof(RadioPacket)) {
    return false;
  }
  RadioPacket candidate;
  memcpy(&candidate, buffer, sizeof(RadioPacket));

  if (candidate.version != TRACKSIDE_RADIO_VERSION) {
    return false;
  }
  if (candidate.stage > TRACKSIDE_STAGE_INTERVENE) {
    return false;
  }
  if (!trackside_validate_g(candidate.g)) {
    return false;
  }

  if (outPacket != NULL) {
    *outPacket = candidate;
  }
  return true;
}

/**
 * Evaluates whether an incoming packet sequence counter is valid or a replay.
 * Input: incomingCounter (uint32_t), lastCounter (pointer to stored state), isInitialized (pointer to bool flag).
 * Output: true if counter is accepted, false if rejected.
 * Security: First packet after boot initializes baseline. Subsequent packets must have
 * incomingCounter strictly greater than lastCounter. Duplicate or decreasing counters are rejected.
 */
static inline bool trackside_check_replay_guard(uint32_t incomingCounter, uint32_t* lastCounter, bool* isInitialized) {
  if (lastCounter == NULL || isInitialized == NULL) {
    return false;
  }
  if (!(*isInitialized)) {
    *lastCounter = incomingCounter;
    *isInitialized = true;
    return true;
  }
  if (incomingCounter > *lastCounter) {
    *lastCounter = incomingCounter;
    return true;
  }
  return false;
}

/**
 * Parses stage word strictly against allowed vocabulary: NOMINAL, MONITORING, INTERVENE.
 * Input: wordText (null-terminated string), outStage (pointer to stage output).
 * Output: true if matched, false if unrecognized.
 * Security: Rejects unknown words. Never defaults to NOMINAL on unrecognized input.
 */
static inline bool trackside_parse_stage_word(const char* wordText, uint8_t* outStage) {
  if (wordText == NULL || outStage == NULL) {
    return false;
  }
  while (*wordText == ' ' || *wordText == '\t') {
    wordText++;
  }
  char cleanWord[16];
  size_t idx = 0;
  while (*wordText != '\0' && !isspace((unsigned char)*wordText) && *wordText != '\r' && *wordText != '\n') {
    if (idx + 1 < sizeof(cleanWord)) {
      cleanWord[idx++] = (char)toupper((unsigned char)*wordText);
    } else {
      return false; // Word exceeds maximum valid token size
    }
    wordText++;
  }
  cleanWord[idx] = '\0';

  if (strcmp(cleanWord, "NOMINAL") == 0) {
    *outStage = TRACKSIDE_STAGE_NOMINAL;
    return true;
  }
  if (strcmp(cleanWord, "MONITORING") == 0) {
    *outStage = TRACKSIDE_STAGE_MONITORING;
    return true;
  }
  if (strcmp(cleanWord, "INTERVENE") == 0) {
    *outStage = TRACKSIDE_STAGE_INTERVENE;
    return true;
  }
  return false;
}

/**
 * Computes warning stage from plain g-force reading when no explicit stage word is provided.
 * Input: g (float value), fallbackThreshold (float limit).
 * Output: stage code (0 = NOMINAL, 1 = MONITORING, 2 = INTERVENE).
 * Logic: g >= limit -> INTERVENE (2), g >= 0.82 * limit -> MONITORING (1), else NOMINAL (0).
 */
static inline uint8_t trackside_classify_stage(float g, float fallbackThreshold) {
  if (g >= fallbackThreshold) {
    return TRACKSIDE_STAGE_INTERVENE;
  }
  if (g >= fallbackThreshold * 0.82f) {
    return TRACKSIDE_STAGE_MONITORING;
  }
  return TRACKSIDE_STAGE_NOMINAL;
}

/**
 * Parses a complete serial telemetry line into validated g-force and stage values.
 * Input: rawLine (raw input text), fallbackThreshold (float), outG (float*), outStage (uint8_t*).
 * Output: true if valid and parsed, false if line must be ignored.
 * Security: Discards non-numeric starts, invalid floats, out-of-range g (0..10), and unknown stages.
 */
static inline bool trackside_parse_serial_line(const char* rawLine, float fallbackThreshold, float* outG, uint8_t* outStage) {
  if (rawLine == NULL || outG == NULL || outStage == NULL) {
    return false;
  }
  while (*rawLine == ' ' || *rawLine == '\t') {
    rawLine++;
  }
  if (*rawLine == '\0') {
    return false;
  }
  if (!(isdigit((unsigned char)*rawLine) || *rawLine == '.' || *rawLine == '-')) {
    return false;
  }

  char lineBuffer[64];
  size_t copyLen = 0;
  while (*rawLine != '\0' && *rawLine != '\r' && *rawLine != '\n' && copyLen + 1 < sizeof(lineBuffer)) {
    lineBuffer[copyLen++] = *rawLine++;
  }
  lineBuffer[copyLen] = '\0';

  char* commaPos = strchr(lineBuffer, ',');
  float parsedG = 0.0f;
  uint8_t parsedStage = TRACKSIDE_STAGE_NOMINAL;

  if (commaPos != NULL) {
    *commaPos = '\0';
    char* endPtr = NULL;
    parsedG = (float)strtod(lineBuffer, &endPtr);
    if (endPtr == lineBuffer || !trackside_validate_g(parsedG)) {
      return false;
    }
    if (!trackside_parse_stage_word(commaPos + 1, &parsedStage)) {
      return false;
    }
  } else {
    char* endPtr = NULL;
    parsedG = (float)strtod(lineBuffer, &endPtr);
    if (endPtr == lineBuffer || !trackside_validate_g(parsedG)) {
      return false;
    }
    parsedStage = trackside_classify_stage(parsedG, fallbackThreshold);
  }

  *outG = parsedG;
  *outStage = parsedStage;
  return true;
}

#endif // TRACKSIDE_RADIO_PROTOCOL_H
