from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from models import RequestStatus

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookBase(BaseModel):
    title: str
    author: str
    genre: str
    description: Optional[str] = None
    cover_url: Optional[str] = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_available: Optional[bool] = None

class BookResponse(BookBase):
    id: int
    is_available: bool
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookRequestBase(BaseModel):
    book_id: int

class BookRequestCreate(BookRequestBase):
    pass

class BookRequestResponse(BaseModel):
    id: int
    book_id: int
    requester_id: int
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True