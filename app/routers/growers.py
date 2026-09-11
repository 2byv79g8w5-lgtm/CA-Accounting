from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/growers", tags=["growers"])


@router.post("/", response_model=schemas.GrowerRefOut)
def create_grower(payload: schemas.GrowerRefCreate, db: Session = Depends(get_db)):
    """
    Creates the local cache record for a grower. This does NOT create a
    partner in Odoo — the odoo_partner_id must already exist there. Once
    app/odoo_client.py is built out, consider adding a lookup here that
    verifies the ID exists in Odoo before saving.
    """
    grower = models.GrowerRef(**payload.model_dump())
    db.add(grower)
    db.commit()
    db.refresh(grower)
    return grower


@router.get("/", response_model=list[schemas.GrowerRefOut])
def list_growers(db: Session = Depends(get_db)):
    return db.query(models.GrowerRef).all()


@router.get("/{grower_id}", response_model=schemas.GrowerRefOut)
def get_grower(grower_id: str, db: Session = Depends(get_db)):
    grower = db.get(models.GrowerRef, grower_id)
    if not grower:
        raise HTTPException(404, "Grower not found")
    return grower
