"""
Trackside Virtual Lap Simulator — Do not outrun the server.

Readings are posted to the server one by one. When each post takes longer than the 0.2 s between readings
(a hosted server posting to its own public address, or a slow link), a backlog builds up, and whatever is
still waiting when the run ends is lost: the live dot then stops part-way round the lap. So the simulated
clock pauses while the backlog is longer than MAX_BACKLOG readings. The run takes longer on a slow server,
but every reading arrives and the dot ends on the start/finish line.
"""

import time

import sim_backend_poster as poster

MAX_BACKLOG = 4            # readings allowed to wait before the clock pauses
MAX_PAUSE_PER_READING_S = 2.0   # one reading never holds the run for longer than this
MAX_PAUSE_PER_RUN_S = 90.0      # after this much pausing in total the server counts as dead and the run goes on
PAUSE_STEP_S = 0.02

paused_total_s = 0.0


def wait_for_backend_room() -> None:
    """Pause while the server is more than MAX_BACKLOG readings behind (a no-op when nothing is posted)."""
    global paused_total_s
    worker = poster.BACKEND_WORKER_THREAD
    if worker is None or not worker.is_alive() or poster.SHUTDOWN_EVENT.is_set():
        return
    started = time.monotonic()
    while (poster.TELEMETRY_QUEUE.qsize() > MAX_BACKLOG
           and time.monotonic() - started < MAX_PAUSE_PER_READING_S
           and paused_total_s + (time.monotonic() - started) < MAX_PAUSE_PER_RUN_S):
        time.sleep(PAUSE_STEP_S)
    paused_total_s += time.monotonic() - started
