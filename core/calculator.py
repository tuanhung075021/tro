# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Core mathematical calculation engine for the tro. rental utility billing system.

This module is strictly independent of database and web layers, adhering to pure Python
standard library principles for mathematical precision and testability.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from core.models import (
    DisputeResult,
    ElectricityConfig,
    ElectricityResult,
    LossAllocationMethod,
    ProratedQuotaResult,
    SharedMeterResult,
    SubMeterReading,
    TenantStayPeriod,
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


def allocate_shared_meter(
    master_consumption: Decimal,
    sub_readings: list[SubMeterReading],
    method: LossAllocationMethod = LossAllocationMethod.PROPORTIONAL,
) -> SharedMeterResult:
    """Allocates master meter consumption difference (loss/common area) to individual rooms.

    Args:
        master_consumption: Total consumption recorded by the master meter.
        sub_readings: List of sub-meter readings for individual rooms.
        method: Allocation method (PROPORTIONAL based on consumption or EQUAL per room).

    Returns:
        SharedMeterResult containing breakdown of total consumption, loss, and allocations.

    Raises:
        ValueError: If master_consumption < total_sub, negative readings, or sub_readings is empty.
    """
    d_master = _to_decimal(master_consumption)
    if d_master < Decimal("0"):
        raise ValueError("Master meter consumption cannot be negative.")

    if not sub_readings:
        raise ValueError("sub_readings cannot be empty.")

    # Normalize allocation method (support case-insensitive string or enum)
    if isinstance(method, str):
        try:
            method = LossAllocationMethod(method.upper())
        except ValueError:
            raise ValueError(f"Unsupported allocation method: {method}")
    elif not isinstance(method, LossAllocationMethod):
        raise ValueError(f"Unsupported allocation method: {method}")

    room_ids = [r.room_id for r in sub_readings]
    if len(room_ids) != len(set(room_ids)):
        raise ValueError("Duplicate room_id found in sub_readings.")

    for r in sub_readings:
        if _to_decimal(r.consumption) < Decimal("0"):
            raise ValueError(f"Sub-meter consumption cannot be negative for room '{r.room_id}'.")

    total_sub = sum(_to_decimal(r.consumption) for r in sub_readings)

    if d_master < total_sub:
        raise ValueError(
            f"Master consumption ({d_master}) cannot be less than total sub-meter consumption ({total_sub})."
        )

    loss_consumption = d_master - total_sub
    num_rooms = Decimal(len(sub_readings))
    allocations: dict[str, Decimal] = {}

    if method == LossAllocationMethod.PROPORTIONAL:
        if total_sub == Decimal("0"):
            equal_share = loss_consumption / num_rooms
            allocations = {r.room_id: equal_share for r in sub_readings}
        else:
            allocations = {
                r.room_id: (_to_decimal(r.consumption) * loss_consumption) / total_sub
                for r in sub_readings
            }
    elif method == LossAllocationMethod.EQUAL:
        equal_share = loss_consumption / num_rooms
        allocations = {r.room_id: equal_share for r in sub_readings}

    return SharedMeterResult(
        master_consumption=d_master,
        total_sub_consumption=total_sub,
        loss_consumption=loss_consumption,
        allocations=allocations,
    )


def calculate_prorated_quota(
    days_in_month: int,
    tenant_stays: list[TenantStayPeriod],
) -> ProratedQuotaResult:
    """Calculates effective electricity quota prorated by actual residency days.

    Formula: effective_quota = sum(days_stayed) / (4 * days_in_month)

    Args:
        days_in_month: Number of calendar days in the billing cycle (e.g. 28, 29, 30, 31).
        tenant_stays: List of tenant stay records within the month.

    Returns:
        ProratedQuotaResult with effective_quota and detailed breakdown per tenant.

    Raises:
        ValueError: If days_in_month <= 0, days_stayed < 0, or tenant days exceed days_in_month.
        TypeError: If days_in_month is boolean or not an integer.
    """
    if isinstance(days_in_month, bool) or not isinstance(days_in_month, int):
        raise TypeError("days_in_month must be an integer.")

    if days_in_month <= 0:
        raise ValueError("days_in_month must be greater than zero.")

    if not tenant_stays:
        return ProratedQuotaResult(
            total_days_in_month=days_in_month,
            effective_quota=Decimal("0"),
            details=[],
        )

    tenant_cumulative_days: dict[str, int] = {}
    for stay in tenant_stays:
        if stay.days_stayed < 0:
            raise ValueError(f"days_stayed cannot be negative for tenant '{stay.tenant_name}'.")
        if stay.days_stayed > days_in_month:
            raise ValueError(
                f"Tenant '{stay.tenant_name}' stayed {stay.days_stayed} days, "
                f"which exceeds days in month ({days_in_month})."
            )
        tenant_cumulative_days[stay.tenant_name] = (
            tenant_cumulative_days.get(stay.tenant_name, 0) + stay.days_stayed
        )
        if tenant_cumulative_days[stay.tenant_name] > days_in_month:
            raise ValueError(
                f"Cumulative days stayed for tenant '{stay.tenant_name}' "
                f"({tenant_cumulative_days[stay.tenant_name]}) exceeds days in month ({days_in_month})."
            )

    total_person_days = sum(Decimal(stay.days_stayed) for stay in tenant_stays)
    divisor = Decimal("4") * Decimal(days_in_month)
    effective_quota = total_person_days / divisor

    details = [
        {
            "tenant_name": stay.tenant_name,
            "days_stayed": stay.days_stayed,
            "effective_quota": Decimal(stay.days_stayed) / divisor,
        }
        for stay in tenant_stays
    ]

    return ProratedQuotaResult(
        total_days_in_month=days_in_month,
        effective_quota=effective_quota,
        details=details,
    )
