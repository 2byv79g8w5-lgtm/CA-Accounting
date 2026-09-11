from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/commodities", tags=["commodities"])


@router.post("/", response_model=schemas.CommodityOut)
def create_commodity(payload: schemas.CommodityCreate, db: Session = Depends(get_db)):
    commodity = models.Commodity(**payload.model_dump())
    db.add(commodity)
    db.commit()
    db.refresh(commodity)
    return commodity


@router.get("/", response_model=list[schemas.CommodityOut])
def list_commodities(db: Session = Depends(get_db)):
    return db.query(models.Commodity).all()


@router.get("/{commodity_id}", response_model=schemas.CommodityOut)
def get_commodity(commodity_id: str, db: Session = Depends(get_db)):
    commodity = db.get(models.Commodity, commodity_id)
    if not commodity:
        raise HTTPException(404, "Commodity not found")
    return commodity
