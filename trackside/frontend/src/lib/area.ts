/**
 * Trackside — Which role area this page belongs to.
 *
 * Each role (admin, coach, driver) has its own sign-in cookie on the server, so a driver tab and a coach tab can
 * both stay signed in in one browser. Every request says which area it belongs to with the X-Trackside-Area
 * header (live feeds use ?area=). The area is the module's own address (/driver, /coach, /admin); on pages that
 * every role shares (such as /maps) it is the one this tab signed in with, remembered for this tab only.
 */

export type Area = "admin" | "coach" | "driver";

const AREAS: Area[] = ["admin", "coach", "driver"];
const STORAGE_KEY = "trackside_area";

/** The area named by an address such as "/coach" or "/driver/anything", or null for any other address. */
export function areaFromPath(pathname: string): Area | null {
  const first = pathname.split("/")[1];
  return (AREAS as string[]).includes(first) ? (first as Area) : null;
}

/** The area this tab signed in with (kept for this tab only), or null. */
function rememberedArea(): Area | null {
  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    return (AREAS as string[]).includes(stored ?? "") ? (stored as Area) : null;
  } catch {
    return null;
  }
}

/** The area of this page: its own module address first, otherwise the one this tab signed in with. */
export function currentArea(): Area | null {
  if (typeof window === "undefined") return null;
  return areaFromPath(window.location.pathname) ?? rememberedArea();
}

/** Remember the area this tab signed in with (so shared pages such as /maps use the right sign-in). */
export function rememberArea(role: string): void {
  try {
    if ((AREAS as string[]).includes(role)) window.sessionStorage.setItem(STORAGE_KEY, role);
  } catch {
    /* a browser that refuses storage still works: module addresses carry the area */
  }
}

/** Forget the remembered area (on sign-out). */
export function forgetArea(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing to forget */
  }
}

/** A live-feed address with the page's area added (?area=driver), or unchanged when the page has none. */
export function withArea(url: string): string {
  const area = currentArea();
  return area ? `${url}${url.includes("?") ? "&" : "?"}area=${area}` : url;
}
