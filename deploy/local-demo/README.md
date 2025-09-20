Local CKAN 2.11 Demo

This compose spins up CKAN 2.11 locally on http://localhost:5000 with Postgres, Solr 8, and Redis.

Prerequisites
- Docker + Docker Compose plugin installed
- A `.env` file at the repository root (already provided by you) with at least:
  - `CKAN_SITE_URL=http://localhost:5000`
  - `POSTGRES_PASSWORD=...`
  - `BEAKER_SESSION_SECRET=...`
  - `CKAN_SYSADMIN_NAME=...`, `CKAN_SYSADMIN_EMAIL=...`, `CKAN_SYSADMIN_PASSWORD=...`

Start
1) From the repo root, bring everything up:

   docker compose -f deploy/local-demo/docker-compose.yml up -d

2) Watch init logs (optional) until the initializer finishes:

   docker compose -f deploy/local-demo/docker-compose.yml logs -f ckan-init

3) Open the site:

   http://localhost:5000

   Log in using the sysadmin credentials from `.env`.

Stopping / Cleanup
- Stop: `docker compose -f deploy/local-demo/docker-compose.yml down`
- Full reset (removes volumes): `docker compose -f deploy/local-demo/docker-compose.yml down -v`

Notes
- This setup omits the DataStore/DataPusher for simplicity. If you need previews powered by DataStore, we can extend the compose to add them.
- If your Docker Compose version does not support `depends_on.condition`, run the initializer manually first:

  docker compose -f deploy/local-demo/docker-compose.yml run --rm ckan-init
  docker compose -f deploy/local-demo/docker-compose.yml up -d ckan

