from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    phone: str
    email: Optional[EmailStr] = None

class UserCreate(BaseModel):
    phone: str

class UserUpdateEmail(BaseModel):
    email: EmailStr

class User(UserBase):
    id: int

    class Config:
        orm_mode = True
