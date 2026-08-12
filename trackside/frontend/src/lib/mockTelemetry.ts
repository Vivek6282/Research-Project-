/**
 * Trackside — Isolated Mock Telemetry Generator
 *
 * Simulates 20Hz speed variations, lateral G-force oscillations, and biometrics
 * for demo/testing when physical IoT hardware is offline.
 *
 * Easy to remove permanently by deleting this single file.
 */

export interface DriverState {
  baseSpeed: number;
  baseHr: number;
  baseSpo2: number;
  baseBreathing: number;
  inPit?: boolean;
}

export interface TelemetryPacket {
  speed: number;
  gForce: number;
  hr: number;
  spo2: number;
  breathing: number;
  oscilloscopeVal: number;
}

export function startMockTelemetryEngine(
  driver: DriverState,
  onUpdate: (packet: TelemetryPacket) => void
): () => void {
  const interval = setInterval(() => {
    const time = Date.now() / 300;

    let speed = 0;
    let gForce = 0.0;

    if (driver.inPit) {
      speed = 0;
      gForce = 0.0;
    } else {
      const speedVar = Math.round(driver.baseSpeed + Math.sin(time) * 14 + (Math.random() * 3 - 1.5));
      speed = Math.max(45, Math.min(145, speedVar));
      gForce = Number((1.1 + Math.abs(Math.sin(time * 0.8)) * 0.65).toFixed(2));
    }

    const hr = Math.round(driver.baseHr + Math.sin(time * 0.5) * 4 + (Math.random() * 2 - 1));
    const spo2 = Math.min(99, Math.max(94, Math.round(driver.baseSpo2 + (Math.random() * 0.6 - 0.3))));
    const breathing = Math.round(driver.baseBreathing + (Math.random() * 1.6 - 0.8));

    const oscVal = driver.inPit
      ? 140
      : 160 - ((speed / 140) * 120 + (Math.random() * 8 - 4));

    onUpdate({
      speed,
      gForce,
      hr,
      spo2,
      breathing,
      oscilloscopeVal: Math.max(20, Math.min(150, oscVal)),
    });
  }, 200);

  return () => clearInterval(interval);
}
