from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, init_db
from app.auth import get_current_user, create_access_token, verify_password, get_password_hash
from app.models.user import User, UserRole
from app.routers import cases, admin
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from datetime import datetime
import contextlib

app = FastAPI(title="Take It Down API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cases.router)
app.include_router(admin.router)

# Pydantic models for requests/responses
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.VICTIM


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


from datetime import datetime

class UserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()
    print("🚀 Take It Down API server started successfully!")
    print("📋 Workflow features: State transitions, SLA tracking, Auto-escalation")
    
    # Start automation service in background (uncomment for production)
    # import asyncio
    # from app.automation import start_automation_service
    # asyncio.create_task(start_automation_service())


@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Take It Down API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
