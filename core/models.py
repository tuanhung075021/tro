# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Data models and schemas for the tro core calculation engine."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional


@dataclass
class TariffTier:
    """Represents a single tier in the progressive electricity tariff."""
    tier_number: int
    max_threshold: Optional[Decimal]  # None for the unbounded last tier (tier 6)
    unit_price: Decimal


def get_default_electricity_tiers() -> List[TariffTier]:
    """Default 6-tier progressive electricity tariff according to QĐ 1279/QĐ-BCT."""
    return [
        TariffTier(tier_number=1, max_threshold=Decimal("50"), unit_price=Decimal("1984")),
        TariffTier(tier_number=2, max_threshold=Decimal("50"), unit_price=Decimal("2050")),
        TariffTier(tier_number=3, max_threshold=Decimal("100"), unit_price=Decimal("2380")),
        TariffTier(tier_number=4, max_threshold=Decimal("100"), unit_price=Decimal("2998")),
        TariffTier(tier_number=5, max_threshold=Decimal("100"), unit_price=Decimal("3350")),
        TariffTier(tier_number=6, max_threshold=None, unit_price=Decimal("3460")),
    ]


@dataclass
class ElectricityConfig:
    """Configuration for electricity billing calculations."""
    tiers: List[TariffTier] = field(default_factory=get_default_electricity_tiers)
    vat_rate: Decimal = Decimal("0.08")  # 8% VAT per Nghị quyết 204/2025/QH15
    tier3_price: Decimal = Decimal("2380")  # Tier 3 unit price per TT 60/2025/TT-BCT


class WaterPricingType(str, Enum):
    """Supported water pricing methods."""
    PER_M3 = "PER_M3"
    PER_PERSON = "PER_PERSON"


@dataclass
class WaterConfig:
    """Configuration for water billing calculations."""
    pricing_type: WaterPricingType = WaterPricingType.PER_M3
    unit_price: Decimal = Decimal("8500")  # Default 8.500 đ/m³ or 80.000 đ/person/month
    vat_rate: Decimal = Decimal("0.05")     # 5% VAT for clean water
    env_fee_rate: Decimal = Decimal("0.10") # 10% Environmental protection fee


@dataclass
class TierBreakdown:
    """Detailed breakdown for each tier consumed."""
    tier_number: int
    threshold_applied: Optional[Decimal]
    kwh_used: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class ElectricityResult:
    """Result of electricity calculation."""
    consumption_kwh: Decimal
    quota: Decimal
    pre_tax_amount: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    breakdown: List[TierBreakdown]
    method: str  # "TIERED" or "TIER_3"


@dataclass
class WaterResult:
    """Result of water calculation."""
    usage: Decimal
    pre_tax_amount: Decimal
    vat_amount: Decimal
    env_fee_amount: Decimal
    total_amount: Decimal


@dataclass
class DisputeResult:
    """Result of comparing actual collected money against legal calculations."""
    calculated_amount: Decimal
    actual_amount: Decimal
    diff_amount: Decimal
    is_overcharged: bool
