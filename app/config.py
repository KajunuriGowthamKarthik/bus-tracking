from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Database Configuration
    # Use SQLite by default for easy local setup; override via env for Postgres
    database_url: str = "sqlite:///./bus_tracking.db"
    test_database_url: str = "sqlite:///./bus_tracking_test.db"
    
    # JWT Configuration
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Application Settings
    app_name: str = "SmartTransit Bus Tracking"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"]
    
    # College/Institution Settings
    college_name: str = "Your College Name"
    college_coordinates_lat: float = 12.9716
    college_coordinates_lng: float = 77.5946
    college_radius_km: float = 5.0
    
    # Real-time Tracking Settings
    tracking_update_interval_seconds: int = 10
    location_accuracy_threshold_meters: int = 50
    
    # Notification Settings
    enable_push_notifications: bool = True
    fcm_server_key: Optional[str] = None
    
    # File Upload Settings
    max_file_size_mb: int = 5
    upload_directory: str = "uploads/"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_directory, exist_ok=True)
