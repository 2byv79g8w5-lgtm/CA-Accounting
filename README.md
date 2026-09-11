# Grain Basis Contract Accounting

A standalone app for managing grain basis contracts, pricing events, deliveries,
and settlements — with settlements posting as journal entries into Odoo's
accounting via Odoo's external API.

This is a **scaffold**, not a finished product. It has the data model, basic
CRUD endpoints, and the computed logic for running totals / weighted averages
in place. The Odoo integration is stubbed out (see `app/odoo_client.py`) since
Odoo isn't set up yet — wire it up once you have a live instance to test against.

## Stack

- **FastAPI** — backend API
- **SQLAlchemy** — ORM / data model
- **Postgres** — database (works with SQLite for local dev too, see below)
- **Pydantic** — request/response validation

## Project layout

```
app/
  main.py           FastAPI app entrypoint
  database.py       DB engine/session setup
  models.py         SQLAlchemy models (the 6 core objects)
  schemas.py        Pydantic request/response schemas
  odoo_client.py    Odoo API integration (STUBBED — build this once Odoo exists)
  services/
    settlement.py   Weighted-average price, running totals, settlement math
  routers/
    commodities.py
    contracts.py
    pricing_events.py
    delivery_tickets.py
    grade_schedules.py
    settlements.py
init_db.py          One-off script to create tables
requirements.txt
.env.example
```

## Setup

1. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   For local development without Postgres installed, you can leave
   `DATABASE_URL` pointed at the default SQLite file — it'll just work.
   Switch to a real Postgres URL when you deploy (e.g. on Render, which
   provisions a `DATABASE_URL` for you automatically if you add their
   Postgres add-on).

   Leave the `ODOO_*` variables blank until Odoo is set up — the app will
   run fine without them; the Odoo client just won't be able to connect yet.

3. **Create the database tables**

   ```bash
   python init_db.py
   ```

4. **Run the app**

   ```bash
   uvicorn app.main:app --reload
   ```

   Visit `http://localhost:8000/docs` for interactive API docs (FastAPI
   generates this automatically from the schemas — it's the fastest way to
   poke at the endpoints while building the UI).

## What's built vs. what's next

**Built:**
- Full data model for all 6 objects from the design doc (Commodity, Basis
  Contract, Pricing Event, Delivery Ticket, Grade Adjustment Schedule,
  Settlement)
- CRUD endpoints for all of them
- Settlement math: weighted-average futures price from pricing events,
  running totals for quantity priced/delivered, grade adjustment lookup
- A lightweight local cache table for grower info (`GrowerRef`) — Odoo's
  `res.partner` stays the source of truth; this just stores the Odoo partner
  ID plus a display name so contracts can reference a grower without a live
  API call on every read

**Not built yet (by design — needs a live Odoo instance to build against):**
- The actual Odoo API calls in `odoo_client.py` (authentication, creating
  `account.move` records, looking up `res.partner`)
- The settlement → journal entry account mapping (which GL accounts get
  debited/credited — this is an accounting policy decision, see the
  `TODO` in `app/odoo_client.py`)
- A frontend UI (the API is usable as-is via `/docs`, but there's no
  browser UI for data entry yet)
- Authentication/authorization on the API itself
- Alembic migrations (currently using a blunt `create_all` — fine for now,
  worth adding once the schema stabilizes and you need to evolve it without
  dropping data)

## Next steps

1. Get Odoo running (Odoo.sh, their cloud hosting, or self-hosted) with the
   Accounting app enabled.
2. Fill in `app/odoo_client.py` — start with just authenticating and fetching
   a `res.partner` record to confirm the connection works.
3. Decide the settlement → journal entry account mapping and implement it in
   `create_settlement_journal_entry()`.
4. Build a frontend, or start with the auto-generated `/docs` UI for internal
   use while the frontend comes later.
