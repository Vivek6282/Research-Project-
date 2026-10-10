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
