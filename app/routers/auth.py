from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Driver, Passenger
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, Token, 
    RefreshTokenRequest, DriverCreate, PassengerCreate
)
from app.auth import (
    authenticate_user, create_tokens_for_user, get_password_hash,
    verify_token, create_access_token, get_user_by_username,
    get_user_by_email, get_current_user
)
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        role=user_data.role,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/register/driver", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_driver(
    user_data: UserCreate,
    driver_data: DriverCreate,
    db: Session = Depends(get_db)
):
    """Register a new driver with driver profile"""
    
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if license number already exists
    existing_driver = db.query(Driver).filter(Driver.license_number == driver_data.license_number).first()
    if existing_driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already registered"
        )
    
    # Create new user with driver role
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        role="driver",
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create driver profile
    db_driver = Driver(
        user_id=db_user.id,
        license_number=driver_data.license_number,
        license_expiry=driver_data.license_expiry,
        emergency_contact=driver_data.emergency_contact
    )
    
    db.add(db_driver)
    db.commit()
    
    return db_user


@router.post("/register/passenger", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_passenger(
    user_data: UserCreate,
    passenger_data: PassengerCreate,
    db: Session = Depends(get_db)
):
    """Register a new passenger with passenger profile"""
    
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if student ID already exists (if provided)
    if passenger_data.student_id:
        existing_passenger = db.query(Passenger).filter(
            Passenger.student_id == passenger_data.student_id
        ).first()
        if existing_passenger:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student ID already registered"
            )
    
    # Create new user with passenger role
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        role="passenger",
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create passenger profile
    db_passenger = Passenger(
        user_id=db_user.id,
        student_id=passenger_data.student_id,
        department=passenger_data.department,
        year_of_study=passenger_data.year_of_study,
        emergency_contact=passenger_data.emergency_contact
    )
    
    db.add(db_passenger)
    db.commit()
    
    return db_user


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return tokens"""
    
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    tokens = create_tokens_for_user(user)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    try:
        token_data = verify_token(refresh_data.refresh_token, "refresh")
        user = get_user_by_username(db, username=token_data.username)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new tokens
        tokens = create_tokens_for_user(user)
        return tokens
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout():
    """Logout user (client should discard tokens)"""
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.post("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user email (placeholder for email verification)"""
    # In a real implementation, you would:
    # 1. Verify the email token
    # 2. Update user.is_verified = True
    # 3. Return success message
    
    return {"message": "Email verification endpoint - implement with email service"}


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """Send password reset email (placeholder)"""
    # In a real implementation, you would:
    # 1. Check if email exists
    # 2. Generate reset token
    # 3. Send email with reset link
    
    return {"message": "Password reset email sent (if email exists)"}


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset password with token (placeholder)"""
    # In a real implementation, you would:
    # 1. Verify reset token
    # 2. Hash new password
    # 3. Update user password
    
    return {"message": "Password reset endpoint - implement with token verification"}
