from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, odoo_client
from app.database import get_db
from app.services import settlement as settlement_service

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.post("/", response_model=schemas.SettlementOut)
def create_settlement(payload: schemas.SettlementCreate, db: Session = Depends(get_db)):
    """
    Computes and saves a settlement. Does NOT post to Odoo yet — that's a
    separate step (see POST /settlements/{id}/post-to-odoo) so a settlement
    can be reviewed locally before it becomes a real journal entry.
    """
    contract = db.get(models.BasisContract, payload.contract_id)
    if not contract:
        raise HTTPException(400, "contract_id does not exist")

    computed = settlement_service.build_settlement(
        db, contract, payload.quantity_settled, payload.deductions or 0
    )

    settlement = models.Settlement(
        contract_id=payload.contract_id,
        settlement_date=payload.settlement_date,
        quantity_settled=payload.quantity_settled,
        **computed,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    settlement_service.refresh_contract_status(db, contract)

    return settlement


@router.get("/", response_model=list[schemas.SettlementOut])
def list_settlements(contract_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Settlement)
    if contract_id:
        query = query.filter(models.Settlement.contract_id == contract_id)
    return query.all()


@router.get("/{settlement_id}", response_model=schemas.SettlementOut)
def get_settlement(settlement_id: str, db: Session = Depends(get_db)):
    settlement = db.get(models.Settlement, settlement_id)
    if not settlement:
        raise HTTPException(404, "Settlement not found")
    return settlement


@router.post("/{settlement_id}/post-to-odoo", response_model=schemas.SettlementOut)
def post_settlement_to_odoo(settlement_id: str, db: Session = Depends(get_db)):
    """
    Calls odoo_client.create_settlement_journal_entry() for an existing
    settlement. Will raise a 501 until that function is actually built —
    this endpoint exists now so the shape of the flow is in place once it is.
    """
    settlement = db.get(models.Settlement, settlement_id)
    if not settlement:
        raise HTTPException(404, "Settlement not found")
    if settlement.payment_status == models.PaymentStatus.posted:
        raise HTTPException(400, "Settlement already posted to Odoo")

    contract = settlement.contract
    grower = contract.grower

    try:
        journal_entry_id = odoo_client.create_settlement_journal_entry(
            settlement_id=settlement.id,
            partner_odoo_id=grower.odoo_partner_id,
            net_amount=float(settlement.net_amount),
            description=f"Settlement for contract {contract.contract_number}",
        )
    except odoo_client.OdooNotConfigured as e:
        raise HTTPException(503, str(e))
    except NotImplementedError as e:
        raise HTTPException(501, str(e))

    settlement.odoo_journal_entry_id = journal_entry_id
    settlement.payment_status = models.PaymentStatus.posted
    db.commit()
    db.refresh(settlement)
    return settlement
