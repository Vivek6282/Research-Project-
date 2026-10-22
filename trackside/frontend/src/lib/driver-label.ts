/**
 * Trackside — Driver label.
 * "Marco Ferrati · D17256" when the driver has an ID, otherwise just the name.
 */

/** The name followed by the driver ID, or only the name when there is no ID. */
export function driverLabel(name: string, driverCode?: string | null): string {
  return driverCode ? `${name} · ${driverCode}` : name;
}
