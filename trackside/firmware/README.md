# Trackside ESP32 Firmware Guide

This directory contains the ESP32 hardware firmware for the Trackside Driver Safety & Telemetry System.

---

## 1. Board Roles & Hardware Architecture

- **Trackside Bridge Unit (`trackside_bridge/trackside_bridge.ino`)**:
  - Connects to the laptop via USB Serial.
  - Receives live lateral-g telemetry streams from `virtual_lap_simulator.py`.
  - Converts incoming serial data into ESP-NOW wireless radio packets and broadcasts them to the Glove unit.
- **Trackside Glove Unit (`trackside_glove/trackside_glove.ino`)**:
  - Worn on the driver's hand.
  - Receives ESP-NOW radio messages wirelessly from the Bridge unit.
  - Drives a 5-segment WS2812B NeoPixel LED visual strip to indicate safety stages.
  - LED-only design.

---

## 2. Hardware Wiring & Pinout

### Glove Unit (`trackside_glove`)
- **Board**: ESP32-32X board.
- **LED Strip**: WS2812B 5V addressable LED strip with 10 LEDs (only the first 5 LEDs are used as segments).
- **Data Line (`DIN`)**: Connected to GPIO 18 (`G18`) through an inline 330 ohm resistor (recommended).
- **Ground (`GND`)**: LED strip GND joined to ESP32 GND (all grounds must be shared).
- **Power (`+5V`)**: LED strip +5V powered directly from the board's 5V pin, or from a separate USB power source (such as a micro-USB breakout board) with only the grounds shared.

---

## 3. Visual Stages & Alert Levels

The glove displays real-time driver intervention levels across the 5 NeoPixel segments (ordered left-to-right: 2 Green, 2 Amber, 1 Red):

- **Nominal Stage**: 2 green LEDs steady.
- **Monitoring Stage**: 2 green LEDs steady + 2 amber LEDs flashing at 2 Hz.
- **Intervene Stage**: All 5 LEDs flashing at 2.5 Hz.
- **Waiting Stage**: One dim blue LED (pixel 0) displayed when no radio messages arrive for 1.5 seconds.
- **Photosensitivity Consideration**: All flash rates are deliberately kept at or below 3 per second on purpose (photosensitivity).

---

## 4. Radio Addresses (MAC Addresses)

ESP-NOW peer-to-peer wireless communication relies on unique hardware MAC addresses:

- **Glove MAC Address**: `B0:CB:D8:0A:4F:20`
- **Bridge MAC Address**: `B0:CB:D8:0A:95:64`

### Important Configuration Note:
The Bridge firmware line `const char* GLOVE_MAC` is specifically configured for this Glove board (`B0:CB:D8:0A:4F:20`). If the glove ESP32 board is ever replaced, the new board's MAC address must be updated in `trackside_bridge.ino` before uploading.

### Finding the Glove MAC Address:
1. Connect the Glove ESP32 to the computer via USB.
2. Open the Arduino Serial Monitor at 115200 baud.
3. While waiting for radio messages, the Glove automatically prints its MAC address every 3 seconds:
   ```text
   GLOVE MAC ADDRESS: B0:CB:D8:0A:4F:20
   ```

---

## 5. Bridge Serial Protocol & Behavior

- **Serial Input Formats**:
  - `1.25` (plain lateral-g reading)
  - `1.25,MONITORING` (lateral-g reading with explicit stage string: `NOMINAL`, `MONITORING`, or `INTERVENE`)
- **Fallback Fixed Limit**: Without a stage, the bridge uses a fixed 1.15 g limit (`< 0.94 g` Nominal, `0.94 g – 1.14 g` Monitoring, `≥ 1.15 g` Intervene).
- **Harmless MAC Output**: The Bridge board prints its own address as `00:00:00:00:00:00` during initialization on certain ESP32 hardware revisions; this is harmless and does not affect radio transmission.

---

## 6. Software Setup & Upload Instructions

1. **Arduino IDE Setup**:
   - Open **Arduino IDE**.
   - In `Tools > Board > Boards Manager...`, install **`esp32 by Espressif Systems`** version **`3.3.x`**.
2. **Library Installation**:
   - In `Tools > Manage Libraries...`, install **`Adafruit NeoPixel`**.
3. **Flashing Firmware**:
   - Board: Select **`ESP32 Dev Module`**.
   - Baud Rate: Set to **115200 baud**.
   - Port Selection: Each board gets its own COM number. **Always check Tools > Port before uploading with both boards plugged in** to ensure you are flashing the correct sketch to the intended board.

---

## 7. COM Ports & Troubleshooting

- **Bridge Port in Simulator Configuration**: In `trackside/demo/.env`, `SERIAL_PORT` must be the **BRIDGE's** port (e.g., `SERIAL_PORT=COM7`).
- **USB Behavior**: Python reports "Connected" even for the wrong board; the glove ignores USB.
- **"Access is denied" Error**: "Access is denied" means a Serial Monitor (or another program) has the port open. Close the Serial Monitor and retry.

---

## 8. Radio Security & Encryption (ESP-NOW)

The wireless ESP-NOW link between the bridge and glove is encrypted with AES-128 and protected against replay attacks and malformed input.

### Step-by-Step Setup Guide (Click-by-Click for Beginners)

#### 1. Generate Radio Secret Keys
Before compiling or uploading the sketches, generate your unique 16-byte Primary Master Key (PMK) and Local Master Key (LMK):
```bash
python firmware/tools/make_radio_keys.py
```
This automatically writes `radio_secrets.h` into both `firmware/trackside_bridge/` and `firmware/trackside_glove/`. If you forget this step and attempt to compile with unconfigured all-zero keys, the compiler will safely stop with an error prompting you to run this script.

#### 2. Upload Bridge Firmware
1. Plug your **Bridge ESP32** into your computer with a USB cable.
2. In Arduino IDE, open `firmware/trackside_bridge/trackside_bridge.ino`.
3. Verify that `GLOVE_MAC` matches your glove board's MAC address (`B0:CB:D8:0A:4F:20`).
4. Select `Tools > Port` (choose the bridge COM port).
5. Click **Upload** (the Right Arrow icon).

#### 3. Upload Glove Firmware
1. Plug your **Glove ESP32** into your computer with a USB cable.
2. In Arduino IDE, open `firmware/trackside_glove/trackside_glove.ino`.
3. Verify that `BRIDGE_MAC` matches your bridge board's MAC address (`B0:CB:D8:0A:95:64`).
4. Select `Tools > Port` (choose the glove COM port).
5. Click **Upload** (the Right Arrow icon).

#### 4. How to Tell It Worked
1. Power both boards. The glove will perform a brief self-test across all 5 LEDs and then show **one dim blue LED (WAITING)**.
2. Send test telemetry from the bridge (or launch `python demo/virtual_lap_simulator.py`).
3. As valid encrypted telemetry arrives, the glove immediately switches from the dim blue waiting light to the active signal strip:
   - **NOMINAL**: 2 steady green LEDs.
   - **MONITORING**: 2 steady green LEDs + 2 flashing amber LEDs.
   - **INTERVENE**: All 5 LEDs flashing at 2.5 Hz.

#### 5. What a Key Mismatch Looks Like & How to Fix It
- **Symptoms**: The bridge sends telemetry (`send=ok`), but the glove **stays on the single dim blue LED (WAITING)** and never updates.
- **Why this happens**: If the bridge and glove were compiled with different `radio_secrets.h` keys, the glove hardware cannot decrypt the radio frames. Dropping unauthenticated frames is the intentional, safe failure state.
- **The Fix**: Re-run `python firmware/tools/make_radio_keys.py`, then re-upload `trackside_bridge.ino` to the bridge and `trackside_glove.ino` to the glove so both boards share identical keys.

#### 6. Reject Line Diagnostics & The Beginner Spoof Test
- **What the Reject Line Means**: When rejected packets arrive, the glove logs diagnostic counter summaries over Serial at most once every 3 seconds:
  ```text
  Rejected so far: wrong_sender=2 bad_packet=0 replay=1
  ```
  - `wrong_sender`: Packet arrived from a source MAC address that does not match `BRIDGE_MAC`.
  - `bad_packet`: Packet failed length (not 10 bytes), version (not 1), stage (> 2), or acceleration checks (NaN, infinite, or out of 0.0–10.0 g range).
  - `replay`: Packet arrived with a sequence counter less than or equal to `lastPacketCounter`.
- **MAC Filtering vs. Encryption**: A MAC address can be easily forged over the air, so sender checking is only a small extra layer that blocks accidental or lazy interference from other ESP-NOW devices; AES-128 encryption with a shared key is the real protection.
- **The Beginner Spoof Test (Proving Unencrypted Spoofing Fails)**:
  1. In `firmware/trackside_bridge/trackside_bridge.ino`, change `peer.encrypt = true;` to `false`.
  2. Upload the bridge sketch to your Bridge ESP32 board.
  3. Run the simulator (`python demo/virtual_lap_simulator.py`).
  4. The glove must ignore the unencrypted packets and stay on one dim blue LED (WAITING).
  5. Change `peer.encrypt` back to `true` in `trackside_bridge.ino` and upload again to restore normal encrypted telemetry.

### Threat Model & Known Security Limits

1. **Replay Exposure Window**:
   - The bridge uses persistent non-volatile storage (`Preferences` NVS namespace `radio`) to maintain a monotonically increasing sequence counter with a 1000-packet ceiling.
   - The glove keeps `lastCounter` in RAM and strictly rejects packets with `counter <= lastCounter`.
   - **Honest disclosure on boot exposure**: After a glove reboot, the glove accepts the first valid packet it receives to establish its baseline counter. There is a theoretical one-packet exposure window upon glove reboot. However, any replayed stage lasts at most **1.5 seconds**, because the glove automatically falls back to WAITING unless continuous, strictly increasing, valid packets arrive. Furthermore, an attacker cannot forge packets without possessing the 16-byte shared LMK encryption key.
2. **Flash Storage of Keys**:
   - Radio keys reside in ESP32 flash memory. They are protected against wireless eavesdropping over the air, but remain extractable via physical chip readout unless ESP32 Hardware Flash Encryption and Secure Boot are enabled (recommended for production deployment).
3. **Encrypted Peer Limits**:
   - ESP-NOW supports a hardware maximum of encrypted peers (typically 6–17 depending on ESP-IDF configuration). For Trackside's 2-board point-to-point architecture (1 Bridge to 1 Glove), this limit is never approached.

