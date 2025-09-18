from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"
    ADMIN = "admin"


class BusStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class CrowdLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseSchema):
    email: EmailStr
    username: str
    full_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.PASSENGER


class UserCreate(UserBase):
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None


# Driver schemas
class DriverBase(BaseSchema):
    license_number: str
    license_expiry: Optional[datetime] = None
    emergency_contact: Optional[str] = None


class DriverCreate(DriverBase):
    user_id: int


class DriverUpdate(BaseSchema):
    license_number: Optional[str] = None
    license_expiry: Optional[datetime] = None
    emergency_contact: Optional[str] = None
    is_available: Optional[bool] = None


class DriverResponse(DriverBase):
    id: int
    user_id: int
    is_available: bool
    rating: float
    total_trips: int
    hire_date: datetime
    user: UserResponse


# Passenger schemas
class PassengerBase(BaseSchema):
    student_id: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[int] = None
    emergency_contact: Optional[str] = None


class PassengerCreate(PassengerBase):
    user_id: int


class PassengerUpdate(BaseSchema):
    student_id: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[int] = None
    emergency_contact: Optional[str] = None


class PassengerResponse(PassengerBase):
    id: int
    user_id: int
    created_at: datetime
    user: UserResponse


# Bus schemas
class BusBase(BaseSchema):
    bus_number: str
    license_plate: str
    capacity: int
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    year: Optional[int] = None
    features: Optional[Dict[str, Any]] = None


class BusCreate(BusBase):
    pass


class BusUpdate(BaseSchema):
    bus_number: Optional[str] = None
    license_plate: Optional[str] = None
    capacity: Optional[int] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    year: Optional[int] = None
    status: Optional[BusStatus] = None
    features: Optional[Dict[str, Any]] = None


class BusResponse(BusBase):
    id: int
    status: BusStatus
    created_at: datetime


# Route schemas
class RouteBase(BaseSchema):
    route_code: str
    name: str
    description: Optional[str] = None
    color: str = "#2196F3"
    estimated_duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None


class RouteCreate(RouteBase):
    pass


class RouteUpdate(BaseSchema):
    route_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    estimated_duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None


class RouteResponse(RouteBase):
    id: int
    is_active: bool
    created_at: datetime


# Bus Stop schemas
class BusStopBase(BaseSchema):
    stop_code: str
    name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    facilities: Optional[Dict[str, Any]] = None


class BusStopCreate(BusStopBase):
    pass


class BusStopUpdate(BaseSchema):
    stop_code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None
    facilities: Optional[Dict[str, Any]] = None


class BusStopResponse(BusStopBase):
    id: int
    is_active: bool
    created_at: datetime


# Route Stop schemas
class RouteStopBase(BaseSchema):
    route_id: int
    stop_id: int
    sequence: int
    estimated_arrival_time_minutes: Optional[int] = None
    is_pickup_allowed: bool = True
    is_dropoff_allowed: bool = True


class RouteStopCreate(RouteStopBase):
    pass


class RouteStopUpdate(BaseSchema):
    sequence: Optional[int] = None
    estimated_arrival_time_minutes: Optional[int] = None
    is_pickup_allowed: Optional[bool] = None
    is_dropoff_allowed: Optional[bool] = None


class RouteStopResponse(RouteStopBase):
    id: int
    stop: BusStopResponse
    created_at: datetime


# Bus Assignment schemas
class BusAssignmentBase(BaseSchema):
    bus_id: int
    driver_id: int
    route_id: int
    start_time: datetime
    end_time: Optional[datetime] = None


class BusAssignmentCreate(BusAssignmentBase):
    pass


class BusAssignmentUpdate(BaseSchema):
    end_time: Optional[datetime] = None
    is_active: Optional[bool] = None


class BusAssignmentResponse(BusAssignmentBase):
    id: int
    is_active: bool
    bus: BusResponse
    driver: DriverResponse
    route: RouteResponse
    created_at: datetime


# Bus Tracking schemas
class BusTrackingBase(BaseSchema):
    bus_id: int
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    accuracy_meters: Optional[float] = None
    crowd_level: CrowdLevel = CrowdLevel.MEDIUM
    current_stop_id: Optional[int] = None
    next_stop_id: Optional[int] = None
    eta_minutes: Optional[int] = None
    is_on_route: bool = True


class BusTrackingCreate(BusTrackingBase):
    pass


class BusTrackingResponse(BusTrackingBase):
    id: int
    timestamp: datetime
    current_stop: Optional[BusStopResponse] = None
    next_stop: Optional[BusStopResponse] = None


# Service Alert schemas
class ServiceAlertBase(BaseSchema):
    title: str
    message: str
    severity: AlertSeverity = AlertSeverity.MEDIUM
    affected_routes: Optional[List[int]] = None
    affected_stops: Optional[List[int]] = None
    start_time: datetime
    end_time: Optional[datetime] = None


class ServiceAlertCreate(ServiceAlertBase):
    pass


class ServiceAlertUpdate(BaseSchema):
    title: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    affected_routes: Optional[List[int]] = None
    affected_stops: Optional[List[int]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: Optional[bool] = None


class ServiceAlertResponse(ServiceAlertBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


# Favorite schemas
class FavoriteStopBase(BaseSchema):
    stop_id: int


class FavoriteStopCreate(FavoriteStopBase):
    pass


class FavoriteStopResponse(FavoriteStopBase):
    id: int
    user_id: int
    stop: BusStopResponse
    created_at: datetime


class FavoriteRouteBase(BaseSchema):
    route_id: int


class FavoriteRouteCreate(FavoriteRouteBase):
    pass


class FavoriteRouteResponse(FavoriteRouteBase):
    id: int
    user_id: int
    route: RouteResponse
    created_at: datetime


# Trip History schemas
class TripHistoryBase(BaseSchema):
    route_id: int
    bus_id: int
    start_stop_id: int
    end_stop_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    fare_amount: Optional[float] = None


class TripHistoryCreate(TripHistoryBase):
    pass


class TripHistoryResponse(TripHistoryBase):
    id: int
    user_id: int
    route: RouteResponse
    bus: BusResponse
    start_stop: BusStopResponse
    end_stop: BusStopResponse
    created_at: datetime


# Notification schemas
class NotificationBase(BaseSchema):
    title: str
    message: str
    type: str = "info"
    data: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime


# Authentication schemas
class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseSchema):
    username: Optional[str] = None


class LoginRequest(BaseSchema):
    username: str
    password: str


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


# Search and Filter schemas
class SearchRequest(BaseSchema):
    query: str
    type: Optional[str] = None  # bus, stop, route


class SearchResponse(BaseSchema):
    buses: List[Dict[str, Any]] = []
    stops: List[BusStopResponse] = []
    routes: List[RouteResponse] = []


class RoutePlanRequest(BaseSchema):
    origin: str
    destination: str
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None


class RouteOption(BaseSchema):
    duration_minutes: int
    transfers: int
    buses: List[str]
    walking_time_minutes: int
    details: str
    total_distance_km: float


class RoutePlanResponse(BaseSchema):
    options: List[RouteOption]
    origin: str
    destination: str


# Real-time update schemas
class BusLocationUpdate(BaseSchema):
    bus_id: int
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    accuracy_meters: Optional[float] = None
    crowd_level: Optional[CrowdLevel] = None
    current_stop_id: Optional[int] = None
    next_stop_id: Optional[int] = None
    eta_minutes: Optional[int] = None


class WebSocketMessage(BaseSchema):
    type: str  # location_update, alert, notification
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()


# Dashboard schemas
class DashboardStats(BaseSchema):
    total_buses: int
    active_buses: int
    total_routes: int
    active_routes: int
    total_stops: int
    active_stops: int
    total_users: int
    active_alerts: int


class BusStatusSummary(BaseSchema):
    bus_id: int
    bus_number: str
    route_name: str
    current_location: Optional[Dict[str, float]] = None
    next_stop: Optional[str] = None
    eta_minutes: Optional[int] = None
    crowd_level: CrowdLevel
    is_on_route: bool
    last_updated: datetime
