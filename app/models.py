import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ContractType(str, enum.Enum):
    basis = "basis"
    hta = "hta"  # hedge-to-arrive
    flat_price = "flat_price"
    forward_cash = "forward_cash"


class ContractStatus(str, enum.Enum):
    open = "open"
    partially_priced = "partially_priced"
    fully_priced = "fully_priced"
    delivering = "delivering"
    settled = "settled"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    posted = "posted"  # journal entry created in Odoo
    paid = "paid"


class GradeFactor(str, enum.Enum):
    moisture = "moisture"
    test_weight = "test_weight"
    damage = "damage"
    foreign_material = "foreign_material"


class Commodity(Base):
    """The thing being contracted (corn, soybeans, wheat...). Conceptually
    maps to Odoo's product.product — kept as a separate local table here so
    contract logic doesn't require a live Odoo call on every read."""

    __tablename__ = "commodities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String, nullable=False)  # bushel, ton, cwt
    futures_symbol: Mapped[str] = mapped_column(String, nullable=True)  # ZC, ZS, ZW
    contract_size: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    # Converts delivery-ticket net weight (always lbs — Easy Automation
    # reports feed usage in lbs regardless of the commodity) into this
    # commodity's unit_of_measure. For tons this is always 2000; for bushels
    # it's the commodity's standard test weight (e.g. corn 56, soybeans 60,
    # wheat 60) — it varies by commodity, not by contract, so it lives here.
    lbs_per_unit: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    contracts: Mapped[list["BasisContract"]] = relationship(back_populates="commodity")
    grade_schedules: Mapped[list["GradeAdjustmentSchedule"]] = relationship(
        back_populates="commodity"
    )


class GrowerRef(Base):
    """Lightweight local cache of an Odoo res.partner. Odoo remains the
    source of truth for grower/partner data — this table just stores the
    Odoo partner ID and a display name so contracts can reference a grower
    without a live API round-trip on every read. Refresh `name` periodically
    or on write if you want it to stay in sync."""

    __tablename__ = "grower_refs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    odoo_partner_id: Mapped[int] = mapped_column(nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    contracts: Mapped[list["BasisContract"]] = relationship(back_populates="grower")


class BasisContract(Base):
    __tablename__ = "basis_contracts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    contract_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    grower_id: Mapped[str] = mapped_column(ForeignKey("grower_refs.id"), nullable=False)
    commodity_id: Mapped[str] = mapped_column(ForeignKey("commodities.id"), nullable=False)

    contract_type: Mapped[ContractType] = mapped_column(SAEnum(ContractType), nullable=False)
    futures_month: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "CZ26"
    basis: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    quantity_contracted: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    # quantity_priced / quantity_delivered are DERIVED from child records —
    # see app/services/settlement.py. Not stored here to avoid drift; if you
    # want them denormalized for query speed later, recompute on every
    # pricing event / delivery ticket write rather than trusting a stale value.

    delivery_window_start: Mapped[date] = mapped_column(Date, nullable=True)
    delivery_window_end: Mapped[date] = mapped_column(Date, nullable=True)
    delivery_location: Mapped[str] = mapped_column(String, nullable=True)
    price_by_date: Mapped[date] = mapped_column(Date, nullable=True)

    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus), nullable=False, default=ContractStatus.open
    )
    date_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    grower: Mapped["GrowerRef"] = relationship(back_populates="contracts")
    commodity: Mapped["Commodity"] = relationship(back_populates="contracts")
    pricing_events: Mapped[list["PricingEvent"]] = relationship(back_populates="contract")
    delivery_tickets: Mapped[list["DeliveryTicket"]] = relationship(back_populates="contract")
    settlements: Mapped[list["Settlement"]] = relationship(back_populates="contract")


class PricingEvent(Base):
    __tablename__ = "pricing_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("basis_contracts.id"), nullable=False)

    date_priced: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_priced: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)  # this event only
    futures_price_locked: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    futures_month: Mapped[str] = mapped_column(String, nullable=False)
    broker_reference: Mapped[str] = mapped_column(String, nullable=True)

    contract: Mapped["BasisContract"] = relationship(back_populates="pricing_events")


class DeliveryTicket(Base):
    __tablename__ = "delivery_tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("basis_contracts.id"), nullable=False)

    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticket_number: Mapped[str] = mapped_column(String, nullable=True)
    warehouse_location: Mapped[str] = mapped_column(String, nullable=True)

    # Always lbs (scale weight) regardless of the contract's commodity unit —
    # Easy Automation reports feed usage in lbs. Convert via
    # Commodity.lbs_per_unit before comparing against quantity_contracted;
    # see services/settlement.py:quantity_delivered.
    gross_weight: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    net_weight: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    moisture: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    test_weight: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    damage: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    foreign_material: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)

    # Computed at write time from GradeAdjustmentSchedule — see services/settlement.py
    grade_adjustment_amount: Mapped[float] = mapped_column(Numeric(10, 4), nullable=True)

    contract: Mapped["BasisContract"] = relationship(back_populates="delivery_tickets")


class GradeAdjustmentSchedule(Base):
    """Lookup table, not tied to one contract — discounts/premiums by
    commodity and quality factor. `threshold` is stored as a simple
    comparison value; see services/settlement.py for how it's interpreted
    (currently: adjustment applies when the ticket's factor value exceeds
    this threshold — extend this if you need more complex bands/tiers)."""

    __tablename__ = "grade_adjustment_schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    commodity_id: Mapped[str] = mapped_column(ForeignKey("commodities.id"), nullable=False)

    factor: Mapped[GradeFactor] = mapped_column(SAEnum(GradeFactor), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    adjustment_per_unit: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    commodity: Mapped["Commodity"] = relationship(back_populates="grade_schedules")


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("basis_contracts.id"), nullable=False)

    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_settled: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    avg_futures_price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    basis: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    grade_adjustments_total: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    gross_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    deductions: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    # Populated once app/odoo_client.py successfully creates the journal entry
    odoo_journal_entry_id: Mapped[int] = mapped_column(nullable=True)

    contract: Mapped["BasisContract"] = relationship(back_populates="settlements")
