# ForProfitEMS.com

Portable test build: a Python 3 application with SQLite, a provider directory, moderated resident/employee reviews, and unlisted-provider reporting. No external packages or hosted-platform dependencies.

## Run

Requires Python 3.10 or newer. From this folder:

```sh
export ADMIN_PASSWORD='choose-a-long-unique-password'
python3 server.py
```

Open http://localhost:8080. The admin link opens the password-protected moderation desk. Without ADMIN_PASSWORD the public site works but admin login is disabled. Three fictional providers are seeded on a fresh database. No fabricated reviews are seeded.

## Workflow

- Directory filters by company/parent text, state, and parent company.
- Each provider profile is scoped to a company and state; parent company is displayed and searchable.
- Resident reviews cover billing, no-haul billing, and other experiences.
- Employer reviews cover treatment, profit sharing, benefits/cost, management access, and sourced ownership/assets.
- Reviews and unlisted-provider reports persist in SQLite and start pending.
- Admin approval publishes reviews or creates a provider listing. Reviews can be rejected or returned to pending. Rejecting an already approved provider report does not delete its provider listing.
- Ratings describe the contributor's experience: 1 very poor through 5 very good.

## Export / server

Copy this complete directory to your server. The database defaults to `data/site.db`; persist and back up that directory. Set DATABASE_PATH to change it. Set HOST=0.0.0.0 for container/network use and PORT to change the port. Run behind an HTTPS reverse proxy and set COOKIE_SECURE=1 when using HTTPS. Point ForProfitEMS.com to that server after configuring your DNS and certificate. This build does not modify your domain.

A Dockerfile is included. Build with `docker build -t forprofit-ems .` and run with a persistent volume at `/app/data` and ADMIN_PASSWORD passed through your deployment secret manager.

## Test-build boundaries

This is a single-server pilot using Python's standard HTTP server, not a hardened public deployment. Before opening to unrestricted public traffic, replace the HTTP server with a production app server, add durable per-user moderator accounts/audit history, submission rate limiting/spam protection, provider editing and correction handling, and operational monitoring. Sessions are in memory and expire after 8 hours; restarting signs moderators out. Login attempts are throttled by client IP; public submissions are not yet rate limited. There are no uploads, email collection, email notifications, or patient record storage. Do not submit private health information.

Ownership and assets are submitted as sourced community reports, not automatically verified facts. Moderation is manual. Demo listings should be removed from the SQLite providers table before entering real data; back up the database first. The initial database is intentionally excluded from Git and export archives.

## Verification

Run `python3 -m unittest discover -s tests`. Tests use an isolated temporary database.
