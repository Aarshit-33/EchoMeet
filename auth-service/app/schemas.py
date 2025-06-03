from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from uuid import UUID
from typing import Optional

class UserBase(BaseModel):
    username: constr(max_length=50)
    email: EmailStr
    first_name: Optional[constr(max_length=50)] = None
    last_name: Optional[constr(max_length=50)] = None
    contact_no: Optional[constr(max_length=15)] = None

class UserCreate(UserBase):
    password: constr(min_length=8)

class User(UserBase):
    user_id: UUID
    is_verified: bool
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshToken(BaseModel):
    refresh_token: str