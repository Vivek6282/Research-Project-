/**
 * Trackside Maps — state and server calls for the corner marker editor.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../../lib/api";
import { checkMarkers, nextTurnName, toEditorMarker, toServerMarkers } from "../corner-editor-logic";
import type { CornerSuggestion, EditorMarker, EditorPayload } from "../types";

/** Loads a map's corner editor data and holds the markers being edited. */
export function useCornerEditor(trackId: string) {
  const [payload, setPayload] = useState<EditorPayload | null>(null);
  const [markers, setMarkers] = useState<EditorMarker[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [serial, setSerial] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedNote, setSavedNote] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  /** Put a fresh payload into the editor (after loading or saving). */
  const adopt = useCallback((data: EditorPayload) => {
    setPayload(data);
    setMarkers(data.markers.map((m, i) => toEditorMarker(m, i)));
    setIsDirty(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    api
      .get<EditorPayload>(`/api/tracks/${trackId}/corners/`)
      .then((data) => !cancelled && adopt(data))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the corners."))
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [trackId, adopt]);

  /** Change one marker's fields. */
  const updateMarker = useCallback((key: string, patch: Partial<EditorMarker>) => {
    setMarkers((current) => current.map((m) => (m.key === key ? { ...m, ...patch } : m)));
    setIsDirty(true);
    setSavedNote(null);
  }, []);

  /** Add a marker at an outline point (used for clicks and for accepting suggestions). */
  const addMarker = useCallback(
    (centerIndex: number, suggestion?: CornerSuggestion) => {
      if (!payload) return;
      const key = `new-${serial}`;
      setSerial((n) => n + 1);
      setMarkers((current) => [
        ...current,
        {
          key, id: null, centerIndex,
          label: suggestion && !current.some((m) => m.label.toLowerCase() === suggestion.suggested_name.toLowerCase())
            ? suggestion.suggested_name : nextTurnName(current),
          limit: String(payload.limit_range_g.default),
          length: String(payload.zone_length_m.default),
        },
      ]);
      setSelectedKey(key);
      setIsDirty(true);
      setSavedNote(null);
    },
    [payload, serial],
  );

  /** Remove a marker from the list (the server decides on save: delete, or deactivate if it has history). */
  const removeMarker = useCallback((key: string) => {
    setMarkers((current) => current.filter((m) => m.key !== key));
    setSelectedKey((current) => (current === key ? null : current));
    setIsDirty(true);
    setSavedNote(null);
  }, []);

  // The same checks the server makes, recomputed when a marker changes
  const checks = useMemo(() => (payload ? checkMarkers(markers, payload) : { byKey: {}, first: null }), [markers, payload]);

  /** Save all markers; the server re-checks everything and answers with the fresh editor data. */
  const save = useCallback(async () => {
    if (!payload || checks.first) return false;
    setIsSaving(true);
    setError(null);
    try {
      const data = await api.put<EditorPayload>(`/api/tracks/${trackId}/corners/`, {
        outline_version: payload.outline_version,
        markers: toServerMarkers(markers),
      });
      adopt(data);
      const s = data.saved;
      setSavedNote(
        s
          ? `Saved: ${s.created} added, ${s.updated} kept, ${s.deleted} removed` +
              (s.deactivated ? `, ${s.deactivated} hidden (they have telemetry or alerts, so their history is kept)` : "")
          : "Saved.",
      );
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the corners.");
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [payload, checks.first, trackId, markers, adopt]);

  return {
    payload, markers, selectedKey, setSelectedKey, isLoading, isSaving, isDirty, error, savedNote, checks,
    updateMarker, addMarker, removeMarker, save,
  };
}
