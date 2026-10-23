# Trackside on Render (free plan)

One Render web service runs everything: the website, the API and the live WebSockets. A free Render PostgreSQL database stores the data. There is no Redis and no separate frontend host: everything is on one address (`https://<name>.onrender.com`), so login cookies just work.

This is the easy, free way to show the dashboards. The server setup in `DEPLOYMENT.md` is the always-on one.

## Free-plan limits (check Render's current terms)

* The free web service **sleeps after a period with no visits**. The first visit after that takes about a minute to wake it, and an open live view drops when it sleeps.
* The free **database may expire** after a limited time. Do not keep data you cannot lose on it. Back up by exporting from Render's dashboard, or move to a paid database or an external one later.
* Free instances have a small amount of memory. The backend is light, but the first build can take several minutes.
* The Play demo runs on the server (`HOSTED_DEMO_ENABLED=true`, Coach only). The glove still needs your laptop: press **Connect bridge** in Chrome or Edge and the browser forwards the stages to the bridge (see `demo/README.md`). The free instance is small, so the demo can lag a little.

## Steps

1. **Push is already done:** the files `render.yaml` (repository root) and `trackside/Dockerfile.render` are on the `main` branch.
2. In Render's dashboard open **Blueprints** (left menu) and choose **New Blueprint Instance**. Connect your GitHub account and pick the repository `Research-Project-`, branch `main`.
3. Render reads `render.yaml` and lists one **web service** (`trackside`) and one **database** (`trackside-db`), both on the **free** plan. It asks for three values:
   * `ADMIN_EMAIL`: the email you will log in with
   * `ADMIN_NAME`: your name
   * `ADMIN_PASSWORD`: a strong password (at least 8 characters). Pick it yourself; there is no default.
4. Press **Apply** and wait. The first build takes several minutes: it builds the website, installs the backend, creates the database tables and creates your admin account.
5. When the service shows **Live**, open its address (`https://trackside-xxxx.onrender.com`, shown at the top of the service page) and log in with the admin email and password. Sign in as **Admin**.
6. **Remove the password from Render:** open the service, **Environment**, delete `ADMIN_PASSWORD`, and save. (It is only needed the first time. The admin account stays, and the password is never changed or shown again.)
7. Check it:
   * `https://<your-address>/api/health/` shows `{"status": "ok"}`
   * the login page opens and a deep link like `/coach` reloads without an error
   * in the Admin screen, create a Coach and a Driver

## Sample data (so the dashboards are not empty)

The hosted site has no live data on its own: a session only exists when a device or a demo posts readings. With `SEED_SAMPLE_DATA=true` in the service's **Environment** (the Blueprint sets it), the first start adds one finished **sample session**, clearly labelled **DEMO RUN**:

* a driver called **Sample Driver** (it has no login; nobody can sign in as it)
* the built-in **Demo Circuit**, 5 laps (240 readings) and the 9 alerts they cause (amber and red)
* it fills the Coach **Historical** tab, the Timing Tower, the track view and **Corner Deltas**; the live feed still shows offline because nothing is running right now

It never runs twice. To remove it: open the Admin screen, **Delete** the "Sample Driver" (its session goes with it), and set `SEED_SAMPLE_DATA` to `false` in Environment so it is not added again. If you did not use the Blueprint, add `SEED_SAMPLE_DATA` = `true` in Environment by hand and redeploy.

## Glove demo with this site

In Chrome or Edge: plug in the bridge, press **Connect bridge**, then **Maps & Demo > Play demo**. The server runs the virtual race and the browser drives the glove. The steps are in `demo/README.md` ("Play demo + Connect bridge"). **Connect laptop** is the fallback.

## Real map: draw a track, see the driver on it

* **Draw a track:** Maps → **Draw on map**. Zoom to the track (or type `latitude, longitude`, or press My location), click points around it in driving order (the first point is the start/finish line), press **Preview track**, name the corners, set each corner's limit (0.3 to 1.5 g) and save. It becomes a normal map: Edit corners, Play demo and the live view all use it.
* **Live position:** on the Coach page the Live Track View shows any map with real coordinates on a real map, with the corners highlighted and the driver's dot. **Plain** switches to the simple drawing (for example with no internet at the track). The **Demo Circuit** is not a real place, so it keeps the simple drawing.
* **No key needed to start:** the pictures come from OpenStreetMap, which is free but meant for light use, and the credit "© OpenStreetMap contributors" stays on the map.
* **Satellite later (needs a provider key, for example MapTiler or Mapbox):** in Render → Environment add these, then redeploy (the first three are read when the site is built):
  * `VITE_MAP_TILE_URL` = the provider's tile address with `{z}/{x}/{y}` in it, key included
  * `VITE_MAP_ATTRIBUTION` = the credit text the provider requires
  * `VITE_MAP_MAX_ZOOM` = the highest zoom the provider offers
  * `MAP_TILE_HOSTS` = the provider's host, for example `https://api.maptiler.com` (the page only loads pictures from hosts listed here)
  
  A key inside the tile address is visible to anyone who opens the site, so in the provider's dashboard **restrict the key to your site's address**. Never paste a key into chat or commit it.

## Check the login limit sees real addresses (one minute)

The login limit counts attempts per visitor address, and per account. The per-address part only works if the server reads the visitor's real address from behind Render's proxy. Sign in as **Admin** and look at **Telemetry Diagnostics > Your address, as the server sees it**:

* it should be **your own public address** (search "what is my IP" to compare). Then nothing to do;
* if it shows a Render or Cloudflare address instead, set `TRUSTED_PROXY_COUNT` in Environment to the number of proxies in front of the server (try `2`) and redeploy, then look again.

The per-account limit (10 wrong tries a minute for one email or Driver ID) works whatever this shows, so guessing one account's password is capped either way.

## Two roles at the same time

Each role has its own sign-in in the browser (separate cookies for Admin, Coach and Driver), so a driver tab and a coach tab can both stay signed in side by side in one browser. Signing in as the coach never changes the driver tab, and signing the driver out never signs the coach out. A tab changes account by itself only when the same role was signed in or out in another tab (it then shows a notice saying so).

After this update everyone signs in once more, because the old single sign-in is no longer used by the pages.

## If something goes wrong

* **Build fails:** open the service's **Logs** tab and send me the last 30 lines. Never paste a password or a `SECRET_KEY`.
* **"Bad Request (400)" page:** the address is not allowed. Render adds its own address automatically; if you use a custom domain, add it to `ALLOWED_HOSTS` in Environment, comma separated.
* **Cannot log in right after sleeping:** wait a minute for the service to wake and try again.
* **Updating the site:** push to `main`. Render rebuilds by itself.
