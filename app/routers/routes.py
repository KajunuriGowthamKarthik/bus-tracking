from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Route, BusStop, RouteStop, Bus, BusTracking
from app.schemas import (
    RouteResponse, RouteCreate, RouteUpdate, BusStopResponse, 
    BusStopCreate, BusStopUpdate, RouteStopResponse, RouteStopCreate,
    RoutePlanRequest, RoutePlanResponse, RouteOption
)
from app.auth import get_current_user, get_current_admin
from datetime import datetime, timedelta
import math

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/", response_model=List[RouteResponse])
async def get_all_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get all routes with optional filtering"""
    query = db.query(Route)
    
    if active_only:
        query = query.filter(Route.is_active == True)
    
    routes = query.offset(skip).limit(limit).all()
    return routes


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(route_id: int, db: Session = Depends(get_db)):
    """Get a specific route by ID"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    return route


@router.get("/{route_id}/stops", response_model=List[RouteStopResponse])
async def get_route_stops(route_id: int, db: Session = Depends(get_db)):
    """Get all stops for a specific route"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    route_stops = db.query(RouteStop).filter(
        RouteStop.route_id == route_id
    ).order_by(RouteStop.sequence).all()
    
    return route_stops


@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    route_data: RouteCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Create a new route (Admin only)"""
    
    # Check if route code already exists
    existing_route = db.query(Route).filter(Route.route_code == route_data.route_code).first()
    if existing_route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Route code already exists"
        )
    
    db_route = Route(**route_data.dict())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    
    return db_route


@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    route_data: RouteUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Update a route (Admin only)"""
    
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Check for conflicts if updating route code
    if route_data.route_code and route_data.route_code != route.route_code:
        existing_route = db.query(Route).filter(Route.route_code == route_data.route_code).first()
        if existing_route:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Route code already exists"
            )
    
    # Update route data
    for field, value in route_data.dict(exclude_unset=True).items():
        setattr(route, field, value)
    
    db.commit()
    db.refresh(route)
    
    return route


@router.delete("/{route_id}")
async def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Delete a route (Admin only)"""
    
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Check if route has active assignments
    from app.models import BusAssignment
    active_assignment = db.query(BusAssignment).filter(
        BusAssignment.route_id == route_id,
        BusAssignment.is_active == True
    ).first()
    
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete route with active assignments"
        )
    
    # Delete route stops first
    db.query(RouteStop).filter(RouteStop.route_id == route_id).delete()
    
    # Delete route
    db.delete(route)
    db.commit()
    
    return {"message": "Route deleted successfully"}


@router.post("/{route_id}/stops", response_model=RouteStopResponse, status_code=status.HTTP_201_CREATED)
async def add_stop_to_route(
    route_id: int,
    stop_data: RouteStopCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Add a stop to a route (Admin only)"""
    
    # Verify route exists
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Verify stop exists
    stop = db.query(BusStop).filter(BusStop.id == stop_data.stop_id).first()
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found"
        )
    
    # Check if stop is already in route
    existing_route_stop = db.query(RouteStop).filter(
        RouteStop.route_id == route_id,
        RouteStop.stop_id == stop_data.stop_id
    ).first()
    
    if existing_route_stop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stop already exists in this route"
        )
    
    # Check sequence conflicts
    existing_sequence = db.query(RouteStop).filter(
        RouteStop.route_id == route_id,
        RouteStop.sequence == stop_data.sequence
    ).first()
    
    if existing_sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sequence number already exists in this route"
        )
    
    db_route_stop = RouteStop(
        route_id=route_id,
        **stop_data.dict()
    )
    
    db.add(db_route_stop)
    db.commit()
    db.refresh(db_route_stop)
    
    return db_route_stop


@router.delete("/{route_id}/stops/{stop_id}")
async def remove_stop_from_route(
    route_id: int,
    stop_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Remove a stop from a route (Admin only)"""
    
    route_stop = db.query(RouteStop).filter(
        RouteStop.route_id == route_id,
        RouteStop.stop_id == stop_id
    ).first()
    
    if not route_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found in this route"
        )
    
    db.delete(route_stop)
    db.commit()
    
    return {"message": "Stop removed from route successfully"}


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    plan_request: RoutePlanRequest,
    db: Session = Depends(get_db)
):
    """Plan a route between two locations"""
    
    # This is a simplified route planning algorithm
    # In a real implementation, you would use a proper routing service
    
    # Find stops near origin and destination
    origin_stops = find_nearby_stops(plan_request.origin, db)
    destination_stops = find_nearby_stops(plan_request.destination, db)
    
    if not origin_stops or not destination_stops:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stops found near the specified locations"
        )
    
    # Generate route options
    options = []
    
    # Option 1: Direct route (if exists)
    direct_route = find_direct_route(origin_stops[0], destination_stops[0], db)
    if direct_route:
        options.append(RouteOption(
            duration_minutes=30,
            transfers=0,
            buses=[direct_route["bus_number"]],
            walking_time_minutes=5,
            details=f"Take {direct_route['bus_number']} from {plan_request.origin} to {plan_request.destination}",
            total_distance_km=10.5
        ))
    
    # Option 2: One transfer route
    transfer_route = find_transfer_route(origin_stops[0], destination_stops[0], db)
    if transfer_route:
        options.append(RouteOption(
            duration_minutes=45,
            transfers=1,
            buses=transfer_route["buses"],
            walking_time_minutes=8,
            details=f"Take {transfer_route['buses'][0]}, transfer at {transfer_route['transfer_stop']}, then {transfer_route['buses'][1]}",
            total_distance_km=12.3
        ))
    
    # Option 3: Alternative route
    if len(options) < 2:
        options.append(RouteOption(
            duration_minutes=55,
            transfers=1,
            buses=["Alternative Bus"],
            walking_time_minutes=10,
            details=f"Alternative route with longer travel time",
            total_distance_km=15.2
        ))
    
    return RoutePlanResponse(
        options=options,
        origin=plan_request.origin,
        destination=plan_request.destination
    )


def find_nearby_stops(location: str, db: Session) -> List[BusStop]:
    """Find stops near a location (simplified)"""
    # In a real implementation, you would use geocoding and distance calculation
    stops = db.query(BusStop).filter(
        BusStop.name.ilike(f"%{location}%")
    ).limit(3).all()
    
    return stops


def find_direct_route(origin_stop: BusStop, destination_stop: BusStop, db: Session) -> Optional[dict]:
    """Find a direct route between two stops"""
    # Check if both stops are on the same route
    origin_routes = db.query(RouteStop.route_id).filter(
        RouteStop.stop_id == origin_stop.id
    ).all()
    
    destination_routes = db.query(RouteStop.route_id).filter(
        RouteStop.stop_id == destination_stop.id
    ).all()
    
    # Find common routes
    common_routes = set([r[0] for r in origin_routes]) & set([r[0] for r in destination_routes])
    
    if common_routes:
        route_id = list(common_routes)[0]
        # Get a bus on this route
        from app.models import BusAssignment
        assignment = db.query(BusAssignment).filter(
            BusAssignment.route_id == route_id,
            BusAssignment.is_active == True
        ).first()
        
        if assignment:
            return {
                "bus_number": assignment.bus.bus_number,
                "route_id": route_id
            }
    
    return None


def find_transfer_route(origin_stop: BusStop, destination_stop: BusStop, db: Session) -> Optional[dict]:
    """Find a route with one transfer"""
    # Simplified transfer route finding
    # In a real implementation, you would use a proper routing algorithm
    
    return {
        "buses": ["Bus A", "Bus B"],
        "transfer_stop": "Central Station"
    }
