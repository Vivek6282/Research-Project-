/**
 * Trackside Maps — state and actions for the Add map wizard (upload -> review -> save).
 * The same file is sent to both the preview and the save call; the server re-reads it.
 */

import { useCallback, useMemo, useState } from "react";
import { api } from "../../../lib/api";
import { choicesForServer, saveBlocker, startingChoices } from "../wizard-blocker";
import type { CornerChoice, ImportPreview } from "../types";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const DEFAULT_RADIUS = "60";

/** Holds the wizard's file, preview and edits, and talks to the import endpoints. */
export function useImportWizard(onSaved: () => void) {
  const [file, setFile] = useState<File | null>(null);
  const [radius, setRadius] = useState(DEFAULT_RADIUS);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [choices, setChoices] = useState<CornerChoice[]>([]);
  const [mapName, setMapName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Pick a file; refuse the wrong type or size before any upload. */
  const pickFile = useCallback((picked: File | null) => {
    setError(null);
    setPreview(null);
    if (!picked) return setFile(null);
    if (!/\.(csv|vbo)$/i.test(picked.name)) {
      setFile(null);
      return setError("Choose a .csv (RaceChrono) or .vbo (Racelogic) file.");
    }
    if (picked.size > MAX_FILE_BYTES) {
      setFile(null);
      return setError("That file is larger than 5 MB.");
    }
    setFile(picked);
  }, []);

  /** Upload the file and show what it contains; nothing is saved yet. */
  const runPreview = useCallback(async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("corner_radius_m", radius);
      const result = await api.upload<ImportPreview>("/api/tracks/import/preview/", form);
      setPreview(result);
      setChoices(startingChoices(result));
      setMapName((previous) => previous || result.track_name || result.session_title || "");
    } catch (e) {
      setPreview(null);
      setError(e instanceof Error ? e.message : "Could not read that file.");
    } finally {
      setBusy(false);
    }
  }, [file, radius]);

  /** Change one corner's name or limit. */
  const changeChoice = useCallback((number: number, patch: Partial<CornerChoice>) => {
    setChoices((current) => current.map((c) => (c.number === number ? { ...c, ...patch } : c)));
  }, []);

  /** First problem that stops saving, or null when everything is valid. */
  const blocker = useMemo(() => saveBlocker(preview, mapName, choices, "Preview a file first."), [preview, mapName, choices]);

  /** Save the map. The server checks everything again and answers with a clear error if needed. */
  const save = useCallback(async () => {
    if (!file || !preview || blocker) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("name", mapName.trim());
      form.append("corner_radius_m", String(preview.corner_radius_m));
      form.append("corners", JSON.stringify(choicesForServer(choices)));
      await api.upload("/api/tracks/import/confirm/", form);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the map.");
    } finally {
      setBusy(false);
    }
  }, [file, preview, blocker, mapName, choices, onSaved]);

  return {
    file, pickFile, radius, setRadius, preview, choices, changeChoice,
    mapName, setMapName, busy, error, blocker, runPreview, save,
    backToUpload: () => setPreview(null),
  };
}
