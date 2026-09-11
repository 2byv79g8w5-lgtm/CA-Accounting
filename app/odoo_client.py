"""
Odoo integration — STUBBED. Fill this in once you have a live Odoo instance
to test against (see README "Next steps").

Odoo's external API is JSON-RPC (or XML-RPC). The pattern for every call is:
  1. Authenticate (get a uid using db/username/api-key)
  2. Call `execute_kw` with a model name, method, and args

Recommended build order:
  1. authenticate() — confirm you can log in at all
  2. find_partner_by_name() or similar — confirm you can READ data
  3. create_settlement_journal_entry() — the actual write this app needs

Docs: https://www.odoo.com/documentation/latest/developer/reference/external_api.html
"""

import os
import xmlrpc.client
from typing import Optional

ODOO_URL = os.getenv("ODOO_URL", "")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_API_KEY = os.getenv("ODOO_API_KEY", "")


class OdooNotConfigured(Exception):
    """Raised when Odoo credentials aren't set — lets the app run fine
    without Odoo configured, and fail loudly (not silently) only when
    something actually tries to use the integration."""


def _require_config():
    if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY]):
        raise OdooNotConfigured(
            "ODOO_URL, ODOO_DB, ODOO_USERNAME, and ODOO_API_KEY must all be "
            "set in .env before calling Odoo."
        )


def authenticate() -> int:
    """Logs in and returns the Odoo user id (uid) needed for every
    subsequent call. TODO: build and test this first once Odoo is running."""
    _require_config()
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed — check credentials.")
    return uid


def _models_proxy() -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


def find_partner_by_odoo_id(odoo_partner_id: int) -> Optional[dict]:
    """Fetches a res.partner record by ID. Useful as a first end-to-end
    test: if this works, your credentials and connection are good."""
    uid = authenticate()
    models = _models_proxy()
    results = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "res.partner", "read",
        [[odoo_partner_id]],
        {"fields": ["id", "name"]},
    )
    return results[0] if results else None


def create_settlement_journal_entry(
    settlement_id: str,
    partner_odoo_id: int,
    net_amount: float,
    description: str,
) -> int:
    """
    TODO — this is the real integration point, deliberately left unbuilt.

    Before writing this function, you need to decide (as an accounting
    policy, not a technical one — see the design doc):
      - Which journal to post into (e.g. Purchases journal)
      - Which GL accounts get debited/credited — likely something like
        debit Grain Purchases/COGS, credit Accounts Payable to the grower
      - Whether this posts as a draft (needs manual review/approval in
        Odoo) or posts immediately — draft is the safer default while
        you're building trust in the numbers

    Sketch of what the call looks like once those decisions are made:

        uid = authenticate()
        models = _models_proxy()
        move_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            "account.move", "create",
            [{
                "move_type": "in_invoice",  # or journal entry type of choice
                "partner_id": partner_odoo_id,
                "ref": description,
                "line_ids": [
                    (0, 0, {
                        "account_id": <grain_purchases_account_id>,
                        "debit": net_amount,
                        "credit": 0,
                    }),
                    (0, 0, {
                        "account_id": <accounts_payable_account_id>,
                        "debit": 0,
                        "credit": net_amount,
                    }),
                ],
            }]
        )
        return move_id

    Raises NotImplementedError until the above is filled in — this is
    intentional so nothing silently "succeeds" without actually posting.
    """
    raise NotImplementedError(
        "create_settlement_journal_entry is a stub — see the docstring for "
        "what's left to decide and build."
    )
