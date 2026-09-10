# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Core calculation engine package for the tro project."""

from core.models import (
    DisputeResult,
    ElectricityConfig,
    ElectricityResult,
    LossAllocationMethod,
    ProratedQuotaResult,
    SharedMeterResult,
    SubMeterReading,
    TariffTier,
    TenantStayPeriod,
    TierBreakdown,
    WaterConfig,
    WaterPricingType,
    WaterResult,
    get_default_electricity_tiers,
)
from core.calculator import (
    allocate_shared_meter,
    calculate_consumption,
    calculate_dispute,
    calculate_electricity_tier3,
    calculate_electricity_tiered,
    calculate_prorated_quota,
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
    "LossAllocationMethod",
    "SubMeterReading",
    "SharedMeterResult",
    "TenantStayPeriod",
    "ProratedQuotaResult",
    "get_default_electricity_tiers",
    "calculate_consumption",
    "calculate_quota",
    "calculate_electricity_tiered",
    "calculate_electricity_tier3",
    "calculate_water",
    "calculate_dispute",
    "round_currency",
    "allocate_shared_meter",
    "calculate_prorated_quota",
]
