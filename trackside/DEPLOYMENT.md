# Trackside — Hosting Guide

One Ubuntu 24.04 server runs four containers with Docker Compose:

| Container | What it does | Reachable from |
|---|---|---|
| `caddy` | HTTPS (certificate by itself), serves the website, proxies `/api` and `/ws` | the internet, ports 80 and 443 only |
| `backend` | Django + Daphne (HTTP and live WebSockets) | inside the compose network only |
| `db` | PostgreSQL 16 | inside the compose network only |
| `redis` | live-update channel (password protected) | inside the compose network only |

Everything is configured from **one file named `.env`**, next to `docker-compose.yml`.

---

## 1. Server preparation

You need: an Ubuntu 24.04 server (2 vCPU and 2 GB memory are enough to start) and a domain (or subdomain) such as `trackside.example.com`.

1. **DNS:** create an `A` record for the domain pointing at the server's public IP address. Wait until `nslookup trackside.example.com` shows that address (Caddy cannot get a certificate before this).
2. **Firewall:** allow only SSH, HTTP and HTTPS.
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```
3. **Docker:** install Docker Engine and the Compose plugin from Docker's official instructions for Ubuntu (https://docs.docker.com/engine/install/ubuntu/), then check:
   ```bash
   docker --version
   docker compose version
   ```
   Never publish any other container port: Docker publishes ports around the firewall. The database, Redis and backend stay unpublished on purpose.

## 2. Get the code and create `.env`

```bash
git clone https://github.com/Vivek6282/Research-Project-.git /opt/trackside
cd /opt/trackside/trackside
cp .env.production.example .env
nano .env
```

Fill in every value (the file explains each one):

* `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`: generate each with
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
* `DOMAIN`, `ALLOWED_HOSTS` (keep `localhost,127.0.0.1` in the list), `CORS_ALLOWED_ORIGINS` (`https://your-domain`)
* leave `DJANGO_ENV=production`, `DEBUG=False`, `TRUSTED_PROXY_COUNT=1`

`.env` is git-ignored and is never printed in the logs. Keep a copy somewhere safe (a password manager): without it you cannot rebuild the server. See `backend/README.md` ("Production variables") for what each variable does.

## 3. Start

```bash
docker compose up -d --build
docker compose ps
```

The first build takes several minutes. The backend waits for the database, applies the migrations by itself and refuses to start if `DEBUG` is not `False`. The stack is ready when `docker compose ps` shows `backend`, `db` and `redis` as `healthy`.

## 4. Create the first Admin (one time, by hand)

Nothing creates a user automatically and there is no default password. `seed_admin` reads the email and password from the environment of that one command, so type the password without putting it on the command line:

```bash
read -r -s -p "Admin password (min 8 characters): " ADMIN_PASSWORD; echo; export ADMIN_PASSWORD
docker compose run --rm -e ADMIN_EMAIL=you@example.com -e ADMIN_NAME="Your Name" -e ADMIN_PASSWORD backend python manage.py seed_admin
unset ADMIN_PASSWORD
```

It prints one line and never prints the password:

```
Admin account created: you@example.com (Your Name) with login ID TRK-ADMIN-000001
```

Running it again does not change the password (it prints that the account already exists). To change an account's password later:

```bash
docker compose run --rm backend python manage.py changepassword you@example.com
```

## 5. Verify (checklist)

1. **Health:** `curl -fsS https://trackside.example.com/api/health/` prints `{"status":"ok"}`.
2. **Certificate:** the browser shows a padlock for the domain (the first visit can take a few seconds while Caddy gets the certificate). `http://` redirects to `https://`.
3. **Website:** the login page opens; a deep link such as `https://trackside.example.com/coach` reloads without an error.
4. **Login:** sign in with the Admin you created. Open the Admin screen and create a Coach.
5. **Live WebSocket view:** as Coach, open the live tab and select a driver who has a session. The header shows **LIVE WS STREAM** (not "LIVE FEED OFFLINE"). Until a device or a run is posting data there is no session to watch, so repeat this check when the first one exists.
6. **Ports:** from another computer only 80 and 443 answer (`nmap -p 22,80,443,5432,6379,8000 your-domain`).

## 6. Update

```bash
cd /opt/trackside/trackside
git pull
docker compose up -d --build
```

Migrations run automatically when the backend starts. Take a backup first (section 7).

## 7. Backups and restore

Backups are `pg_dump -Fc` files in `trackside/backups/` (git-ignored); the newest 14 are kept. No password is printed.

```bash
./scripts/backup.sh
```

**Nightly backup:** add one line with `crontab -e` (runs at 03:15):

```
15 3 * * * cd /opt/trackside/trackside && ./scripts/backup.sh >> backups/backup.log 2>&1
```

**Restore** (replaces the current data; stops the backend while it runs):

```bash
./scripts/restore.sh backups/trackside-20261022-031500.dump
```

It asks you to type `RESTORE`. **Test this once before you rely on it:** make a backup, add a throw-away user in the Admin screen, restore the backup, and check that the user is gone. Copy backups off the server too; a backup on the same disk does not survive losing the server.

## 8. Rollback

1. Find the version to return to: `git log --oneline` or `git tag`.
2. `git checkout <tag-or-commit>` then `docker compose up -d --build`.
3. Only if the newer version applied a migration that must be undone: restore the backup taken before the update (section 7). Otherwise leave the data alone.

To go forward again: `git checkout main && git pull && docker compose up -d --build`.

## 9. Logs

```bash
docker compose logs -f backend        # the application
docker compose logs -f caddy          # HTTPS, certificate and proxy messages
docker compose logs --tail 100 db     # the database
docker compose ps                     # state and health of every container
```

Logs rotate by themselves (10 MB, 5 files per container).

## 10. What is not available when hosted

* **The Play demo, the demo Start/Stop control and "Open live visualizer"** only work on the laptop that has the bridge. The server refuses the demo endpoints in production and the hosted website is built without the demo controls.
* **The visualizer's local stream** (the simulator's own WebSocket on the laptop) is not part of the hosted site.
* **The glove** never talks to the server; it works from the bridge and the laptop.
* A laptop simulator posting to the hosted server (`BACKEND_URL=https://your-domain`) needs a device token and a session, and there is no supported way to create them on a production server yet. Until that is designed, run the glove demo locally and use the hosted site for the dashboards.
