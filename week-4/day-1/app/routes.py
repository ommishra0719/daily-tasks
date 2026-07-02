from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from db.database import get_db
from db.repository import UserRepository
# Note: In a real app, use passlib to hash passwords. Using plain text here for structural brevity.

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True # Tells Pydantic to read ORM objects

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    
    # Check if user exists
    existing_user = await repo.get_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # In reality, hash the password here before passing to repo
    fake_hashed_password = f"{user.password}_hashed" 
    
    new_user = await repo.create(email=user.email, hashed_password=fake_hashed_password)
    return new_user