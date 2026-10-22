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

## If something goes wrong

* **Build fails:** open the service's **Logs** tab and send me the last 30 lines. Never paste a password or a `SECRET_KEY`.
* **"Bad Request (400)" page:** the address is not allowed. Render adds its own address automatically; if you use a custom domain, add it to `ALLOWED_HOSTS` in Environment, comma separated.
* **Cannot log in right after sleeping:** wait a minute for the service to wake and try again.
* **Updating the site:** push to `main`. Render rebuilds by itself.
