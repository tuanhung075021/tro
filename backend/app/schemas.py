# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Pydantic data schemas for authentication, role-based access, properties, and rooms."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserRegister(BaseModel):
    """Schema for user registration with optional room invite code."""
    username: str = Field(..., min_length=1, max_length=100, description="Unique username")
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
    tariff_type: Optional[str] = "statutory"  # "statutory" | "custom"
    custom_elec_rate: Optional[float] = Field(default=None, ge=0.0)
    custom_water_rate: Optional[float] = Field(default=None, ge=0.0)
    custom_water_type: Optional[str] = "PER_M3"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Property name cannot be empty or whitespace")
        return cleaned


class PropertyUpdate(BaseModel):
    """Schema for updating a rental property and its tariff configuration."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=300)
    tariff_type: Optional[str] = None
    custom_elec_rate: Optional[float] = Field(default=None, ge=0.0)
    custom_water_rate: Optional[float] = Field(default=None, ge=0.0)
    custom_water_type: Optional[str] = None


class PropertyOut(BaseModel):
    """Schema for returning property details."""
    id: int
    name: str
    address: Optional[str] = None
    landlord_id: Optional[int] = None
    tariff_type: Optional[str] = "statutory"
    custom_elec_rate: Optional[float] = None
    custom_water_rate: Optional[float] = None
    custom_water_type: Optional[str] = "PER_M3"

    model_config = ConfigDict(from_attributes=True)


class RoomCreate(BaseModel):
    """Schema for creating a rental room."""
    room_number: str = Field(..., min_length=1, max_length=50)
    property_id: Optional[int] = None
    current_people_count: int = Field(default=1, ge=0)
    invite_code: Optional[str] = None
    status: str = Field(default="empty")
    tenant_id: Optional[int] = None

    @field_validator("room_number")
    @classmethod
    def validate_room_number(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Room number cannot be empty or whitespace")
        return cleaned


class RoomOut(BaseModel):
    """Schema for returning room details enriched with tenant and property metadata."""
    id: int
    room_number: str
    property_id: Optional[int] = None
    invite_code: str
    status: str
    current_people_count: int
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    tenant_phone: Optional[str] = None
    property_name: Optional[str] = None
    property_address: Optional[str] = None
    landlord_name: Optional[str] = None
    landlord_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TenantRoomOut(RoomOut):
    """Schema for returning room information tailored to the assigned tenant."""
    pass


class AssignTenantRequest(BaseModel):
    """Schema for landlord assigning a tenant to a room via username or phone."""
    username: Optional[str] = Field(default=None, max_length=50, description="Tenant username")
    phone: Optional[str] = Field(default=None, max_length=20, description="Tenant phone number")

    @field_validator("username", "phone")
    @classmethod
    def clean_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class RoomJoinRequest(BaseModel):
    """Schema for a tenant self-associating with a room via invite code."""
    invite_code: str = Field(..., min_length=1, max_length=20, description="Room invite code")

    @field_validator("invite_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Invite code cannot be empty or whitespace")
        return cleaned


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

    @field_validator("tiers")
    @classmethod
    def validate_tiers(cls, v: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if v is not None:
            if not v:
                raise ValueError("Tiers list cannot be empty")
            for idx, tier in enumerate(v):
                if not isinstance(tier, dict):
                    raise ValueError(f"Tier at index {idx} must be a dictionary")
                if "tier_number" not in tier or "unit_price" not in tier:
                    raise ValueError(f"Tier at index {idx} must contain 'tier_number' and 'unit_price'")
                try:
                    t_num = int(tier["tier_number"])
                    if t_num <= 0:
                        raise ValueError
                except (ValueError, TypeError):
                    raise ValueError(f"Tier at index {idx}: 'tier_number' must be a positive integer")
                try:
                    price = float(tier["unit_price"])
                    if price < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    raise ValueError(f"Tier at index {idx}: 'unit_price' must be non-negative")
        return v

    @field_validator("tiers_json")
    @classmethod
    def validate_tiers_json(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import json
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError("tiers_json must encode a JSON list")
            except Exception as exc:
                raise ValueError(f"Invalid tiers_json format: {exc}")
        return v


class SystemConfigOut(BaseModel):
    """Schema for returning system pricing configuration."""
    id: Optional[int] = None
    electricity_vat_rate: float
    electricity_tier3_price: float
    tiers_json: str
    tiers: List[Dict[str, Any]]
    water_pricing_type: str
    water_unit_price: float
    water_vat_rate: float
    water_env_fee_rate: float
    tariff_version: Optional[str] = "QD-1279-2023"
    tariff_updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MeterReadingCreate(BaseModel):
    """Schema for recording monthly meter readings for a room."""
    month_year: str = Field(..., description="Format YYYY-MM")
    elec_start: float = Field(default=0.0, ge=0.0)
    elec_end: float = Field(default=0.0, ge=0.0)
    water_start: float = Field(default=0.0, ge=0.0)
    water_end: float = Field(default=0.0, ge=0.0)

    @field_validator("month_year")
    @classmethod
    def validate_month_year(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("month_year cannot be empty or whitespace")
        return cleaned


class MeterReadingOut(BaseModel):
    """Schema for returning recorded meter readings."""
    id: int
    room_id: int
    month_year: str
    elec_start: float
    elec_end: float
    water_start: float
    water_end: float
    recorded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceCalculateRequest(BaseModel):
    """Schema for calculating and generating a room invoice."""
    month_year: str = Field(..., description="Format YYYY-MM")
    reading_id: Optional[int] = None
    elec_start: Optional[float] = Field(default=None, ge=0.0)
    elec_end: Optional[float] = Field(default=None, ge=0.0)
    water_start: Optional[float] = Field(default=None, ge=0.0)
    water_end: Optional[float] = Field(default=None, ge=0.0)
    actual_collected: Optional[float] = Field(default=None, ge=0.0)
    actual_collected_amount: Optional[float] = Field(default=None, ge=0.0)
    has_registered_quota: Optional[bool] = None
    registered_quota: Optional[bool] = None
    use_tier3: Optional[bool] = None
    water_usage: Optional[float] = Field(default=None, ge=0.0)
    max_meter: Optional[float] = Field(default=99999.0, gt=0.0)
    people_count: Optional[int] = Field(default=None, ge=0)

    @field_validator("month_year")
    @classmethod
    def validate_month_year(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("month_year cannot be empty or whitespace")
        return cleaned


class InvoiceOut(BaseModel):
    """Schema for returning invoice details, breakdowns, and dispute comparisons."""
    id: int
    room_id: int
    month_year: str
    elec_kwh: float
    elec_amount: float
    water_usage: float
    water_amount: float
    total_statutory_amount: float
    actual_collected_amount: float
    diff_amount: float
    share_token: str
    short_code: Optional[str] = None
    status: str = "draft"
    published_at: Optional[datetime] = None
    breakdown_json: Optional[str] = None
    breakdown: Optional[Dict[str, Any]] = None
    room_number: Optional[str] = None
    property_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Admin and Statutory Tariff Schemas
# ============================================================================


class AdminApprovalRequestOut(BaseModel):
    """Schema for admin approval audit requests."""
    id: int
    user_id: int
    secret_key_id: int
    requested_at: datetime
    status: str
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminRejectIn(BaseModel):
    """Schema for admin rejection payload."""
    reject_reason: Optional[str] = None


AdminRejectPayload = AdminRejectIn


class ChangePasswordIn(BaseModel):
    """Schema for user changing their own password."""
    current_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới (tối thiểu 6 ký tự)")
    confirm_password: str = Field(..., min_length=6, description="Xác nhận mật khẩu mới")


class SecretRotateIn(BaseModel):
    """Schema for admin secret key rotation."""
    new_secret: str = Field(..., min_length=8, description="Khóa bí mật mới")
    admin_password: str = Field(..., min_length=1, description="Mật khẩu xác thực của Root Admin")


SecretRotateRequest = SecretRotateIn


class SecretRevealIn(BaseModel):
    """Schema for Root Admin requesting to reveal the active secret key."""
    admin_password: str = Field(..., min_length=1, description="Mật khẩu xác thực của Root Admin")


class TariffTierIn(BaseModel):
    """Schema for a single progressive electricity tariff tier."""
    tier_name: str = "Bậc"
    min_kwh: int = 0
    max_kwh: Optional[int] = None
    unit_price: float
    tier_number: Optional[int] = None
    max_threshold: Optional[float] = None


class TariffUpdateIn(BaseModel):
    """Schema for updating dynamic statutory electricity and water tariffs."""
    electricity_tiers: List[TariffTierIn]
    vat_rate: float
    water_rate: float
    note: Optional[str] = None
    tariff_version: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "electricity_tiers" not in data and "tiers" in data:
                data["electricity_tiers"] = data["tiers"]
            if "vat_rate" not in data and "electricity_vat_rate" in data:
                data["vat_rate"] = data["electricity_vat_rate"]
            if "water_rate" not in data and "water_unit_price" in data:
                data["water_rate"] = data["water_unit_price"]
        return data


class TariffOut(BaseModel):
    """Schema for statutory tariff response."""
    tariff_version: str
    tariff_updated_at: Optional[datetime] = None
    electricity_tiers: list
    vat_rate: float
    water_rate: float

    model_config = ConfigDict(from_attributes=True)


class TariffChangeLogOut(BaseModel):
    """Schema for returning historical tariff updates."""
    id: int
    changed_by_id: int
    changed_at: datetime
    tariff_version: str
    snapshot_json: str
    note: Optional[str] = None
    changed_by_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserOut(BaseModel):
    """Schema for admin user details and role status."""
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    is_root_admin: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


