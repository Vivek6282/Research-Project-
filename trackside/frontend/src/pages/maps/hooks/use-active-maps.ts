/**
 * Trackside Maps — the active (not archived) maps with their corner names, for pickers.
 */

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import type { MapTrack } from "../types";

/** Loads the active maps once, sorted by name. */
export function useActiveMaps() {
  const [maps, setMaps] = useState<MapTrack[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ results?: MapTrack[] } | MapTrack[]>("/api/tracks/")
      .then((res) => {
        if (cancelled) return;
        const rows = Array.isArray(res) ? res : res.results ?? [];
        setMaps([...rows].sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the maps."))
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return { maps, isLoading, error };
}
