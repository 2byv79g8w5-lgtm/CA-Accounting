"""
Business logic for the two places the design doc flagged as needing real
thought: partial pricing/delivery running totals, and the settlement math
that eventually feeds the Odoo journal entry.

Nothing here talks to Odoo — see app/odoo_client.py for that. This module
only computes numbers from local data.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


def quantity_priced(db: Session, contract_id: str) -> float:
    """Sum of all pricing events for a contract."""
    total = (
        db.query(func.coalesce(func.sum(models.PricingEvent.quantity_priced), 0))
        .filter(models.PricingEvent.contract_id == contract_id)
        .scalar()
    )
    return float(total)


def quantity_delivered(db: Session, contract_id: str) -> float:
    """Sum of delivered quantity for a contract, in the contract's commodity
    unit (bu/ton/etc). Delivery ticket net_weight is always lbs — see
    DeliveryTicket — so this converts using Commodity.lbs_per_unit rather
    than summing raw lbs against a quantity_contracted that may be in a
    different unit."""
    total_lbs = (
        db.query(func.coalesce(func.sum(models.DeliveryTicket.net_weight), 0))
        .filter(models.DeliveryTicket.contract_id == contract_id)
        .scalar()
    )
    if not total_lbs:
        return 0.0

    contract = db.get(models.BasisContract, contract_id)
    lbs_per_unit = float(contract.commodity.lbs_per_unit)
    return float(total_lbs) / lbs_per_unit


def weighted_avg_futures_price(db: Session, contract_id: str) -> float:
    """
    Weighted average of futures_price_locked across all pricing events,
    weighted by quantity_priced on each event. This is the number that
    feeds both the contract summary and the settlement.

    Returns 0 if nothing has been priced yet — callers should check
    quantity_priced() > 0 before relying on this for a real settlement.
    """
    events = (
        db.query(models.PricingEvent)
        .filter(models.PricingEvent.contract_id == contract_id)
        .all()
    )
    total_qty = sum(float(e.quantity_priced) for e in events)
    if total_qty == 0:
        return 0.0
    weighted_sum = sum(
        float(e.quantity_priced) * float(e.futures_price_locked) for e in events
    )
    return weighted_sum / total_qty


def contract_summary(db: Session, contract: models.BasisContract) -> dict:
    """Derived running totals for a contract — quantity_priced,
    quantity_delivered, and what's still open against the contracted amount."""
    priced = quantity_priced(db, contract.id)
    delivered = quantity_delivered(db, contract.id)
    return {
        "quantity_priced": priced,
        "quantity_delivered": delivered,
        "quantity_open": float(contract.quantity_contracted) - delivered,
    }


def compute_grade_adjustment(db: Session, ticket: models.DeliveryTicket) -> float:
    """
    Looks up the Grade Adjustment Schedule for this ticket's commodity and
    sums the adjustment for every factor that crosses its threshold.

    Current rule: a factor's adjustment applies if the ticket's measured
    value for that factor EXCEEDS the schedule's threshold (e.g. moisture
    > 15.5% triggers that row's adjustment_per_unit as a discount). This is
    a simple one-sided rule — real grading schedules often have multiple
    tiers (every point over 15% costs X, every point over 18% costs more).
    Extend this function first if/when that complexity shows up; the schema
    already supports adding more schedule rows per factor.
    """
    contract = ticket.contract
    schedules = (
        db.query(models.GradeAdjustmentSchedule)
        .filter(models.GradeAdjustmentSchedule.commodity_id == contract.commodity_id)
        .all()
    )

    factor_values = {
        models.GradeFactor.moisture: ticket.moisture,
        models.GradeFactor.test_weight: ticket.test_weight,
        models.GradeFactor.damage: ticket.damage,
        models.GradeFactor.foreign_material: ticket.foreign_material,
    }

    total_adjustment = 0.0
    for schedule in schedules:
        value = factor_values.get(schedule.factor)
        if value is None:
            continue
        if float(value) > float(schedule.threshold):
            total_adjustment += float(schedule.adjustment_per_unit)

    return total_adjustment


def build_settlement(
    db: Session,
    contract: models.BasisContract,
    quantity_settled: float,
    deductions: float = 0.0,
) -> dict:
    """
    Computes all the derived fields for a new settlement. Does NOT write to
    the database or call Odoo — the router is responsible for persisting
    this and, later, calling odoo_client.create_settlement_journal_entry().
    """
    avg_price = weighted_avg_futures_price(db, contract.id)

    tickets = (
        db.query(models.DeliveryTicket)
        .filter(models.DeliveryTicket.contract_id == contract.id)
        .all()
    )
    grade_adjustments_total = sum(
        float(t.grade_adjustment_amount or 0) for t in tickets
    )

    flat_price = avg_price + float(contract.basis)
    gross_amount = flat_price * quantity_settled + grade_adjustments_total
    net_amount = gross_amount - deductions

    return {
        "avg_futures_price": avg_price,
        "basis": float(contract.basis),
        "grade_adjustments_total": grade_adjustments_total,
        "gross_amount": gross_amount,
        "deductions": deductions,
        "net_amount": net_amount,
    }


def refresh_contract_status(db: Session, contract: models.BasisContract) -> None:
    """
    Recomputes and updates contract.status from current totals. Call this
    after any pricing event, delivery ticket, or settlement write that
    could change where the contract sits in its lifecycle.
    """
    summary = contract_summary(db, contract)
    contracted = float(contract.quantity_contracted)
    priced = summary["quantity_priced"]
    delivered = summary["quantity_delivered"]

    has_settlement = (
        db.query(models.Settlement)
        .filter(models.Settlement.contract_id == contract.id)
        .first()
        is not None
    )

    if has_settlement and delivered >= contracted and priced >= contracted:
        contract.status = models.ContractStatus.settled
    elif delivered > 0:
        contract.status = models.ContractStatus.delivering
    elif priced >= contracted and contracted > 0:
        contract.status = models.ContractStatus.fully_priced
    elif priced > 0:
        contract.status = models.ContractStatus.partially_priced
    else:
        contract.status = models.ContractStatus.open

    db.add(contract)
    db.commit()
