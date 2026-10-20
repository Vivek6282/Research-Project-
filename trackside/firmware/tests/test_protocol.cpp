/**
 * Trackside Firmware Protocol Host Tests
 * --------------------------------------
 * Tests packet serialization, validation, replay protection, and serial line parsing.
 * Written in standard C++11 for host compilation using plain g++ (no Arduino dependencies).
 */

#include <iostream>
#include <cassert>
#include <cmath>
#include <cstring>
#include <vector>
#include <string>

#include "trackside_radio_protocol.h"

static int gPassedTestCount = 0;
static int gFailedTestCount = 0;

#define TEST_ASSERT(cond, message) do { \
  if (cond) { \
    gPassedTestCount++; \
  } else { \
    gFailedTestCount++; \
    std::cerr << "  [FAIL] " << message << " (" << #cond << " at line " << __LINE__ << ")" << std::endl; \
  } \
} while(0)

// Helper to construct a raw RadioPacket byte vector
std::vector<uint8_t> makeRawPacket(uint8_t version, uint8_t stage, float g, uint32_t counter) {
  RadioPacket pkt;
  pkt.version = version;
  pkt.stage = stage;
  pkt.g = g;
  pkt.counter = counter;
  std::vector<uint8_t> bytes(sizeof(RadioPacket));
  std::memcpy(bytes.data(), &pkt, sizeof(RadioPacket));
  return bytes;
}

void testReplayGuardCounterEqualRejected() {
  uint32_t lastCounter = 0;
  bool isInitialized = false;

  // Initial packet sets baseline counter to 100
  bool initResult = trackside_check_replay_guard(100, &lastCounter, &isInitialized);
  TEST_ASSERT(initResult == true, "Baseline counter 100 accepted");
  TEST_ASSERT(lastCounter == 100, "lastCounter set to 100");

  // Replay packet with identical counter 100 must be rejected (G4, G7)
  bool equalResult = trackside_check_replay_guard(100, &lastCounter, &isInitialized);
  TEST_ASSERT(equalResult == false, "Counter equal rejected");
  TEST_ASSERT(lastCounter == 100, "lastCounter unchanged on equal counter rejection");
}

void testReplayGuardCounterLowerRejected() {
  uint32_t lastCounter = 0;
  bool isInitialized = false;

  trackside_check_replay_guard(100, &lastCounter, &isInitialized);

  // Replayed packet with lower counter 99 must be rejected (G4, G7)
  bool lowerResult = trackside_check_replay_guard(99, &lastCounter, &isInitialized);
  TEST_ASSERT(lowerResult == false, "Counter lower rejected");
  TEST_ASSERT(lastCounter == 100, "lastCounter unchanged on lower counter rejection");
}

void testReplayGuardCounterHigherAccepted() {
  uint32_t lastCounter = 0;
  bool isInitialized = false;

  trackside_check_replay_guard(100, &lastCounter, &isInitialized);

  // Fresh packet with higher counter 101 must be accepted (G4, G7)
  bool higherResult = trackside_check_replay_guard(101, &lastCounter, &isInitialized);
  TEST_ASSERT(higherResult == true, "Counter higher accepted");
  TEST_ASSERT(lastCounter == 101, "lastCounter updated to 101");
}

void testFirstPacketAccepted() {
  uint32_t lastCounter = 0;
  bool isInitialized = false;

  // The very first packet after boot must always be accepted (G4, G7)
  bool firstResult = trackside_check_replay_guard(42, &lastCounter, &isInitialized);
  TEST_ASSERT(firstResult == true, "First packet accepted regardless of counter magnitude");
  TEST_ASSERT(isInitialized == true, "State flag initialized");
  TEST_ASSERT(lastCounter == 42, "lastCounter set to first packet value");
}

void testVersion2Rejected() {
  auto bytes = makeRawPacket(2, TRACKSIDE_STAGE_INTERVENE, 1.35f, 10);
  RadioPacket outPacket;
  bool valid = trackside_validate_packet(bytes.data(), bytes.size(), &outPacket);
  TEST_ASSERT(valid == false, "Packet with version 2 rejected (must be 1)");
}

void testStage3Rejected() {
  auto bytes = makeRawPacket(1, 3, 1.25f, 10);
  RadioPacket outPacket;
  bool valid = trackside_validate_packet(bytes.data(), bytes.size(), &outPacket);
  TEST_ASSERT(valid == false, "Packet with stage 3 rejected (allowed: 0, 1, 2)");
}

void testNanRejected() {
  float nanValue = std::nanf("");
  TEST_ASSERT(trackside_validate_g(nanValue) == false, "validate_g rejects NaN");

  auto bytes = makeRawPacket(1, TRACKSIDE_STAGE_NOMINAL, nanValue, 10);
  RadioPacket outPacket;
  bool valid = trackside_validate_packet(bytes.data(), bytes.size(), &outPacket);
  TEST_ASSERT(valid == false, "Packet with NaN g rejected");
}

void testG105Rejected() {
  TEST_ASSERT(trackside_validate_g(10.5f) == false, "validate_g rejects 10.5g");

  auto bytes = makeRawPacket(1, TRACKSIDE_STAGE_NOMINAL, 10.5f, 10);
  RadioPacket outPacket;
  bool valid = trackside_validate_packet(bytes.data(), bytes.size(), &outPacket);
  TEST_ASSERT(valid == false, "Packet with g=10.5 rejected (>10.0 limit)");
}

void testGarbageStageWordRejected() {
  uint8_t stage = 99;
  bool parsed = trackside_parse_stage_word("garbage", &stage);
  TEST_ASSERT(parsed == false, "parse_stage_word rejects 'garbage'");
  TEST_ASSERT(stage == 99, "Stage variable unchanged on rejection");

  float g = 0.0f;
  uint8_t parsedStage = 99;
  bool lineValid = trackside_parse_serial_line("1.9,garbage", 1.15f, &g, &parsedStage);
  TEST_ASSERT(lineValid == false, "parse_serial_line rejects '1.9,garbage' (never defaults to NOMINAL)");
}

void testInterveneAccepted() {
  uint8_t stage = 99;
  bool parsed = trackside_parse_stage_word("intervene", &stage);
  TEST_ASSERT(parsed == true, "parse_stage_word accepts lowercase 'intervene'");
  TEST_ASSERT(stage == TRACKSIDE_STAGE_INTERVENE, "Stage mapped to INTERVENE (2)");

  float g = 0.0f;
  uint8_t parsedStage = 99;
  bool lineValid = trackside_parse_serial_line("1.4,intervene", 1.15f, &g, &parsedStage);
  TEST_ASSERT(lineValid == true, "parse_serial_line accepts '1.4,intervene'");
  TEST_ASSERT(parsedStage == TRACKSIDE_STAGE_INTERVENE, "Parsed stage is INTERVENE");
  TEST_ASSERT(std::abs(g - 1.4f) < 0.001f, "Parsed g is 1.4");
}

void testAdditionalEdgeCases() {
  // Length mismatch
  uint8_t shortBuf[5] = {1, 0, 0, 0, 0};
  RadioPacket out;
  TEST_ASSERT(trackside_validate_packet(shortBuf, sizeof(shortBuf), &out) == false, "Short packet rejected");
  TEST_ASSERT(trackside_validate_packet(NULL, sizeof(RadioPacket), &out) == false, "NULL buffer rejected");

  // Infinite values
  float infValue = INFINITY;
  TEST_ASSERT(trackside_validate_g(infValue) == false, "validate_g rejects positive infinity");
  TEST_ASSERT(trackside_validate_g(-infValue) == false, "validate_g rejects negative infinity");
  TEST_ASSERT(trackside_validate_g(-0.1f) == false, "validate_g rejects negative g");

  // Fallback stage classification
  TEST_ASSERT(trackside_classify_stage(1.20f, 1.15f) == TRACKSIDE_STAGE_INTERVENE, "1.20g >= 1.15g is INTERVENE");
  TEST_ASSERT(trackside_classify_stage(1.00f, 1.15f) == TRACKSIDE_STAGE_MONITORING, "1.00g >= 0.943g is MONITORING");
  TEST_ASSERT(trackside_classify_stage(0.80f, 1.15f) == TRACKSIDE_STAGE_NOMINAL, "0.80g < 0.943g is NOMINAL");

  // Plain serial line classification without stage word
  float g = 0.0f;
  uint8_t stage = 99;
  TEST_ASSERT(trackside_parse_serial_line("1.25", 1.15f, &g, &stage) == true, "Plain '1.25' line parsed");
  TEST_ASSERT(stage == TRACKSIDE_STAGE_INTERVENE, "Plain '1.25' classified as INTERVENE");
}

void testSenderCheck() {
  const uint8_t expectedMac[6] = {0xB0, 0xCB, 0xD8, 0x0A, 0x95, 0x64};
  const uint8_t matchingMac[6] = {0xB0, 0xCB, 0xD8, 0x0A, 0x95, 0x64};
  const uint8_t differentMac[6] = {0xB0, 0xCB, 0xD8, 0x0A, 0x95, 0x65}; // Last byte differs

  // Matching MAC accepted
  TEST_ASSERT(trackside_is_expected_sender(matchingMac, expectedMac) == true, "Matching MAC accepted");

  // One-byte-different MAC rejected
  TEST_ASSERT(trackside_is_expected_sender(differentMac, expectedMac) == false, "One-byte-different MAC rejected");

  // Null source rejected
  TEST_ASSERT(trackside_is_expected_sender(NULL, expectedMac) == false, "Null source rejected");

  // Null expected rejected
  TEST_ASSERT(trackside_is_expected_sender(matchingMac, NULL) == false, "Null expected rejected");
}

int main() {
  std::cout << "==================================================" << std::endl;
  std::cout << " TRACKSIDE FIRMWARE PROTOCOL SECURITY UNIT TESTS  " << std::endl;
  std::cout << "==================================================" << std::endl;

  testReplayGuardCounterEqualRejected();
  testReplayGuardCounterLowerRejected();
  testReplayGuardCounterHigherAccepted();
  testFirstPacketAccepted();
  testVersion2Rejected();
  testStage3Rejected();
  testNanRejected();
  testG105Rejected();
  testGarbageStageWordRejected();
  testInterveneAccepted();
  testAdditionalEdgeCases();
  testSenderCheck();

  std::cout << "--------------------------------------------------" << std::endl;
  std::cout << "Total assertions passed: " << gPassedTestCount << std::endl;
  std::cout << "Total assertions failed: " << gFailedTestCount << std::endl;
  std::cout << "--------------------------------------------------" << std::endl;

  if (gFailedTestCount == 0) {
    std::cout << "RESULT: ALL TESTS PASSED (11/11 Core Scenarios Verified)" << std::endl;
    return 0;
  } else {
    std::cerr << "RESULT: TESTS FAILED (" << gFailedTestCount << " failures)" << std::endl;
    return 1;
  }
}
