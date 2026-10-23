/**
 * Trackside Maps — state and actions for the "Draw on map" wizard (click points -> review -> save).
 * The clicked points are sent to both the preview and the save call; the server builds the smooth outline
 * from them each time and never trusts an outline sent by the browser.
 */

import { useCallback, useMemo, useState } from "react";
import { api } from "../../../lib/api";
import { choicesForServer, saveBlocker, startingChoices } from "../wizard-blocker";
import type { CornerChoice, ImportPreview, LatLng } from "../types";

export const MIN_DRAWN_POINTS = 8;
export const MAX_DRAWN_POINTS = 1000;
const DEFAULT_RADIUS = "60";

/** A point rounded to about a centimetre, as the server stores it. */
function tidy(point: LatLng): LatLng {
  return { lat: Number(point.lat.toFixed(7)), lng: Number(point.lng.toFixed(7)) };
}

/** Holds the clicked points, the preview and the edits, and talks to the draw endpoints. */
export function useDrawWizard(onSaved: () => void) {
  const [points, setPoints] = useState<LatLng[]>([]);
  const [radius, setRadius] = useState(DEFAULT_RADIUS);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [choices, setChoices] = useState<CornerChoice[]>([]);
  const [mapName, setMapName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Add a clicked point at the end (ignored once the limit is reached). */
  const addPoint = useCallback((point: LatLng) => {
    setError(null);
    setPoints((current) => (current.length >= MAX_DRAWN_POINTS ? current : [...current, tidy(point)]));
  }, []);

  /** Move one point (after it was dragged). */
  const movePoint = useCallback((index: number, point: LatLng) => {
    setPoints((current) => current.map((p, i) => (i === index ? tidy(point) : p)));
  }, []);

  /** Remove the last point. */
  const undo = useCallback(() => setPoints((current) => current.slice(0, -1)), []);

  /** Remove every point. */
  const clear = useCallback(() => {
    setPoints([]);
    setError(null);
  }, []);

  /** Send the points and show the smooth track and its corners; nothing is saved yet. */
  const runPreview = useCallback(async () => {
    const radiusValue = Number(radius);
    if (points.length < MIN_DRAWN_POINTS) return setError(`Click at least ${MIN_DRAWN_POINTS} points around the track.`);
    if (!Number.isFinite(radiusValue)) return setError("The corner radius must be a number.");
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<ImportPreview>("/api/tracks/draw/preview/", { points, corner_radius_m: radiusValue });
      setPreview(result);
      setChoices(startingChoices(result));
    } catch (e) {
      setPreview(null);
      setError(e instanceof Error ? e.message : "Could not build the track from those points.");
    } finally {
      setBusy(false);
    }
  }, [points, radius]);

  /** Change one corner's name or limit. */
  const changeChoice = useCallback((number: number, patch: Partial<CornerChoice>) => {
    setChoices((current) => current.map((c) => (c.number === number ? { ...c, ...patch } : c)));
  }, []);

  const blocker = useMemo(
    () => saveBlocker(preview, mapName, choices, "Preview the track first."),
    [preview, mapName, choices],
  );

  /** Save the map. The server checks everything again and answers with a clear error if needed. */
  const save = useCallback(async () => {
    if (!preview || blocker) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/tracks/draw/confirm/", {
        points,
        name: mapName.trim(),
        corner_radius_m: preview.corner_radius_m,
        corners: choicesForServer(choices),
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the map.");
    } finally {
      setBusy(false);
    }
  }, [points, preview, blocker, mapName, choices, onSaved]);

  return {
    points, addPoint, movePoint, undo, clear, radius, setRadius, preview, choices, changeChoice,
    mapName, setMapName, busy, error, setError, blocker, runPreview, save,
    canPreview: points.length >= MIN_DRAWN_POINTS,
    backToDrawing: () => setPreview(null),
  };
}
