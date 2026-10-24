/**
 * Trackside phone sensors — readings waiting to be sent.
 *
 * Readings get a rising sequence number and wait here; they are sent in order, at most 100 per request.
 * When the network drops they stay queued (oldest dropped first above MAX_QUEUED, and counted) and are
 * sent when it returns, retrying with a growing delay. A refused batch (400) is dropped and counted; a
 * "stop" answer (no consent, not a real-time session) stops sending and keeps the message.
 */

export interface PhoneReading {
  recorded_at: string;
  lateral_g: number;
  speed_kmh: number;
  gps_lat: number;
  gps_lng: number;
  gps_accuracy_m: number | null;
}

export type QueuedReading = PhoneReading & { sequence: number };
export type SendResult = { kind: "ok" } | { kind: "retry" } | { kind: "reject" } | { kind: "stop"; message: string };

export const MAX_QUEUED = 3000;
export const BATCH_SIZE = 100;
export const MAX_RETRY_DELAY_MS = 30_000;

export class UploadQueue {
  private items: QueuedReading[] = [];
  private nextSequence = 0;
  private sending = false;
  private failures = 0;
  private nextTryAt = 0;
  sent = 0;
  dropped = 0;
  rejected = 0;
  stoppedMessage: string | null = null;

  constructor(private readonly send: (batch: QueuedReading[]) => Promise<SendResult>) {}

  /** Readings waiting to be sent. */
  get queued(): number {
    return this.items.length;
  }

  /** Add one reading (gets the next sequence number); drops the oldest when the queue is full. */
  push(reading: PhoneReading): void {
    if (this.stoppedMessage) return;
    this.items.push({ ...reading, sequence: this.nextSequence });
    this.nextSequence += 1;
    if (this.items.length > MAX_QUEUED) {
      this.items.shift();
      this.dropped += 1;
    }
  }

  /** Send the oldest batch if nothing is in flight and no retry delay is running. */
  async flush(nowMs: number): Promise<void> {
    if (this.sending || this.stoppedMessage || !this.items.length || nowMs < this.nextTryAt) return;
    this.sending = true;
    const batch = this.items.slice(0, BATCH_SIZE);
    try {
      const result = await this.send(batch);
      if (result.kind === "ok" || result.kind === "reject") {
        // Remove by sequence number: the oldest readings may have been dropped while this batch was in flight
        const lastSent = batch[batch.length - 1].sequence;
        this.items = this.items.filter((item) => item.sequence > lastSent);
        if (result.kind === "ok") this.sent += batch.length;
        else this.rejected += batch.length;
        this.failures = 0;
      } else if (result.kind === "stop") {
        this.stoppedMessage = result.message;
      } else {
        this.failures += 1;
        this.nextTryAt = nowMs + Math.min(MAX_RETRY_DELAY_MS, 1000 * 2 ** this.failures);
      }
    } finally {
      this.sending = false;
    }
  }
}
