from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import settlement as settlement_service

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/", response_model=schemas.BasisContractOut)
def create_contract(payload: schemas.BasisContractCreate, db: Session = Depends(get_db)):
    if not db.get(models.GrowerRef, payload.grower_id):
        raise HTTPException(400, "grower_id does not exist")
    if not db.get(models.Commodity, payload.commodity_id):
        raise HTTPException(400, "commodity_id does not exist")

    contract = models.BasisContract(**payload.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/", response_model=list[schemas.BasisContractOut])
def list_contracts(db: Session = Depends(get_db)):
    return db.query(models.BasisContract).all()


@router.get("/{contract_id}", response_model=schemas.BasisContractOut)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(models.BasisContract, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")
    return contract


@router.get("/{contract_id}/summary", response_model=schemas.BasisContractSummary)
def get_contract_summary(contract_id: str, db: Session = Depends(get_db)):
    """Contract fields plus the derived running totals (quantity priced,
    delivered, and still open) computed live from pricing events and
    delivery tickets."""
    contract = db.get(models.BasisContract, contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")

    summary = settlement_service.contract_summary(db, contract)
    return schemas.BasisContractSummary(
        **schemas.BasisContractOut.model_validate(contract).model_dump(),
        **summary,
    )
