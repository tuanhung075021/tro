# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Unit test suite for core calculation engine, validating against official OLP PMNM exam test cases."""

from decimal import Decimal
import unittest

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
from core.models import (
    ElectricityConfig,
    LossAllocationMethod,
    ProratedQuotaResult,
    SharedMeterResult,
    SubMeterReading,
    TariffTier,
    TenantStayPeriod,
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

    def test_allocate_shared_meter_proportional(self):
        """Test proportional allocation of master meter loss based on room consumption."""
        readings = [
            SubMeterReading(room_id="P101", consumption=Decimal("100")),
            SubMeterReading(room_id="P102", consumption=Decimal("150")),
            SubMeterReading(room_id="P103", consumption=Decimal("150")),
        ]
        result = allocate_shared_meter(
            master_consumption=Decimal("500"),
            sub_readings=readings,
            method=LossAllocationMethod.PROPORTIONAL,
        )

        self.assertEqual(result.master_consumption, Decimal("500"))
        self.assertEqual(result.total_sub_consumption, Decimal("400"))
        self.assertEqual(result.loss_consumption, Decimal("100"))
        self.assertEqual(result.allocations["P101"], Decimal("25"))
        self.assertEqual(result.allocations["P102"], Decimal("37.5"))
        self.assertEqual(result.allocations["P103"], Decimal("37.5"))
        self.assertEqual(
            sum(result.allocations.values()),
            result.loss_consumption,
        )

    def test_allocate_shared_meter_equal(self):
        """Test equal allocation of master meter loss across all rooms."""
        readings = [
            SubMeterReading(room_id="P101", consumption=Decimal("100")),
            SubMeterReading(room_id="P102", consumption=Decimal("150")),
            SubMeterReading(room_id="P103", consumption=Decimal("150")),
            SubMeterReading(room_id="P104", consumption=Decimal("0")),
        ]
        result = allocate_shared_meter(
            master_consumption=Decimal("500"),
            sub_readings=readings,
            method=LossAllocationMethod.EQUAL,
        )

        self.assertEqual(result.master_consumption, Decimal("500"))
        self.assertEqual(result.total_sub_consumption, Decimal("400"))
        self.assertEqual(result.loss_consumption, Decimal("100"))
        self.assertEqual(result.allocations["P101"], Decimal("25"))
        self.assertEqual(result.allocations["P102"], Decimal("25"))
        self.assertEqual(result.allocations["P103"], Decimal("25"))
        self.assertEqual(result.allocations["P104"], Decimal("25"))
        self.assertEqual(sum(result.allocations.values()), Decimal("100"))

    def test_allocate_shared_meter_proportional_all_zero_consumption(self):
        """When all rooms consume 0 kWh under PROPORTIONAL, loss must be divided equally."""
        readings = [
            SubMeterReading(room_id="P101", consumption=Decimal("0")),
            SubMeterReading(room_id="P102", consumption=Decimal("0")),
            SubMeterReading(room_id="P103", consumption=Decimal("0")),
        ]
        result = allocate_shared_meter(
            master_consumption=Decimal("30"),
            sub_readings=readings,
            method=LossAllocationMethod.PROPORTIONAL,
        )

        self.assertEqual(result.master_consumption, Decimal("30"))
        self.assertEqual(result.total_sub_consumption, Decimal("0"))
        self.assertEqual(result.loss_consumption, Decimal("30"))
        self.assertEqual(result.allocations["P101"], Decimal("10"))
        self.assertEqual(result.allocations["P102"], Decimal("10"))
        self.assertEqual(result.allocations["P103"], Decimal("10"))

    def test_allocate_shared_meter_zero_loss(self):
        """Test exact match between master and sub-meters (zero loss)."""
        readings = [
            SubMeterReading(room_id="P101", consumption=Decimal("120")),
            SubMeterReading(room_id="P102", consumption=Decimal("180")),
        ]
        result = allocate_shared_meter(
            master_consumption=Decimal("300"),
            sub_readings=readings,
        )

        self.assertEqual(result.loss_consumption, Decimal("0"))
        self.assertEqual(result.allocations["P101"], Decimal("0"))
        self.assertEqual(result.allocations["P102"], Decimal("0"))

    def test_allocate_shared_meter_master_less_than_sub_raises(self):
        """Master meter lower than sum of sub-meters must raise ValueError."""
        readings = [
            SubMeterReading(room_id="P101", consumption=Decimal("150")),
            SubMeterReading(room_id="P102", consumption=Decimal("100")),
        ]
        with self.assertRaises(ValueError):
            allocate_shared_meter(master_consumption=Decimal("200"), sub_readings=readings)

    def test_allocate_shared_meter_invalid_inputs(self):
        """Test invalid inputs: negative values, empty readings, duplicate room IDs."""
        valid_reading = SubMeterReading(room_id="P101", consumption=Decimal("50"))

        # Negative master consumption
        with self.assertRaises(ValueError):
            allocate_shared_meter(master_consumption=Decimal("-10"), sub_readings=[valid_reading])

        # Negative sub-meter consumption
        with self.assertRaises(ValueError):
            allocate_shared_meter(
                master_consumption=Decimal("100"),
                sub_readings=[SubMeterReading(room_id="P101", consumption=Decimal("-5"))],
            )

        # Empty sub_readings list
        with self.assertRaises(ValueError):
            allocate_shared_meter(master_consumption=Decimal("100"), sub_readings=[])

        # Duplicate room_id
        with self.assertRaises(ValueError):
            allocate_shared_meter(
                master_consumption=Decimal("200"),
                sub_readings=[
                    SubMeterReading(room_id="P101", consumption=Decimal("50")),
                    SubMeterReading(room_id="P101", consumption=Decimal("50")),
                ],
            )

        # Unsupported method
        with self.assertRaises(ValueError):
            allocate_shared_meter(
                master_consumption=Decimal("100"),
                sub_readings=[valid_reading],
                method="INVALID_METHOD",  # type: ignore
            )

    def test_calculate_prorated_quota_exam_example(self):
        """Exam example: 30 days, 2 tenants stay 30 days, 1 tenant stays 15 days -> 0.625 quota.

        Total person-days = 30 + 30 + 15 = 75.
        Divisor = 4 * 30 = 120.
        Effective quota = 75 / 120 = 0.625.
        """
        stays = [
            TenantStayPeriod(tenant_name="Nguyen Van A", days_stayed=30),
            TenantStayPeriod(tenant_name="Tran Thi B", days_stayed=30),
            TenantStayPeriod(tenant_name="Le Van C", days_stayed=15),
        ]
        result = calculate_prorated_quota(days_in_month=30, tenant_stays=stays)

        self.assertEqual(result.total_days_in_month, 30)
        self.assertEqual(result.effective_quota, Decimal("0.625"))
        self.assertEqual(len(result.details), 3)

        self.assertEqual(result.details[0]["tenant_name"], "Nguyen Van A")
        self.assertEqual(result.details[0]["days_stayed"], 30)
        self.assertEqual(result.details[0]["effective_quota"], Decimal("0.25"))

        self.assertEqual(result.details[1]["tenant_name"], "Tran Thi B")
        self.assertEqual(result.details[1]["days_stayed"], 30)
        self.assertEqual(result.details[1]["effective_quota"], Decimal("0.25"))

        self.assertEqual(result.details[2]["tenant_name"], "Le Van C")
        self.assertEqual(result.details[2]["days_stayed"], 15)
        self.assertEqual(result.details[2]["effective_quota"], Decimal("0.125"))

        self.assertEqual(
            sum(d["effective_quota"] for d in result.details),
            result.effective_quota,
        )

    def test_calculate_prorated_quota_tenants_mid_month_changes(self):
        """Test tenant moving out and another moving in during a 31-day month."""
        stays = [
            TenantStayPeriod(tenant_name="Tenant Leaver", days_stayed=10),
            TenantStayPeriod(tenant_name="Tenant Continuous", days_stayed=31),
            TenantStayPeriod(tenant_name="Tenant Newcomer", days_stayed=12),
        ]
        result = calculate_prorated_quota(days_in_month=31, tenant_stays=stays)

        # Total person-days = 10 + 31 + 12 = 53
        # Divisor = 4 * 31 = 124
        expected_quota = Decimal("53") / Decimal("124")
        self.assertEqual(result.effective_quota, expected_quota)
        self.assertEqual(result.total_days_in_month, 31)
        self.assertEqual(len(result.details), 3)

    def test_calculate_prorated_quota_full_month_tenants(self):
        """4 tenants staying all 30 days must yield exactly 1.00 quota."""
        stays = [
            TenantStayPeriod(tenant_name="T1", days_stayed=30),
            TenantStayPeriod(tenant_name="T2", days_stayed=30),
            TenantStayPeriod(tenant_name="T3", days_stayed=30),
            TenantStayPeriod(tenant_name="T4", days_stayed=30),
        ]
        result = calculate_prorated_quota(days_in_month=30, tenant_stays=stays)
        self.assertEqual(result.effective_quota, Decimal("1.0"))

    def test_calculate_prorated_quota_empty_tenants(self):
        """No tenants in room yields 0 quota."""
        result = calculate_prorated_quota(days_in_month=30, tenant_stays=[])
        self.assertEqual(result.effective_quota, Decimal("0"))
        self.assertEqual(result.details, [])

    def test_calculate_prorated_quota_invalid_inputs(self):
        """Test invalid inputs for days_in_month and days_stayed."""
        # Zero or negative days_in_month
        with self.assertRaises(ValueError):
            calculate_prorated_quota(days_in_month=0, tenant_stays=[])
        with self.assertRaises(ValueError):
            calculate_prorated_quota(days_in_month=-5, tenant_stays=[])

        # Negative days_stayed via TenantStayPeriod
        with self.assertRaises(ValueError):
            TenantStayPeriod(tenant_name="Invalid", days_stayed=-1)

        # Days stayed exceeding days in month
        with self.assertRaises(ValueError):
            calculate_prorated_quota(
                days_in_month=30,
                tenant_stays=[TenantStayPeriod(tenant_name="Overstayer", days_stayed=31)],
            )

    def test_prorated_quota_integrated_with_tiered_electricity(self):
        """Integration test: prorated quota (0.625) applied to tiered electricity calculation.

        Quota = 0.625. Consumption = 100 kWh.
        Tier 1 threshold: 50 * 0.625 = 31.25 kWh -> 31.25 * 1984 = 62.000
        Tier 2 threshold: 50 * 0.625 = 31.25 kWh -> 31.25 * 2050 = 64.062,50
        Tier 3: remaining 37.5 kWh -> 37.5 * 2380 = 89.250
        Pre-tax: 62.000 + 64.062,50 + 89.250 = 215.312,50
        VAT (8%): 17.225,00
        Total: 232.537,50 -> rounds half-up to 232.538 VND.
        """
        stays = [
            TenantStayPeriod(tenant_name="A", days_stayed=30),
            TenantStayPeriod(tenant_name="B", days_stayed=30),
            TenantStayPeriod(tenant_name="C", days_stayed=15),
        ]
        quota_res = calculate_prorated_quota(days_in_month=30, tenant_stays=stays)
        self.assertEqual(quota_res.effective_quota, Decimal("0.625"))

        elec_res = calculate_electricity_tiered(consumption=100, quota=quota_res.effective_quota)
        self.assertEqual(elec_res.pre_tax_amount, Decimal("215312.50"))
        self.assertEqual(elec_res.vat_amount, Decimal("17225.00"))
        self.assertEqual(elec_res.total_amount, Decimal("232538"))
        self.assertEqual(len(elec_res.breakdown), 3)

    def test_allocate_shared_meter_exact_fraction_precision(self):
        """Test multiplication before division preserves exact decimal integer fractions."""
        readings = [
            SubMeterReading(room_id="P1", consumption=Decimal("10")),
            SubMeterReading(room_id="P2", consumption=Decimal("20")),
        ]
        result = allocate_shared_meter(
            master_consumption=Decimal("60"),
            sub_readings=readings,
            method=LossAllocationMethod.PROPORTIONAL,
        )
        self.assertEqual(result.loss_consumption, Decimal("30"))
        self.assertEqual(result.allocations["P1"], Decimal("10"))
        self.assertEqual(result.allocations["P2"], Decimal("20"))
        self.assertEqual(sum(result.allocations.values()), Decimal("30"))

    def test_allocate_shared_meter_method_case_insensitive(self):
        """Test string method names are accepted case-insensitively."""
        readings = [SubMeterReading(room_id="P1", consumption=Decimal("100"))]
        res1 = allocate_shared_meter(Decimal("120"), readings, method="proportional")  # type: ignore
        self.assertEqual(res1.allocations["P1"], Decimal("20"))

        res2 = allocate_shared_meter(Decimal("120"), readings, method="equal")  # type: ignore
        self.assertEqual(res2.allocations["P1"], Decimal("20"))

    def test_allocate_shared_meter_whitespace_room_id_duplicate(self):
        """Room IDs with whitespace differences should be trimmed and flagged as duplicates."""
        with self.assertRaises(ValueError):
            allocate_shared_meter(
                master_consumption=Decimal("200"),
                sub_readings=[
                    SubMeterReading(room_id="P101", consumption=Decimal("50")),
                    SubMeterReading(room_id=" P101 ", consumption=Decimal("50")),
                ],
            )

    def test_sub_meter_reading_invalid_inputs(self):
        """SubMeterReading must reject empty room_id and negative consumption."""
        with self.assertRaises(ValueError):
            SubMeterReading(room_id="", consumption=Decimal("50"))
        with self.assertRaises(ValueError):
            SubMeterReading(room_id="   ", consumption=Decimal("50"))
        with self.assertRaises(ValueError):
            SubMeterReading(room_id="P101", consumption=Decimal("-10"))

    def test_tenant_stay_period_validation(self):
        """TenantStayPeriod must validate name and days_stayed types/values."""
        # Empty tenant_name
        with self.assertRaises(ValueError):
            TenantStayPeriod(tenant_name="", days_stayed=10)
        with self.assertRaises(ValueError):
            TenantStayPeriod(tenant_name="   ", days_stayed=10)

        # Boolean days_stayed rejected
        with self.assertRaises(TypeError):
            TenantStayPeriod(tenant_name="A", days_stayed=True)  # type: ignore

        # Float non-integer days_stayed rejected
        with self.assertRaises(ValueError):
            TenantStayPeriod(tenant_name="A", days_stayed=15.5)  # type: ignore

        # String integer coercion works
        t = TenantStayPeriod(tenant_name=" A ", days_stayed="25")  # type: ignore
        self.assertEqual(t.days_stayed, 25)
        self.assertEqual(t.tenant_name, "A")

    def test_calculate_prorated_quota_cumulative_days_exceeded(self):
        """Cumulative days stayed for the same tenant across split periods cannot exceed month."""
        stays = [
            TenantStayPeriod(tenant_name="A", days_stayed=20),
            TenantStayPeriod(tenant_name="A", days_stayed=15),
        ]
        with self.assertRaises(ValueError):
            calculate_prorated_quota(days_in_month=30, tenant_stays=stays)

    def test_calculate_prorated_quota_split_stays_valid(self):
        """Cumulative days stayed within month limits for same tenant are valid."""
        stays = [
            TenantStayPeriod(tenant_name="A", days_stayed=10),
            TenantStayPeriod(tenant_name="A", days_stayed=15),
        ]
        res = calculate_prorated_quota(days_in_month=30, tenant_stays=stays)
        # Total person-days = 25 / (4 * 30) = 25 / 120
        self.assertEqual(res.effective_quota, Decimal("25") / Decimal("120"))
        self.assertEqual(len(res.details), 2)

    def test_calculate_prorated_quota_days_in_month_types(self):
        """days_in_month must be integer, not boolean or string."""
        with self.assertRaises(TypeError):
            calculate_prorated_quota(days_in_month=True, tenant_stays=[])  # type: ignore
        with self.assertRaises(TypeError):
            calculate_prorated_quota(days_in_month="30", tenant_stays=[])  # type: ignore


if __name__ == "__main__":
    unittest.main()
