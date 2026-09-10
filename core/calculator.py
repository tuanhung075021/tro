# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Core mathematical calculation engine for the tro rental utility billing system.

This module is strictly independent of database and web layers, adhering to pure Python
standard library principles for mathematical precision and testability.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from core.models import (
    DisputeResult,
    ElectricityConfig,
    ElectricityResult,
    TierBreakdown,
    WaterConfig,
    WaterResult,
)

Numeric = Union[Decimal, int, float, str]


def _to_decimal(value: Numeric) -> Decimal:
    """Helper to convert any numeric input reliably into Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_currency(value: Numeric) -> Decimal:
    """Rounds a currency value half-up to the nearest integer VND (hàng đồng)."""
    dec_val = _to_decimal(value)
    return dec_val.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def calculate_consumption(
    start: Numeric,
    end: Numeric,
    max_meter: Numeric = Decimal("99999"),
) -> Decimal:
    """Calculates electrical or water consumption between meter readings.

    Handles standard forward consumption as well as meter rollover when end < start.
    Formula when rolled over: (max_meter + 1 - start) + end.
    For a 5-digit meter (max 99.999), 99.850 to 00.120 yields (100.000 - 99.850) + 120 = 270 kWh.
    """
    d_start = _to_decimal(start)
    d_end = _to_decimal(end)
    d_max = _to_decimal(max_meter)

    if d_start < Decimal("0") or d_end < Decimal("0"):
        raise ValueError("Meter readings cannot be negative.")
    if d_max <= Decimal("0"):
        raise ValueError("Maximum meter reading must be greater than zero.")

    if d_end >= d_start:
        return d_end - d_start

    # Meter has rolled over
    rollover_capacity = d_max + Decimal("1")
    return (rollover_capacity - d_start) + d_end


def calculate_quota(num_people: Numeric) -> Decimal:
    """Calculates electricity quota according to Thông tư số 60/2025/TT-BCT.

    Every 4 registered tenants are considered 1 household quota (1 quota).
    1 tenant = 0.25 quota; 2 tenants = 0.50 quota; 5 tenants = 1.25 quota.
    """
    d_people = _to_decimal(num_people)
    if d_people < Decimal("0"):
        raise ValueError("Number of tenants cannot be negative.")
    return d_people / Decimal("4")


def calculate_electricity_tiered(
    consumption: Numeric,
    quota: Numeric,
    config: Optional[ElectricityConfig] = None,
) -> ElectricityResult:
    """Calculates progressive tiered electricity cost according to QĐ 1279/QĐ-BCT & TT 60/2025/TT-BCT.

    Intermediate calculations retain full decimal precision without mid-way rounding.
    Only the final total amount is rounded half-up to whole VND.
    """
    cfg = config if config is not None else ElectricityConfig()
    d_consumption = _to_decimal(consumption)
    d_quota = _to_decimal(quota)

    if d_consumption < Decimal("0"):
        raise ValueError("Electricity consumption cannot be negative.")
    if d_quota <= Decimal("0"):
        raise ValueError("Electricity quota must be greater than zero.")

    remaining = d_consumption
    pre_tax_total = Decimal("0")
    breakdown: list[TierBreakdown] = []

    for tier in cfg.tiers:
        if tier.max_threshold is not None:
            tier_threshold = tier.max_threshold * d_quota
            kwh_in_tier = min(remaining, tier_threshold)
        else:
            tier_threshold = None
            kwh_in_tier = remaining

        tier_amount = kwh_in_tier * tier.unit_price
        pre_tax_total += tier_amount

        breakdown.append(
            TierBreakdown(
                tier_number=tier.tier_number,
                threshold_applied=tier_threshold,
                kwh_used=kwh_in_tier,
                unit_price=tier.unit_price,
                amount=tier_amount,
            )
        )

        remaining -= kwh_in_tier
        if remaining <= Decimal("0") and tier.max_threshold is not None:
            break

    vat_amount = pre_tax_total * cfg.vat_rate
    raw_total = pre_tax_total + vat_amount
    total_amount = round_currency(raw_total)

    return ElectricityResult(
        consumption_kwh=d_consumption,
        quota=d_quota,
        pre_tax_amount=pre_tax_total,
        vat_amount=vat_amount,
        total_amount=total_amount,
        breakdown=breakdown,
        method="TIERED",
    )


def calculate_electricity_tier3(
    consumption: Numeric,
    config: Optional[ElectricityConfig] = None,
) -> ElectricityResult:
    """Calculates flat Tier 3 electricity cost for undeclared tenant count per TT 60/2025/TT-BCT.

    Entire consumption is multiplied by Tier 3 unit price (default 2.380 đ/kWh) + 8% VAT.
    """
    cfg = config if config is not None else ElectricityConfig()
    d_consumption = _to_decimal(consumption)

    if d_consumption < Decimal("0"):
        raise ValueError("Electricity consumption cannot be negative.")

    pre_tax_total = d_consumption * cfg.tier3_price
    vat_amount = pre_tax_total * cfg.vat_rate
    raw_total = pre_tax_total + vat_amount
    total_amount = round_currency(raw_total)

    breakdown = [
        TierBreakdown(
            tier_number=3,
            threshold_applied=None,
            kwh_used=d_consumption,
            unit_price=cfg.tier3_price,
            amount=pre_tax_total,
        )
    ]

    return ElectricityResult(
        consumption_kwh=d_consumption,
        quota=Decimal("0"),
        pre_tax_amount=pre_tax_total,
        vat_amount=vat_amount,
        total_amount=total_amount,
        breakdown=breakdown,
        method="TIER_3",
    )


def calculate_water(
    usage: Numeric,
    config: Optional[WaterConfig] = None,
) -> WaterResult:
    """Calculates water cost including VAT (5%) and environmental protection fee (10%).

    Both VAT and environmental protection fees are computed on the pre-tax water amount.
    """
    cfg = config if config is not None else WaterConfig()
    d_usage = _to_decimal(usage)

    if d_usage < Decimal("0"):
        raise ValueError("Water usage cannot be negative.")

    pre_tax_amount = d_usage * cfg.unit_price
    vat_amount = pre_tax_amount * cfg.vat_rate
    env_fee_amount = pre_tax_amount * cfg.env_fee_rate
    raw_total = pre_tax_amount + vat_amount + env_fee_amount
    total_amount = round_currency(raw_total)

    return WaterResult(
        usage=d_usage,
        pre_tax_amount=pre_tax_amount,
        vat_amount=vat_amount,
        env_fee_amount=env_fee_amount,
        total_amount=total_amount,
    )


def calculate_dispute(
    calculated_total: Numeric,
    actual_collected: Numeric,
) -> DisputeResult:
    """Compares actual landlord charges against statutory calculations.

    A positive diff_amount indicates the tenant is being overcharged.
    """
    d_calc = _to_decimal(calculated_total)
    d_actual = _to_decimal(actual_collected)
    diff = d_actual - d_calc
    is_overcharged = diff > Decimal("0")

    return DisputeResult(
        calculated_amount=d_calc,
        actual_amount=d_actual,
        diff_amount=diff,
        is_overcharged=is_overcharged,
    )
