# Grain Basis Contract Accounting

A standalone app for managing grain basis contracts, pricing events, deliveries,
and settlements — with settlements posting as journal entries into Odoo's
accounting via Odoo's external API.

This is a **scaffold**, not a finished product. It has the data model, basic
CRUD endpoints, and the computed logic for running totals / weighted averages
in place. The Odoo integration is stubbed out (see `app/odoo_client.py`) since
Odoo isn't set up yet — wire it up once you have a live instance to test against.

## Planned integrations (not built yet)

This app is one corner of a **three-way sync** with two other systems:

- **Easy Automation** — the feed-mixing system at the elevator.
- **Odoo** — the accounting system of record for inventory and invoices.

The requirement is: **a change made in either this app or Easy Automation
needs to update the other, and both need to push inventory/invoice updates
to Odoo.** Concretely:

- A contract/inventory change made **in this app** → sync to Easy Automation
  (so its feed mixes reflect current contract terms) → and push the
  resulting inventory/invoice update to Odoo.
- A change made **in Easy Automation** (e.g. feed mixed/used against a
  contract) → sync back to this app (to update running totals/inventory
  here) → and push the resulting inventory/invoice update to Odoo.
- Odoo is the shared destination for inventory and invoice records from
  both sides, not just a one-way destination for settlements from this app
  alone.

None of this is built yet. Open questions to settle before building it:
- **Direction/transport**: webhooks (each side calls the other when it
  changes), polling, or a message queue? Two-way HTTP webhooks are the
  simplest starting point given this app and Odoo already speak HTTP APIs.
- **Source of truth for inventory**: if both this app and Easy Automation
  can change inventory, what happens on a conflict (e.g. both change the
  same contract's remaining quantity at once)?
- **What "invoice to Odoo" means from Easy Automation's side**: does Easy
  Automation call Odoo directly, or always route through this app's
  `odoo_client.py` so there's one place that owns the GL account mapping?
  (Recommend: always through this app, so the accounting policy — which
  accounts get debited/credited — lives in one place.)
- **API auth**: this app has none yet (see "Not built yet" below) — needed
  in both directions before Easy Automation can call in, or before this app
  can call out to Easy Automation.
- **Odoo side**: still needs a live instance to build/test against (see
  `app/odoo_client.py`'s TODOs).

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
- Authentication/authorization on the API itself — needed before Easy
  Automation (or anything else) can call in from outside
- Alembic migrations (currently using a blunt `create_all` — fine for now,
  worth adding once the schema stabilizes and you need to evolve it without
  dropping data)
- The three-way sync with Easy Automation and Odoo (see "Planned
  integrations" above) — no code for this yet; needs API auth on this app,
  a decision on transport (webhooks vs. polling), and a source-of-truth
  rule for inventory conflicts before either sync direction can be built

## Next steps

1. Get Odoo running (Odoo.sh, their cloud hosting, or self-hosted) with the
   Accounting app enabled.
2. Fill in `app/odoo_client.py` — start with just authenticating and fetching
   a `res.partner` record to confirm the connection works.
3. Decide the settlement → journal entry account mapping and implement it in
   `create_settlement_journal_entry()`.
4. Add API authentication so external callers (Easy Automation) can be
   authorized to read from and write to this app.
5. Settle the open questions under "Planned integrations" (transport,
   inventory source-of-truth/conflict rule, whether Easy Automation posts to
   Odoo directly or always through this app's `odoo_client.py`).
6. Build the sync in both directions: this app → Easy Automation, and
   Easy Automation → this app, each followed by an inventory/invoice push
   to Odoo.
7. Build a frontend, or start with the auto-generated `/docs` UI for internal
   use while the frontend comes later.
