from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import settlement as settlement_service

router = APIRouter(prefix="/delivery-tickets", tags=["delivery-tickets"])


@router.post("/", response_model=schemas.DeliveryTicketOut)
def create_delivery_ticket(payload: schemas.DeliveryTicketCreate, db: Session = Depends(get_db)):
    contract = db.get(models.BasisContract, payload.contract_id)
    if not contract:
        raise HTTPException(400, "contract_id does not exist")

    ticket = models.DeliveryTicket(**payload.model_dump())
    db.add(ticket)
    db.flush()  # so ticket.contract is available for the adjustment lookup below

    ticket.grade_adjustment_amount = settlement_service.compute_grade_adjustment(db, ticket)
    db.commit()
    db.refresh(ticket)

    # Delivery changes the contract's derived status — recompute it.
    settlement_service.refresh_contract_status(db, contract)

    return ticket


@router.get("/", response_model=list[schemas.DeliveryTicketOut])
def list_delivery_tickets(contract_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.DeliveryTicket)
    if contract_id:
        query = query.filter(models.DeliveryTicket.contract_id == contract_id)
    return query.all()
