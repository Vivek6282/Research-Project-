# Phase 2 — Which clock each time comes from (Phase 2.0, task 4)

Devices, phones and the server each have their own clock, and they can disagree
by seconds or more. Trackside keeps them apart instead of mixing them.

## Stored times

| Data | Field | Clock | Notes |
|---|---|---|---|
| Telemetry reading | `recorded_at` | Sender (simulator, phone, kart unit) | Phase 1 field, unchanged |
| Alert | `triggered_at` | Sender | Copied from the reading that caused it |
| Biometric reading | `recorded_at` | Sender | Phase 1 field, unchanged |
| Device event | `occurred_at` | Device | When it happened, by the device |
| Device event | `sequence` | Device | Rises by one per message; shows gaps and reordering |
| Device event | `received_at` | **Server** | **Authoritative for ordering** events |
| Session note | `created_at` | Server | |
| Audit log | `timestamp` | Server | |
| Device | `last_seen_at` | Server | Online status |
| Academy settings | `updated_at` | Server | |

New device payloads from Phase 2 on (events now, phone readings in 2.1) carry the
device time and the sequence number; the server adds its own receive time.

## What each screen shows

| Screen | Time shown | Clock |
|---|---|---|
| Live coach console, live map, signal strip | Reading `recorded_at` | Sender |
| Alert log, corner times, lap times, best lap | Reading / alert times | Sender |
| Admin device grid (online / last seen) | `last_seen_at` | Server |
| Audit log | `timestamp` | Server |
| Crash alert banner and crash list (Phase 2.2) | `received_at` for order and "how long ago"; `occurred_at` shown as "device time" | Both, labelled |

Lap and corner times are differences between two times from the **same** sender,
so a sender clock that is off by a constant amount does not change them.
