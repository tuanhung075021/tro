# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Statutory electricity and water tariff catalogue across legal decrees."""

import copy
from typing import Any, Dict, List, Optional

STATUTORY_TARIFF_HISTORY: Dict[str, Dict[str, Any]] = {
    "QD-1279-2023": {
        "version": "QD-1279-2023",
        "legal_basis": "Quyết định 1279/QĐ-BCT & Nghị quyết 204/2025/QH15",
        "description": "Biểu giá bán lẻ điện sinh hoạt 6 bậc thang và thuế suất GTGT 8%",
        "effective_date": "2023-11-09",
        "effective_from": "2023-11-09",
        "vat_rate": 8.0,
        "electricity_vat_rate": 0.08,
        "electricity_tier3_price": 2380.0,
        "tiers": [
            {"tier_number": 1, "max_threshold": 50.0, "unit_price": 1984.0},
            {"tier_number": 2, "max_threshold": 50.0, "unit_price": 2050.0},
            {"tier_number": 3, "max_threshold": 100.0, "unit_price": 2380.0},
            {"tier_number": 4, "max_threshold": 100.0, "unit_price": 2998.0},
            {"tier_number": 5, "max_threshold": 100.0, "unit_price": 3350.0},
            {"tier_number": 6, "max_threshold": None, "unit_price": 3460.0},
        ],
        "water_rate": 8500.0,
        "water_unit_price": 8500.0,
        "water_pricing_type": "PER_M3",
        "water_vat_rate": 0.05,
        "water_env_fee_rate": 0.10,
    }
}


def get_latest_statutory_tariff() -> Dict[str, Any]:
    """Return the most current statutory tariff configuration."""
    return copy.deepcopy(STATUTORY_TARIFF_HISTORY["QD-1279-2023"])


def get_tariff_by_version(version: str) -> Optional[Dict[str, Any]]:
    """Retrieve statutory tariff configuration by its decree version key."""
    if not isinstance(version, str):
        return None
    tariff = STATUTORY_TARIFF_HISTORY.get(version.strip())
    if tariff is None:
        return None
    return copy.deepcopy(tariff)
