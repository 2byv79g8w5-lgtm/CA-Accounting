from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import settlement as settlement_service

router = APIRouter(prefix="/pricing-events", tags=["pricing-events"])


@router.post("/", response_model=schemas.PricingEventOut)
def create_pricing_event(payload: schemas.PricingEventCreate, db: Session = Depends(get_db)):
    contract = db.get(models.BasisContract, payload.contract_id)
    if not contract:
        raise HTTPException(400, "contract_id does not exist")

    event = models.PricingEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)

    # Pricing changes the contract's derived status — recompute it.
    settlement_service.refresh_contract_status(db, contract)

    return event


@router.get("/", response_model=list[schemas.PricingEventOut])
def list_pricing_events(contract_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.PricingEvent)
    if contract_id:
        query = query.filter(models.PricingEvent.contract_id == contract_id)
    return query.all()
