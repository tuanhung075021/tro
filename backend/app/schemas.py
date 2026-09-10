# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Pydantic data schemas for authentication, role-based access, properties, and rooms."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """Schema for user registration with optional room invite code."""
    username: str = Field(..., min_length=1, max_length=50, description="Unique username")
    password: str = Field(..., min_length=1, description="Plain text password")
    full_name: Optional[str] = Field(default=None, max_length=100, description="Full name")
    phone: Optional[str] = Field(default=None, max_length=20, description="Contact phone number")
    role: str = Field(default="tenant", description="User role: 'landlord' or 'tenant'")
    invite_code: Optional[str] = Field(default=None, description="Room invite code for tenants")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("landlord", "tenant"):
            raise ValueError("Role must be 'landlord' or 'tenant'")
        return cleaned

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty")
        return cleaned


class UserLogin(BaseModel):
    """Schema for user login credentials."""
    username: str = Field(..., description="Registered username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Schema for JWT authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    """Schema for public user profile representation."""
    id: int
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PropertyCreate(BaseModel):
    """Schema for creating a rental property."""
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=300)
    landlord_id: Optional[int] = None


class PropertyOut(BaseModel):
    """Schema for returning property details."""
    id: int
    name: str
    address: Optional[str] = None
    landlord_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RoomCreate(BaseModel):
    """Schema for creating a rental room."""
    room_number: str = Field(..., min_length=1, max_length=50)
    property_id: Optional[int] = None
    current_people_count: int = Field(default=1, ge=0)
    invite_code: Optional[str] = None
    status: str = Field(default="empty")
    tenant_id: Optional[int] = None


class RoomOut(BaseModel):
    """Schema for returning room details."""
    id: int
    room_number: str
    property_id: Optional[int] = None
    invite_code: str
    status: str
    current_people_count: int
    tenant_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SystemConfigUpdate(BaseModel):
    """Schema for dynamically updating electricity and water pricing configuration."""
    electricity_vat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    electricity_tier3_price: Optional[float] = Field(default=None, ge=0.0)
    tiers_json: Optional[str] = None
    water_pricing_type: Optional[str] = None
    water_unit_price: Optional[float] = Field(default=None, ge=0.0)
    water_vat_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    water_env_fee_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tiers: Optional[List[Dict[str, Any]]] = None

    @field_validator("water_pricing_type")
    @classmethod
    def validate_water_pricing_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().upper()
            if cleaned not in ("PER_M3", "PER_PERSON"):
                raise ValueError("water_pricing_type must be 'PER_M3' or 'PER_PERSON'")
            return cleaned
        return v
