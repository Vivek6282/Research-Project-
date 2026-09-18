# Trackside Virtual Lap Simulator

This utility simulates a full karting lap, corner by corner, generating realistic lateral-g data and sending it simultaneously to a Bridge ESP32 over USB Serial and to the Django backend via authenticated HTTP POST requests. 

This is perfect for live hardware demonstrations without needing a moving vehicle, as it proves out the full stack: Backend, Frontend, and ESP-NOW device meshing.

## Requirements

You must install the required dependencies:
```bash
pip install pyserial requests python-dotenv
```

## Setup & Configuration

1. **Get a Device Token:**
   - Log into the Trackside Admin Dashboard (`http://localhost:5173`) as an Administrator.
   - Provision or locate a Kart Unit and copy its `DEVICE_TOKEN`.

2. **Environment Variables (.env):**
   - Create a `.env` file in this `demo` directory (or export the variables) containing:
     ```env
     SERIAL_PORT=COM5
     SERIAL_BAUD=115200
     BACKEND_URL=http://localhost:8000
     DEVICE_TOKEN=your_device_token_here
     # SESSION_ID is optional if you use --create-session
     ```
     *(Note: Change `COM5` to your actual serial port, e.g. `/dev/ttyUSB0` on Linux/Mac).*

3. **Bridge ESP32 Firmware:**
   - Flash your ESP32 with the Trackside Bridge Firmware.
   - Connect it via USB to the computer running this script.

## Usage

### 1. Standard Run
If you already have a `SESSION_ID` defined in your `.env` file:
```bash
python virtual_lap_simulator.py
```

### 2. Auto-Create Session
Instead of manually copying a Session UUID, the script can create one on the fly. You must pass a valid Coach or Admin JWT token:
```bash
python virtual_lap_simulator.py --create-session --admin-token eyJ0eX...
```

### 3. Dry-Run (No Hardware)
To test the backend telemetry ingestion without having an ESP32 plugged in, use the `--dry-run` flag:
```bash
python virtual_lap_simulator.py --dry-run --create-session --admin-token eyJ0eX...
```

## How It Works
At startup, the simulator fetches the real Zone configurations (like the Hairpin and Sweeper) via the API to use the actual calibrated thresholds. It then runs 5 virtual laps, randomly applying driving "aggression" levels to generate a mix of clean lines, amber warnings, and red alerts.

These readings are:
- POSTed to `/api/sessions/<id>/telemetry/` where they appear on the Coach dashboard.
- Sent via USB Serial to the Bridge ESP32, which relays them over ESP-NOW to light up the Glove Unit's LEDs and buzzers in real-time.
