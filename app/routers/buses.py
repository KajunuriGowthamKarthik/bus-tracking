from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Bus, BusTracking, BusAssignment, Driver, Route
from app.schemas import (
    BusResponse, BusCreate, BusUpdate, BusTrackingResponse, 
    BusTrackingCreate, BusLocationUpdate, BusStatusSummary
)
from app.auth import get_current_user, get_current_driver, get_current_admin
from datetime import datetime, timedelta
import math
from app.realtime import manager

router = APIRouter(prefix="/buses", tags=["buses"])


@router.get("/", response_model=List[BusResponse])
async def get_all_buses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all buses with optional filtering"""
    query = db.query(Bus)
    
    if status:
        query = query.filter(Bus.status == status)
    
    buses = query.offset(skip).limit(limit).all()
    return buses


@router.get("/{bus_id}", response_model=BusResponse)
async def get_bus(bus_id: int, db: Session = Depends(get_db)):
    """Get a specific bus by ID"""
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    return bus


@router.post("/", response_model=BusResponse, status_code=status.HTTP_201_CREATED)
async def create_bus(
    bus_data: BusCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Create a new bus (Admin only)"""
    
    # Check if bus number already exists
    existing_bus = db.query(Bus).filter(Bus.bus_number == bus_data.bus_number).first()
    if existing_bus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bus number already exists"
        )
    
    # Check if license plate already exists
    existing_plate = db.query(Bus).filter(Bus.license_plate == bus_data.license_plate).first()
    if existing_plate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License plate already exists"
        )
    
    db_bus = Bus(**bus_data.dict())
    db.add(db_bus)
    db.commit()
    db.refresh(db_bus)
    
    return db_bus


@router.put("/{bus_id}", response_model=BusResponse)
async def update_bus(
    bus_id: int,
    bus_data: BusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Update a bus (Admin only)"""
    
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Check for conflicts if updating bus number or license plate
    if bus_data.bus_number and bus_data.bus_number != bus.bus_number:
        existing_bus = db.query(Bus).filter(Bus.bus_number == bus_data.bus_number).first()
        if existing_bus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bus number already exists"
            )
    
    if bus_data.license_plate and bus_data.license_plate != bus.license_plate:
        existing_plate = db.query(Bus).filter(Bus.license_plate == bus_data.license_plate).first()
        if existing_plate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License plate already exists"
            )
    
    # Update bus data
    for field, value in bus_data.dict(exclude_unset=True).items():
        setattr(bus, field, value)
    
    db.commit()
    db.refresh(bus)
    
    return bus


@router.delete("/{bus_id}")
async def delete_bus(
    bus_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Delete a bus (Admin only)"""
    
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Check if bus has active assignments
    active_assignment = db.query(BusAssignment).filter(
        BusAssignment.bus_id == bus_id,
        BusAssignment.is_active == True
    ).first()
    
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete bus with active assignments"
        )
    
    db.delete(bus)
    db.commit()
    
    return {"message": "Bus deleted successfully"}


@router.get("/{bus_id}/tracking", response_model=List[BusTrackingResponse])
async def get_bus_tracking_history(
    bus_id: int,
    hours: int = Query(24, ge=1, le=168),  # Default 24 hours, max 1 week
    db: Session = Depends(get_db)
):
    """Get tracking history for a specific bus"""
    
    # Verify bus exists
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Get tracking data from the last N hours
    start_time = datetime.utcnow() - timedelta(hours=hours)
    tracking_data = db.query(BusTracking).filter(
        BusTracking.bus_id == bus_id,
        BusTracking.timestamp >= start_time
    ).order_by(BusTracking.timestamp.desc()).all()
    
    return tracking_data


@router.post("/{bus_id}/tracking", response_model=BusTrackingResponse)
async def update_bus_location(
    bus_id: int,
    location_data: BusLocationUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_driver)
):
    """Update bus location (Driver only)"""
    
    # Verify bus exists
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Verify driver is assigned to this bus
    active_assignment = db.query(BusAssignment).filter(
        BusAssignment.bus_id == bus_id,
        BusAssignment.driver_id == current_user.driver_profile.id,
        BusAssignment.is_active == True
    ).first()
    
    if not active_assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this bus"
        )
    
    # Create tracking record
    tracking_data = BusTracking(
        bus_id=bus_id,
        latitude=location_data.latitude,
        longitude=location_data.longitude,
        speed_kmh=location_data.speed_kmh,
        heading=location_data.heading,
        accuracy_meters=location_data.accuracy_meters,
        crowd_level=location_data.crowd_level or "medium",
        current_stop_id=location_data.current_stop_id,
        next_stop_id=location_data.next_stop_id,
        eta_minutes=location_data.eta_minutes,
        is_on_route=location_data.is_on_route
    )
    
    db.add(tracking_data)
    db.commit()
    db.refresh(tracking_data)
    # Broadcast to websocket subscribers
    await manager.broadcast({
        "type": "location_update",
        "data": {
            "bus_id": bus_id,
            "latitude": tracking_data.latitude,
            "longitude": tracking_data.longitude,
            "eta_minutes": tracking_data.eta_minutes,
            "crowd_level": str(tracking_data.crowd_level),
            "timestamp": tracking_data.timestamp,
        }
    })

    return tracking_data


@router.get("/active/status", response_model=List[BusStatusSummary])
async def get_active_buses_status(db: Session = Depends(get_db)):
    """Get status of all active buses"""
    
    # Get active bus assignments
    active_assignments = db.query(BusAssignment).filter(
        BusAssignment.is_active == True
    ).all()
    
    bus_statuses = []
    
    for assignment in active_assignments:
        # Get latest tracking data for this bus
        latest_tracking = db.query(BusTracking).filter(
            BusTracking.bus_id == assignment.bus_id
        ).order_by(BusTracking.timestamp.desc()).first()
        
        # Get route name
        route = db.query(Route).filter(Route.id == assignment.route_id).first()
        
        bus_status = BusStatusSummary(
            bus_id=assignment.bus.id,
            bus_number=assignment.bus.bus_number,
            route_name=route.name if route else "Unknown Route",
            current_location={
                "latitude": latest_tracking.latitude,
                "longitude": latest_tracking.longitude
            } if latest_tracking else None,
            next_stop=latest_tracking.next_stop.name if latest_tracking and latest_tracking.next_stop else None,
            eta_minutes=latest_tracking.eta_minutes if latest_tracking else None,
            crowd_level=latest_tracking.crowd_level if latest_tracking else "medium",
            is_on_route=latest_tracking.is_on_route if latest_tracking else True,
            last_updated=latest_tracking.timestamp if latest_tracking else assignment.start_time
        )
        
        bus_statuses.append(bus_status)
    
    return bus_statuses


@router.get("/nearby", response_model=List[BusStatusSummary])
async def get_nearby_buses(
    latitude: float = Query(..., description="User's latitude"),
    longitude: float = Query(..., description="User's longitude"),
    radius_km: float = Query(2.0, ge=0.1, le=10.0, description="Search radius in kilometers"),
    db: Session = Depends(get_db)
):
    """Get buses near a specific location"""
    
    # Get active bus assignments
    active_assignments = db.query(BusAssignment).filter(
        BusAssignment.is_active == True
    ).all()
    
    nearby_buses = []
    
    for assignment in active_assignments:
        # Get latest tracking data
        latest_tracking = db.query(BusTracking).filter(
            BusTracking.bus_id == assignment.bus_id
        ).order_by(BusTracking.timestamp.desc()).first()
        
        if not latest_tracking:
            continue
        
        # Calculate distance using Haversine formula
        distance = calculate_distance(
            latitude, longitude,
            latest_tracking.latitude, latest_tracking.longitude
        )
        
        if distance <= radius_km:
            # Get route name
            route = db.query(Route).filter(Route.id == assignment.route_id).first()
            
            bus_status = BusStatusSummary(
                bus_id=assignment.bus.id,
                bus_number=assignment.bus.bus_number,
                route_name=route.name if route else "Unknown Route",
                current_location={
                    "latitude": latest_tracking.latitude,
                    "longitude": latest_tracking.longitude
                },
                next_stop=latest_tracking.next_stop.name if latest_tracking.next_stop else None,
                eta_minutes=latest_tracking.eta_minutes,
                crowd_level=latest_tracking.crowd_level,
                is_on_route=latest_tracking.is_on_route,
                last_updated=latest_tracking.timestamp
            )
            
            nearby_buses.append(bus_status)
    
    return nearby_buses


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance
