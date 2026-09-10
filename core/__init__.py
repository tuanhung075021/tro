# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Core calculation engine package for the tro project."""

from core.models import (
    DisputeResult,
    ElectricityConfig,
    ElectricityResult,
    TariffTier,
    TierBreakdown,
    WaterConfig,
    WaterPricingType,
    WaterResult,
    get_default_electricity_tiers,
)
from core.calculator import (
    calculate_consumption,
    calculate_dispute,
    calculate_electricity_tier3,
    calculate_electricity_tiered,
    calculate_quota,
    calculate_water,
    round_currency,
)

__all__ = [
    "TariffTier",
    "ElectricityConfig",
    "WaterPricingType",
    "WaterConfig",
    "TierBreakdown",
    "ElectricityResult",
    "WaterResult",
    "DisputeResult",
    "get_default_electricity_tiers",
    "calculate_consumption",
    "calculate_quota",
    "calculate_electricity_tiered",
    "calculate_electricity_tier3",
    "calculate_water",
    "calculate_dispute",
    "round_currency",
]
