/**
 * Trackside — Do not start a task again while its last run is still going.
 * A poller that fires every few seconds would otherwise stack up requests when the server is slow
 * (for example while a free hosting plan wakes up), and older answers could overwrite newer ones.
 */

/** Wraps an async task: a call made while the previous call has not finished is skipped (resolves undefined). */
export function singleFlight<T>(task: () => Promise<T>): () => Promise<T | undefined> {
  let running = false;
  return async () => {
    if (running) return undefined;
    running = true;
    try {
      return await task();
    } finally {
      running = false;
    }
  };
}
