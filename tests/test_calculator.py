# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Unit test suite for core calculation engine, validating against official OLP PMNM exam test cases."""

from decimal import Decimal
import unittest

from core.calculator import (
    calculate_consumption,
    calculate_dispute,
    calculate_electricity_tier3,
    calculate_electricity_tiered,
    calculate_quota,
    calculate_water,
    round_currency,
)
from core.models import (
    ElectricityConfig,
    TariffTier,
    WaterConfig,
    WaterPricingType,
)


class TestCoreCalculator(unittest.TestCase):
    """Test suite covering standard and edge calculations according to competition guidelines."""

    def test_calculate_consumption_normal(self):
        """Test normal consumption when end reading > start reading."""
        consumption = calculate_consumption(start=100, end=250)
        self.assertEqual(consumption, Decimal("150"))

    def test_calculate_consumption_same_reading(self):
        """Test zero consumption when start == end."""
        consumption = calculate_consumption(start=500, end=500)
        self.assertEqual(consumption, Decimal("0"))

    def test_calculate_consumption_rollover_case_4(self):
        """Test Case 4: 5-digit meter rollover (99.850 -> 00.120) must equal 270 kWh."""
        consumption = calculate_consumption(start=99850, end=120, max_meter=99999)
        self.assertEqual(consumption, Decimal("270"))

    def test_calculate_consumption_invalid_negative(self):
        """Test that negative readings raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_consumption(start=-10, end=100)
        with self.assertRaises(ValueError):
            calculate_consumption(start=100, end=-5)

    def test_calculate_quota_tt60(self):
        """Test quota determination per Thông tư 60/2025/TT-BCT (num_people / 4)."""
        self.assertEqual(calculate_quota(1), Decimal("0.25"))
        self.assertEqual(calculate_quota(2), Decimal("0.50"))
        self.assertEqual(calculate_quota(3), Decimal("0.75"))
        self.assertEqual(calculate_quota(4), Decimal("1.00"))
        self.assertEqual(calculate_quota(5), Decimal("1.25"))
        self.assertEqual(calculate_quota(8), Decimal("2.00"))

    def test_calculate_quota_invalid_negative(self):
        """Test that negative people count raises ValueError."""
        with self.assertRaises(ValueError):
            calculate_quota(-1)

    def test_exam_case_1(self):
        """Case 1: 4 people (1.00 quota), 120 kWh -> 269.244 VND.

        Tier 1: 50 kWh * 1984 = 99.200
        Tier 2: 50 kWh * 2050 = 102.500
        Tier 3: 20 kWh * 2380 = 47.600
        Pre-tax: 249.300, VAT: 19.944, Total: 269.244
        """
        quota = calculate_quota(4)
        result = calculate_electricity_tiered(consumption=120, quota=quota)

        self.assertEqual(result.consumption_kwh, Decimal("120"))
        self.assertEqual(result.quota, Decimal("1"))
        self.assertEqual(result.pre_tax_amount, Decimal("249300"))
        self.assertEqual(result.vat_amount, Decimal("19944"))
        self.assertEqual(result.total_amount, Decimal("269244"))
        self.assertEqual(len(result.breakdown), 3)

        self.assertEqual(result.breakdown[0].kwh_used, Decimal("50"))
        self.assertEqual(result.breakdown[0].amount, Decimal("99200"))
        self.assertEqual(result.breakdown[1].kwh_used, Decimal("50"))
        self.assertEqual(result.breakdown[1].amount, Decimal("102500"))
        self.assertEqual(result.breakdown[2].kwh_used, Decimal("20"))
        self.assertEqual(result.breakdown[2].amount, Decimal("47600"))

    def test_exam_case_2(self):
        """Case 2: 5 people (1.25 quota), 200 kWh -> 465.075 VND.

        Tier 1: 62.5 kWh * 1984 = 124.000
        Tier 2: 62.5 kWh * 2050 = 128.125
        Tier 3: 75.0 kWh * 2380 = 178.500
        Pre-tax: 430.625, VAT: 34.450, Total: 465.075
        """
        quota = calculate_quota(5)
        result = calculate_electricity_tiered(consumption=200, quota=quota)

        self.assertEqual(result.consumption_kwh, Decimal("200"))
        self.assertEqual(result.quota, Decimal("1.25"))
        self.assertEqual(result.pre_tax_amount, Decimal("430625"))
        self.assertEqual(result.vat_amount, Decimal("34450"))
        self.assertEqual(result.total_amount, Decimal("465075"))
        self.assertEqual(len(result.breakdown), 3)

        self.assertEqual(result.breakdown[0].kwh_used, Decimal("62.5"))
        self.assertEqual(result.breakdown[0].threshold_applied, Decimal("62.5"))
        self.assertEqual(result.breakdown[0].amount, Decimal("124000"))

        self.assertEqual(result.breakdown[1].kwh_used, Decimal("62.5"))
        self.assertEqual(result.breakdown[1].threshold_applied, Decimal("62.5"))
        self.assertEqual(result.breakdown[1].amount, Decimal("128125"))

        self.assertEqual(result.breakdown[2].kwh_used, Decimal("75.0"))
        self.assertEqual(result.breakdown[2].threshold_applied, Decimal("125.0"))
        self.assertEqual(result.breakdown[2].amount, Decimal("178500"))

    def test_exam_case_3(self):
        """Case 3: 1 person (0.25 quota), 60 kWh -> 151.097 VND (half-up rounding).

        Tier 1: 12.5 kWh * 1984 = 24.800
        Tier 2: 12.5 kWh * 2050 = 25.625
        Tier 3: 25.0 kWh * 2380 = 59.500
        Tier 4: 10.0 kWh * 2998 = 29.980
        Pre-tax: 139.905, VAT: 11.192.40, Total: 151.097.40 -> rounds to 151.097
        """
        quota = calculate_quota(1)
        result = calculate_electricity_tiered(consumption=60, quota=quota)

        self.assertEqual(result.pre_tax_amount, Decimal("139905"))
        self.assertEqual(result.vat_amount, Decimal("11192.40"))
        self.assertEqual(result.total_amount, Decimal("151097"))
        self.assertEqual(len(result.breakdown), 4)

    def test_exam_case_4(self):
        """Case 4: 4 people (1.00 quota), 270 kWh -> 701.525 VND (half-up rounding).

        Rollover consumption: 270 kWh
        Tier 1: 50 * 1984 = 99.200
        Tier 2: 50 * 2050 = 102.500
        Tier 3: 100 * 2380 = 238.000
        Tier 4: 70 * 2998 = 209.860
        Pre-tax: 649.560, VAT: 51.964.80, Total: 701.524.80 -> rounds to 701.525
        """
        consumption = calculate_consumption(start=99850, end=120)
        self.assertEqual(consumption, Decimal("270"))

        quota = calculate_quota(4)
        result = calculate_electricity_tiered(consumption=consumption, quota=quota)

        self.assertEqual(result.pre_tax_amount, Decimal("649560"))
        self.assertEqual(result.vat_amount, Decimal("51964.80"))
        self.assertEqual(result.total_amount, Decimal("701525"))

    def test_exam_case_5(self):
        """Case 5: 120 kWh under undeclared flat Tier 3 -> 308.448 VND.

        120 * 2380 = 285.600, VAT 8% = 22.848, Total = 308.448
        Comparison to Case 1 difference: 308.448 - 269.244 = 39.204 VND.
        """
        res_tier3 = calculate_electricity_tier3(consumption=120)
        self.assertEqual(res_tier3.pre_tax_amount, Decimal("285600"))
        self.assertEqual(res_tier3.vat_amount, Decimal("22848"))
        self.assertEqual(res_tier3.total_amount, Decimal("308448"))

        res_tiered = calculate_electricity_tiered(consumption=120, quota=calculate_quota(4))
        dispute = calculate_dispute(
            calculated_total=res_tiered.total_amount,
            actual_collected=res_tier3.total_amount,
        )
        self.assertEqual(dispute.diff_amount, Decimal("39204"))

    def test_exam_case_6(self):
        """Case 6: Water calculation per m3 (12 m3) -> 117.300 VND.

        Pre-tax: 12 * 8.500 = 102.000
        VAT (5%): 5.100
        Env fee (10%): 10.200
        Total: 117.300
        """
        cfg = WaterConfig(pricing_type=WaterPricingType.PER_M3, unit_price=Decimal("8500"))
        water = calculate_water(usage=12, config=cfg)

        self.assertEqual(water.pre_tax_amount, Decimal("102000"))
        self.assertEqual(water.vat_amount, Decimal("5100"))
        self.assertEqual(water.env_fee_amount, Decimal("10200"))
        self.assertEqual(water.total_amount, Decimal("117300"))

    def test_water_per_person(self):
        """Test water calculation per person (4 people @ 80.000 VND).

        Pre-tax: 4 * 80.000 = 320.000
        VAT (5%): 16.000
        Env fee (10%): 32.000
        Total: 368.000
        """
        cfg = WaterConfig(pricing_type=WaterPricingType.PER_PERSON, unit_price=Decimal("80000"))
        water = calculate_water(usage=4, config=cfg)

        self.assertEqual(water.pre_tax_amount, Decimal("320000"))
        self.assertEqual(water.vat_amount, Decimal("16000"))
        self.assertEqual(water.env_fee_amount, Decimal("32000"))
        self.assertEqual(water.total_amount, Decimal("368000"))

    def test_exam_case_7_dispute(self):
        """Case 7: Case 1 with flat rate 4.000 VND/kWh (480.000 VND collected).

        Calculated: 269.244 VND
        Overcharged diff: 480.000 - 269.244 = 210.756 VND
        """
        calculated_amount = Decimal("269244")
        actual_collected = Decimal("120") * Decimal("4000")  # 480.000
        dispute = calculate_dispute(calculated_amount, actual_collected)

        self.assertEqual(dispute.diff_amount, Decimal("210756"))
        self.assertTrue(dispute.is_overcharged)

    def test_round_currency(self):
        """Test half-up rounding precision."""
        self.assertEqual(round_currency(Decimal("151097.40")), Decimal("151097"))
        self.assertEqual(round_currency(Decimal("151097.50")), Decimal("151098"))
        self.assertEqual(round_currency(Decimal("701524.80")), Decimal("701525"))


if __name__ == "__main__":
    unittest.main()
