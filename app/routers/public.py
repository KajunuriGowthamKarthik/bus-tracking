from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models import Route, RouteStop, BusStop, ServiceAlert, Bus, BusAssignment, BusTracking

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/bootstrap")
async def bootstrap_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return initial data to satisfy the current frontend placeholders"""
    routes = db.query(Route).all()
    stops = db.query(BusStop).all()
    alerts = db.query(ServiceAlert).filter(ServiceAlert.is_active == True).all()

    # Build simplified structures to match frontend expectations
    routes_payload = []
    for r in routes:
        # Last known buses for this route
        assignments = db.query(BusAssignment).filter(BusAssignment.route_id == r.id, BusAssignment.is_active == True).all()
        buses_list = []
        for a in assignments:
            latest = db.query(BusTracking).filter(BusTracking.bus_id == a.bus_id).order_by(BusTracking.timestamp.desc()).first()
            buses_list.append({
                "id": a.bus_id,
                "number": a.bus.bus_number,
                "currentStop": latest.current_stop.name if latest and latest.current_stop else "",
                "nextStop": latest.next_stop.name if latest and latest.next_stop else "",
                "eta": latest.eta_minutes if latest and latest.eta_minutes is not None else 5,
                "crowdLevel": (latest.crowd_level.value if latest and hasattr(latest.crowd_level, "value") else (latest.crowd_level if latest else "medium")),
                "coordinates": [
                    latest.latitude if latest else 12.9716,
                    latest.longitude if latest else 77.5946
                ]
            })
        routes_payload.append({
            "id": r.route_code,
            "name": r.name,
            "color": r.color,
            "buses": buses_list
        })

    stops_payload = [{
        "id": s.id,
        "name": s.name,
        "address": s.address or "",
        "coordinates": [s.latitude, s.longitude],
        "routes": [rs.route_id for rs in s.route_stops]
    } for s in stops]

    alerts_payload = [{
        "id": a.id,
        "title": a.title,
        "message": a.message,
        "severity": a.severity.value if hasattr(a.severity, "value") else a.severity,
        "affectedRoutes": a.affected_routes or []
    } for a in alerts]

    return {
        "busRoutes": routes_payload,
        "busStops": stops_payload,
        "serviceAlerts": alerts_payload
    }


