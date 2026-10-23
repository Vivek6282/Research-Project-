/**
 * Trackside — Remove old browser caches of private data.
 *
 * Earlier versions let the service worker keep API replies (including /api/auth/me/) for 24 hours.
 * That cache is shared by every account that uses the browser, so it is deleted on start and on
 * logout. Nothing writes to it any more.
 */

const OLD_API_CACHE_NAME = "trackside-api-cache";

/** Delete the old API cache. Safe to call anywhere; it does nothing where the Cache API is missing. */
export async function clearPrivateCaches(): Promise<void> {
  try {
    if (typeof caches !== "undefined") {
      await caches.delete(OLD_API_CACHE_NAME);
    }
  } catch {
    // A browser that refuses cache access has nothing to clear.
  }
}
