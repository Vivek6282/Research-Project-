# Trackside frontend

## Admin: managing users

The Admin screen lists every account with its **ID** (a driver's short ID, for example `D17256`) and its login name. Create, edit, deactivate and delete are all there.

* **Edit:** change a name, an email and, for drivers, the driver ID (a letter D and 5 digits, unique). A rule that is broken is shown in the row.
* **Deactivate** is the recommended default: the person can no longer log in, and nothing is lost. Reactivate brings them back.
* **Delete** removes the person for good:
  1. Press the red **Delete** button on the row or card.
  2. The dialog shows what would be removed: sessions, readings, alerts, notes, limits (zero counts are hidden). For a coach it also shows the notes they wrote, which are deleted too. Devices are only unassigned.
  3. Type the driver ID (or the username for a coach) exactly, then press **Delete permanently**. **Deactivate instead** is one click away.
* **Safeguards:** you cannot delete your own account or any Admin account (the button is disabled), and a driver who is live right now cannot be deleted (the dialog says so and has no confirmation field). Every delete is written to the audit log.

Driver IDs also appear beside the name on the Coach screens (Timing Tower, Live Trajectory, Historical Sessions) and on the Driver dashboard.
