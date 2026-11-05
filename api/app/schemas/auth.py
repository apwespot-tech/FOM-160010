from typing import Literal

from pydantic import BaseModel, Field

from app.phones import Phone


class CodeRequest(BaseModel):
    phone: Phone


class CodeRequested(BaseModel):
    expires_in: int


class TestCode(BaseModel):
    code: str


class VerifyRequest(BaseModel):
    phone: Phone
    code: str = Field(min_length=1, max_length=16)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_expires_in: int
