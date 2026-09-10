# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Database entities and dynamic pricing models for tro backend."""

from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict, List, Optional
import uuid

# Ensure compatibility shim is active if sqlmodel is not installed
from .compat import SQLModel, Field


def get_default_tiers() -> List[Dict[str, Any]]:
    """Return default 6-tier progressive electricity tariff per QĐ 1279/QĐ-BCT."""
    return [
        {"tier_number": 1, "max_threshold": 50.0, "unit_price": 1984.0},
        {"tier_number": 2, "max_threshold": 50.0, "unit_price": 2050.0},
        {"tier_number": 3, "max_threshold": 100.0, "unit_price": 2380.0},
        {"tier_number": 4, "max_threshold": 100.0, "unit_price": 2998.0},
        {"tier_number": 5, "max_threshold": 100.0, "unit_price": 3350.0},
        {"tier_number": 6, "max_threshold": None, "unit_price": 3460.0},
    ]


DEFAULT_TIERS_JSON: str = json.dumps(get_default_tiers(), ensure_ascii=False)


def generate_invite_code(length: int = 8) -> str:
    """Generate a random alphanumeric invite code of 6-8 characters."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class User(SQLModel, table=True):
    """User account entity (landlords and tenants)."""
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    role: str = Field(default="tenant")  # "landlord" or "tenant"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_landlord(self) -> bool:
        return self.role == "landlord"

    @property
    def is_tenant(self) -> bool:
        return self.role == "tenant"


class Property(SQLModel, table=True):
    """Rental property entity (Khu trọ) managed by a landlord."""
    __tablename__ = "property"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: Optional[str] = Field(default=None)
    landlord_id: Optional[int] = Field(default=None, foreign_key="user.id")


class Room(SQLModel, table=True):
    """Rental room entity (Phòng trọ) within a property."""
    __tablename__ = "room"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    property_id: Optional[int] = Field(default=None, foreign_key="property.id")
    invite_code: str = Field(default_factory=lambda: generate_invite_code(8), unique=True, index=True)
    status: str = Field(default="active")  # "active", "empty"
    current_people_count: int = Field(default=1)


class SystemConfig(SQLModel, table=True):
    """Dynamic pricing configuration for electricity and water tariffs.

    Enables dynamic configuration without hardcoding values in source code:
    - electricity_vat_rate (default 0.08 per Nghị quyết 204/2025/QH15)
    - electricity_tier3_price (default 2380.0 per Thông tư 60/2025/TT-BCT)
    - tiers_json (6 progressive tiers per Quyết định 1279/QĐ-BCT)
    - water_pricing_type ("PER_M3" or "PER_PERSON")
    - water_unit_price (default 8500.0 đ/m³)
    - water_vat_rate (default 0.05)
    - water_env_fee_rate (default 0.10)
    """
    __tablename__ = "systemconfig"

    id: Optional[int] = Field(default=1, primary_key=True)
    electricity_vat_rate: float = Field(default=0.08)
    electricity_tier3_price: float = Field(default=2380.0)
    tiers_json: str = Field(default=DEFAULT_TIERS_JSON)
    water_pricing_type: str = Field(default="PER_M3")  # "PER_M3" or "PER_PERSON"
    water_unit_price: float = Field(default=8500.0)
    water_vat_rate: float = Field(default=0.05)
    water_env_fee_rate: float = Field(default=0.10)

    def get_tiers(self) -> List[Dict[str, Any]]:
        """Parse and return tiers as a Python list of dictionaries."""
        if not self.tiers_json:
            return get_default_tiers()
        try:
            return json.loads(self.tiers_json)
        except (ValueError, TypeError):
            return get_default_tiers()

    def set_tiers(self, tiers: List[Dict[str, Any]]) -> None:
        """Serialize and store tiers list into tiers_json field."""
        if not isinstance(tiers, list):
            raise TypeError("Tiers must be a list of tier dictionary objects.")
        self.tiers_json = json.dumps(tiers, ensure_ascii=False)

    def to_electricity_config(self) -> Any:
        """Bridge database configuration to core.models.ElectricityConfig for calculation."""
        from decimal import Decimal
        from core.models import ElectricityConfig, TariffTier
        tiers_data = self.get_tiers()
        tiers = [
            TariffTier(
                tier_number=int(t["tier_number"]),
                max_threshold=Decimal(str(t["max_threshold"])) if t.get("max_threshold") is not None else None,
                unit_price=Decimal(str(t["unit_price"])),
            )
            for t in tiers_data
        ]
        return ElectricityConfig(
            tiers=tiers,
            vat_rate=Decimal(str(self.electricity_vat_rate)),
            tier3_price=Decimal(str(self.electricity_tier3_price)),
        )

    def to_water_config(self) -> Any:
        """Bridge database configuration to core.models.WaterConfig for calculation."""
        from decimal import Decimal
        from core.models import WaterConfig, WaterPricingType
        return WaterConfig(
            pricing_type=WaterPricingType(self.water_pricing_type),
            unit_price=Decimal(str(self.water_unit_price)),
            vat_rate=Decimal(str(self.water_vat_rate)),
            env_fee_rate=Decimal(str(self.water_env_fee_rate)),
        )

    @classmethod
    def from_configs(cls, elec_cfg: Any, water_cfg: Any, id: int = 1) -> "SystemConfig":
        """Factory creating SystemConfig from core ElectricityConfig and WaterConfig."""
        tiers_list = [
            {
                "tier_number": t.tier_number,
                "max_threshold": float(t.max_threshold) if t.max_threshold is not None else None,
                "unit_price": float(t.unit_price),
            }
            for t in elec_cfg.tiers
        ]
        return cls(
            id=id,
            electricity_vat_rate=float(elec_cfg.vat_rate),
            electricity_tier3_price=float(elec_cfg.tier3_price),
            tiers_json=json.dumps(tiers_list, ensure_ascii=False),
            water_pricing_type=water_cfg.pricing_type.value if hasattr(water_cfg.pricing_type, "value") else str(water_cfg.pricing_type),
            water_unit_price=float(water_cfg.unit_price),
            water_vat_rate=float(water_cfg.vat_rate),
            water_env_fee_rate=float(water_cfg.env_fee_rate),
        )


class MeterReading(SQLModel, table=True):
    """Monthly meter reading entity for a specific room."""
    __tablename__ = "meterreading"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="room.id")
    month_year: str = Field(index=True)  # Format YYYY-MM
    elec_start: float = Field(default=0.0)
    elec_end: float = Field(default=0.0)
    water_start: float = Field(default=0.0)
    water_end: float = Field(default=0.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Invoice(SQLModel, table=True):
    """Monthly room invoice entity with statutory calculation and dispute comparison."""
    __tablename__ = "invoice"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="room.id")
    month_year: str = Field(index=True)  # Format YYYY-MM
    elec_kwh: float = Field(default=0.0)
    elec_amount: float = Field(default=0.0)
    water_usage: float = Field(default=0.0)
    water_amount: float = Field(default=0.0)
    total_statutory_amount: float = Field(default=0.0)
    actual_collected_amount: float = Field(default=0.0)
    diff_amount: float = Field(default=0.0)
    share_token: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True, index=True)
    breakdown_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_breakdown(self) -> Optional[Dict[str, Any]]:
        """Parse breakdown_json into Python dictionary."""
        if not self.breakdown_json:
            return None
        try:
            return json.loads(self.breakdown_json)
        except (ValueError, TypeError):
            return None

    def set_breakdown(self, breakdown: Dict[str, Any]) -> None:
        """Serialize dictionary into breakdown_json field."""
        self.breakdown_json = json.dumps(breakdown, ensure_ascii=False)
