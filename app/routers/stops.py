from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import BusStop
from app.schemas import BusStopResponse, BusStopCreate, BusStopUpdate
from app.auth import get_current_admin


router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/", response_model=List[BusStopResponse])
async def list_stops(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    active_only: bool = Query(True),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(BusStop)
    if active_only:
        query = query.filter(BusStop.is_active == True)
    if q:
        like = f"%{q}%"
        query = query.filter((BusStop.name.ilike(like)) | (BusStop.address.ilike(like)))
    return query.offset(skip).limit(limit).all()


@router.get("/{stop_id}", response_model=BusStopResponse)
async def get_stop(stop_id: int, db: Session = Depends(get_db)):
    stop = db.query(BusStop).filter(BusStop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")
    return stop


@router.post("/", response_model=BusStopResponse, status_code=status.HTTP_201_CREATED)
async def create_stop(
    stop_data: BusStopCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    # Ensure unique stop_code
    existing = db.query(BusStop).filter(BusStop.stop_code == stop_data.stop_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="stop_code already exists")
    stop = BusStop(
        stop_code=stop_data.stop_code,
        name=stop_data.name,
        address=stop_data.address,
        latitude=stop_data.latitude,
        longitude=stop_data.longitude,
        facilities=stop_data.facilities,
    )
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


@router.put("/{stop_id}", response_model=BusStopResponse)
async def update_stop(
    stop_id: int,
    stop_data: BusStopUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    stop = db.query(BusStop).filter(BusStop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    # Unique code check
    if stop_data.stop_code and stop_data.stop_code != stop.stop_code:
        exists = db.query(BusStop).filter(BusStop.stop_code == stop_data.stop_code).first()
        if exists:
            raise HTTPException(status_code=400, detail="stop_code already exists")
    for field, value in stop_data.dict(exclude_unset=True).items():
        setattr(stop, field, value)
    db.commit()
    db.refresh(stop)
    return stop


@router.delete("/{stop_id}")
async def delete_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    stop = db.query(BusStop).filter(BusStop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    db.delete(stop)
    db.commit()
    return {"message": "Stop deleted"}


