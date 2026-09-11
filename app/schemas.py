from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import ContractType, ContractStatus, PaymentStatus, GradeFactor


# ---------- Commodity ----------

class CommodityCreate(BaseModel):
    name: str
    unit_of_measure: str
    futures_symbol: Optional[str] = None
    contract_size: Optional[float] = None


class CommodityOut(CommodityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ---------- Grower (local cache of an Odoo partner) ----------

class GrowerRefCreate(BaseModel):
    odoo_partner_id: int
    name: str


class GrowerRefOut(GrowerRefCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ---------- Basis Contract ----------

class BasisContractCreate(BaseModel):
    contract_number: str
    grower_id: str
    commodity_id: str
    contract_type: ContractType
    futures_month: str
    basis: float
    quantity_contracted: float
    delivery_window_start: Optional[date] = None
    delivery_window_end: Optional[date] = None
    delivery_location: Optional[str] = None
    price_by_date: Optional[date] = None


class BasisContractOut(BasisContractCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: ContractStatus
    date_created: datetime


class BasisContractSummary(BasisContractOut):
    """Contract plus the derived running totals — see GET /contracts/{id}/summary."""
    quantity_priced: float
    quantity_delivered: float
    quantity_open: float


# ---------- Pricing Event ----------

class PricingEventCreate(BaseModel):
    contract_id: str
    date_priced: date
    quantity_priced: float
    futures_price_locked: float
    futures_month: str
    broker_reference: Optional[str] = None


class PricingEventOut(PricingEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ---------- Delivery Ticket ----------

class DeliveryTicketCreate(BaseModel):
    contract_id: str
    delivery_date: date
    ticket_number: Optional[str] = None
    warehouse_location: Optional[str] = None
    gross_weight: float
    net_weight: float
    moisture: Optional[float] = None
    test_weight: Optional[float] = None
    damage: Optional[float] = None
    foreign_material: Optional[float] = None


class DeliveryTicketOut(DeliveryTicketCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    grade_adjustment_amount: Optional[float] = None


# ---------- Grade Adjustment Schedule ----------

class GradeAdjustmentScheduleCreate(BaseModel):
    commodity_id: str
    factor: GradeFactor
    threshold: float
    adjustment_per_unit: float
    notes: Optional[str] = None


class GradeAdjustmentScheduleOut(GradeAdjustmentScheduleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


# ---------- Settlement ----------

class SettlementCreate(BaseModel):
    contract_id: str
    settlement_date: date
    quantity_settled: float
    deductions: Optional[float] = 0


class SettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    contract_id: str
    settlement_date: date
    quantity_settled: float
    avg_futures_price: float
    basis: float
    grade_adjustments_total: float
    gross_amount: float
    deductions: float
    net_amount: float
    payment_status: PaymentStatus
    odoo_journal_entry_id: Optional[int] = None
