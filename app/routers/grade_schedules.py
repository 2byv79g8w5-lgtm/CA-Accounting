from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/grade-schedules", tags=["grade-schedules"])


@router.post("/", response_model=schemas.GradeAdjustmentScheduleOut)
def create_grade_schedule(
    payload: schemas.GradeAdjustmentScheduleCreate, db: Session = Depends(get_db)
):
    if not db.get(models.Commodity, payload.commodity_id):
        raise HTTPException(400, "commodity_id does not exist")

    schedule = models.GradeAdjustmentSchedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/", response_model=list[schemas.GradeAdjustmentScheduleOut])
def list_grade_schedules(commodity_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.GradeAdjustmentSchedule)
    if commodity_id:
        query = query.filter(models.GradeAdjustmentSchedule.commodity_id == commodity_id)
    return query.all()
