from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"
    ADMIN = "admin"


class BusStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class CrowdLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.PASSENGER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    profile_picture = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    passenger_profile = relationship("Passenger", back_populates="user", uselist=False)
    favorite_stops = relationship("FavoriteStop", back_populates="user")
    favorite_routes = relationship("FavoriteRoute", back_populates="user")
    trip_history = relationship("TripHistory", back_populates="user")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    license_expiry = Column(DateTime(timezone=True))
    emergency_contact = Column(String(20))
    hire_date = Column(DateTime(timezone=True), server_default=func.now())
    is_available = Column(Boolean, default=True)
    rating = Column(Float, default=0.0)
    total_trips = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="driver_profile")
    bus_assignments = relationship("BusAssignment", back_populates="driver")


class Passenger(Base):
    __tablename__ = "passengers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    student_id = Column(String(50), unique=True, index=True)
    department = Column(String(100))
    year_of_study = Column(Integer)
    emergency_contact = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="passenger_profile")


class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_number = Column(String(20), unique=True, nullable=False, index=True)
    license_plate = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    model = Column(String(100))
    manufacturer = Column(String(100))
    year = Column(Integer)
    status = Column(Enum(BusStatus), default=BusStatus.ACTIVE)
    features = Column(JSON)  # WiFi, AC, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assignments = relationship("BusAssignment", back_populates="bus")
    tracking_data = relationship("BusTracking", back_populates="bus")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#2196F3")  # Hex color code
    is_active = Column(Boolean, default=True)
    estimated_duration_minutes = Column(Integer)
    distance_km = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stops = relationship("RouteStop", back_populates="route", order_by="RouteStop.sequence")
    assignments = relationship("BusAssignment", back_populates="route")


class BusStop(Base):
    __tablename__ = "bus_stops"

    id = Column(Integer, primary_key=True, index=True)
    stop_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    facilities = Column(JSON)  # Shelter, seating, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    route_stops = relationship("RouteStop", back_populates="stop")
    favorite_stops = relationship("FavoriteStop", back_populates="stop")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("bus_stops.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    estimated_arrival_time_minutes = Column(Integer)  # From route start
    is_pickup_allowed = Column(Boolean, default=True)
    is_dropoff_allowed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    route = relationship("Route", back_populates="stops")
    stop = relationship("BusStop", back_populates="route_stops")


class BusAssignment(Base):
    __tablename__ = "bus_assignments"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bus = relationship("Bus", back_populates="assignments")
    driver = relationship("Driver", back_populates="bus_assignments")
    route = relationship("Route", back_populates="assignments")


class BusTracking(Base):
    __tablename__ = "bus_tracking"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float)
    heading = Column(Float)  # Direction in degrees
    accuracy_meters = Column(Float)
    crowd_level = Column(Enum(CrowdLevel), default=CrowdLevel.MEDIUM)
    current_stop_id = Column(Integer, ForeignKey("bus_stops.id"))
    next_stop_id = Column(Integer, ForeignKey("bus_stops.id"))
    eta_minutes = Column(Integer)
    is_on_route = Column(Boolean, default=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    bus = relationship("Bus", back_populates="tracking_data")
    current_stop = relationship("BusStop", foreign_keys=[current_stop_id])
    next_stop = relationship("BusStop", foreign_keys=[next_stop_id])


class ServiceAlert(Base):
    __tablename__ = "service_alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM)
    affected_routes = Column(JSON)  # List of route IDs
    affected_stops = Column(JSON)  # List of stop IDs
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User")


class FavoriteStop(Base):
    __tablename__ = "favorite_stops"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("bus_stops.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorite_stops")
    stop = relationship("BusStop", back_populates="favorite_stops")


class FavoriteRoute(Base):
    __tablename__ = "favorite_routes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorite_routes")
    route = relationship("Route")


class TripHistory(Base):
    __tablename__ = "trip_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    start_stop_id = Column(Integer, ForeignKey("bus_stops.id"), nullable=False)
    end_stop_id = Column(Integer, ForeignKey("bus_stops.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    distance_km = Column(Float)
    fare_amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="trip_history")
    route = relationship("Route")
    bus = relationship("Bus")
    start_stop = relationship("BusStop", foreign_keys=[start_stop_id])
    end_stop = relationship("BusStop", foreign_keys=[end_stop_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")  # info, warning, error, success
    is_read = Column(Boolean, default=False)
    data = Column(JSON)  # Additional data for the notification
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
