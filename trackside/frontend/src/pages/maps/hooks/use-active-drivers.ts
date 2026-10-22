/**
 * Trackside Maps — the active drivers a demo can be played for (deactivated drivers are left out).
 */

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

export interface DriverOption {
  id: string;
  name: string;
}

interface RosterResponse {
  roster?: { driver_id: string; driver_name: string; is_active?: boolean }[];
}

/** Loads the roster once and keeps the active drivers, sorted by name. */
export function useActiveDrivers() {
  const [drivers, setDrivers] = useState<DriverOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<RosterResponse>("/api/sessions/roster-status/")
      .then((res) => {
        if (cancelled) return;
        const active = (res.roster ?? []).filter((r) => r.is_active !== false);
        setDrivers(active.map((r) => ({ id: r.driver_id, name: r.driver_name })).sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the drivers."))
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return { drivers, error, isLoading };
}
