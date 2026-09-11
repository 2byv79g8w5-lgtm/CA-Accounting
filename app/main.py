from fastapi import FastAPI

from app.routers import (
    commodities,
    growers,
    contracts,
    pricing_events,
    delivery_tickets,
    grade_schedules,
    settlements,
)

app = FastAPI(
    title="Grain Basis Contract Accounting",
    description=(
        "Manages grain basis contracts, pricing events, deliveries, and "
        "settlements. Settlements post to Odoo as journal entries once "
        "app/odoo_client.py is filled in."
    ),
)

app.include_router(commodities.router)
app.include_router(growers.router)
app.include_router(contracts.router)
app.include_router(pricing_events.router)
app.include_router(delivery_tickets.router)
app.include_router(grade_schedules.router)
app.include_router(settlements.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
