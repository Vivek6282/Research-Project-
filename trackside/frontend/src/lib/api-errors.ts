/**
 * Trackside — Turns a server error body into one readable sentence.
 * DRF answers either {"detail": "..."} or field errors like {"password": ["Too short.", "Too common."]};
 * both become text the person can act on, instead of "Request failed with status 400".
 */

/** Field names shown in a friendlier form. */
const FIELD_LABELS: Record<string, string> = {
  password: "Password",
  email: "Email",
  name: "Name",
  driver: "Driver",
  note_text: "Note",
  goal_text: "Goal",
  non_field_errors: "",
};

/** Flatten one field's value (text, list or nested object) into short sentences. */
function flatten(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(flatten);
  if (value && typeof value === "object") return Object.values(value).flatMap(flatten);
  return [];
}

/** The best message in an error body, or the fallback when it has none. */
export function messageFromErrorBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const record = body as Record<string, unknown>;
  for (const key of ["detail", "message", "error"]) {
    if (typeof record[key] === "string" && record[key]) return record[key] as string;
  }
  const parts = Object.entries(record).flatMap(([field, value]) => {
    const label = field in FIELD_LABELS ? FIELD_LABELS[field] : field;
    return flatten(value).map((text) => (label ? `${label}: ${text}` : text));
  });
  return parts.length ? parts.slice(0, 3).join(" ") : fallback;
}
