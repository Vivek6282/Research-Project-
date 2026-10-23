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

## Real map (Leaflet): drawing a track and the live position

* **Drawing:** `Maps → Draw on map` opens `pages/maps/components/draw-map-wizard.tsx`. Clicks become points (`hooks/use-draw-wizard.ts`, 8 to 1,000 points, draggable); Preview sends them to `/api/tracks/draw/preview/`, and the review step is the same one the file upload uses (`wizard-review.tsx`), so corner names, limits and the save rules are shared (`wizard-blocker.ts`).
* **Live view:** `components/ui/live-track-view.tsx` shows a track with real coordinates on `live-track/gps-map-canvas.tsx` (track line, corner arcs, S/F flag, the driver's dot at its real latitude and longitude). A Map / Plain switch (remembered in this browser) falls back to the simple SVG drawing. The built-in Demo Circuit is schematic (no real place) and always uses the simple drawing.
* **Loading:** Leaflet is a separate chunk (about 44 KB compressed) loaded only when a map is shown or the wizard opens. Its style file is bundled; the only thing fetched from another site is the map pictures.
* **Picture source:** `src/lib/map-tiles.ts`. Default OpenStreetMap (no key). Build-time settings `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION`, `VITE_MAP_MAX_ZOOM` change it; the server must also allow the host (`MAP_TILE_HOSTS`, see `backend/README.md`). A key in the address is public, so restrict it to the site at the provider.
* **Checks:** the corner highlights are placed by `live-track/gps-corner-arcs.ts` (unit tested); the map itself is checked in a real browser, because Leaflet needs real layout.
