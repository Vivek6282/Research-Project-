# Trackside ESP32 Firmware Guide

This directory contains the ESP32 hardware firmware for the Trackside Motorsport Driver Safety & Telemetry System.

---

## 1. Board Roles

- **Trackside Bridge Unit (`trackside_bridge/trackside_bridge.ino`)**:
  - Connects to the laptop via USB Serial.
  - Receives live lateral-g telemetry stream from `virtual_lap_simulator.py`.
  - Converts incoming serial data into ESP-NOW radio packets and broadcasts them wirelessly.
- **Trackside Glove Unit (`trackside_glove/trackside_glove.ino`)**:
  - Worn on the driver's hand.
  - Receives ESP-NOW radio messages wirelessly from the Bridge board.
  - Drives a 5-segment WS2812B NeoPixel LED visual strip (Nominal / Monitoring / Intervene) and a haptic vibration motor feedback circuit.

---

## 2. Radio & Hardware Addresses (MAC Addresses)

- **Glove MAC Address**: `B0:CB:D8:0A:4F:20`
- **Bridge MAC Address**: `B0:CB:D8:0A:95:64`

### How to Find/Verify Glove MAC Address:
1. Connect the Glove ESP32 to your computer via USB.
2. Open the **Arduino Serial Monitor** set to **115200 baud**.
3. While waiting for radio messages, the Glove automatically prints its MAC address every 3 seconds:
   ```text
   GLOVE MAC ADDRESS: B0:CB:D8:0A:4F:20
   ```
4. Copy this MAC address into `trackside_bridge.ino` on the `const char* GLOVE_MAC = "..."` line if reconfiguring hardware.

---

## 3. Pinout & Hardware Wiring

### Glove Unit (`trackside_glove`)
- **LED Strip Data (`DIN`)**: GPIO 18 (`G18`) (5V WS2812B NeoPixel strip, optional 330Ω inline resistor).
- **Vibration Motor**: GPIO 26 (`G26`) driving NPN transistor (BC547 with 1kΩ base resistor + 1N4148 flyback diode across motor).
- **Power**: LED strip 5V to `VIN`/`5V`, GND to `GND`. Motor powered from 3.3V or 5V rail through transistor switch.

---

## 4. Software & Upload Instructions

1. **Environment Setup**:
   - Open **Arduino IDE**.
   - Navigate to `Tools > Board > Boards Manager...`.
   - Search for **`esp32 by Espressif Systems`** and ensure version **`3.3.x`** is installed.
2. **Library Requirements**:
   - Go to `Tools > Manage Libraries...`.
   - Search for and install **`Adafruit NeoPixel`**.
3. **Board Selection & Flash**:
   - Select Board: `Tools > Board > esp32 > ESP32 Dev Module`.
   - Select Port: `Tools > Port > (COMx / /dev/ttyUSBx)`.
   - Click **Upload** for `trackside_glove/trackside_glove.ino` and `trackside_bridge/trackside_bridge.ino` to their respective ESP32 boards.

---

## 5. Serial Protocol Format & Notes

- **Supported Inputs**:
  - `1.25` (plain g-force number)
  - `1.25,MONITORING` (g-force with explicit stage string: `NOMINAL`, `MONITORING`, or `INTERVENE`)
- **Fallback Stage Logic**: Without a stage string, the bridge uses a fixed `1.15 g` threshold limit (`<0.94g` NOMINAL, `0.94g–1.14g` MONITORING, `≥1.15g` INTERVENE).
- **Harmless MAC Output**: The Bridge board may output `00:00:00:00:00:00` for its own MAC address on certain ESP32 hardware revisions; this is completely harmless and does not affect radio transmission.
- **Port Locking Notice**: **The Arduino Serial Monitor MUST be closed before launching `virtual_lap_simulator.py`**, as only one program can hold the USB serial port at a time.
