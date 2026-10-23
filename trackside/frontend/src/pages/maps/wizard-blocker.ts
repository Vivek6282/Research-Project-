/**
 * Trackside Maps — the rules that stop a new map being saved, shared by the upload wizard and the drawing wizard.
 */

import { labelError, limitError, MAX_MAP_NAME_LENGTH } from "./safe-speed";
import type { CornerChoice, ImportPreview } from "./types";

/** The first problem that stops saving, or null when everything is valid. */
export function saveBlocker(
  preview: ImportPreview | null,
  mapName: string,
  choices: CornerChoice[],
  previewFirstMessage: string,
): string | null {
  if (!preview) return previewFirstMessage;
  if (preview.corners.length === 0) return "No corners were found. Raise the radius and preview again.";
  const name = mapName.trim();
  if (!name) return "Give the map a name.";
  if (name.length > MAX_MAP_NAME_LENGTH) return `Map name can be at most ${MAX_MAP_NAME_LENGTH} characters.`;
  const labels = choices.map((c) => c.label.trim().toLowerCase());
  if (new Set(labels).size !== labels.length) return "Each corner needs a different name.";
  const { min, max } = preview.limit_range_g;
  const bad = choices.find((c) => labelError(c.label) || limitError(c.limit, min, max));
  return bad ? `Fix corner ${bad.number}.` : null;
}

/** The corner rows to start from: the suggested names and the default limit. */
export function startingChoices(preview: ImportPreview): CornerChoice[] {
  return preview.corners.map((c) => ({
    number: c.number,
    label: c.suggested_name,
    limit: String(preview.limit_range_g.default),
  }));
}

/** The corner list the server expects when saving. */
export function choicesForServer(choices: CornerChoice[]) {
  return choices.map((c) => ({ number: c.number, label: c.label.trim(), threshold_g: Number(c.limit) }));
}
