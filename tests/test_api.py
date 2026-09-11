# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Comprehensive end-to-end unit and integration tests for tro. RESTful API ecosystem."""

from decimal import Decimal
import os
import tempfile
import unittest
from typing import Dict, Tuple

from backend.app.auth import register
from backend.app.compat import Session, TestClient, create_engine, select
from backend.app.database import init_db
from backend.app.main import app
from backend.app.models import Invoice, MeterReading, Property, Room, SystemConfig, User
from backend.app.schemas import (
    InvoiceCalculateRequest,
    PropertyCreate,
    RoomCreate,
    SystemConfigUpdate,
    UserRegister,
)
from backend.app.security import create_access_token
from core.calculator import (
    calculate_consumption,
    calculate_dispute,
    calculate_electricity_tier3,
    calculate_electricity_tiered,
    calculate_quota,
    calculate_water,
)


class TestTroApiEndpoints(unittest.TestCase):
    """Integration test suite covering properties, rooms, readings, invoices, and dynamic config."""

    def setUp(self) -> None:
        """Create an isolated temporary SQLite database for each test case."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_tro.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Clean up temporary test artifacts."""
        self.temp_dir.cleanup()

    def _create_user(
        self,
        session: Session,
        username: str,
        role: str = "landlord",
        invite_code: str = None,
    ) -> Tuple[User, str]:
        """Helper to create and authenticate a user, returning the entity and JWT token."""
        user_reg = UserRegister(
            username=username,
            password="testPassword123!",
            full_name=f"Full {username}",
            phone="0901234567",
            role=role,
            invite_code=invite_code,
        )
        registered = register(user_reg, session=session)
        token = create_access_token(
            {"sub": registered.username, "user_id": registered.id, "role": registered.role}
        )
        return session.get(User, registered.id), token

    def _auth_headers(self, token: str) -> Dict[str, str]:
        """Helper to generate standard Bearer authorization headers."""
        return {"Authorization": f"Bearer {token}"}

    # ========================================================================
    # 1. Health Check Endpoint
    # ========================================================================

    def test_health_check_endpoint(self) -> None:
        """GET /health must return status healthy and app tro.."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("app"), "tro.")

    # ========================================================================
    # 2. Properties (Khu trọ) CRUD & Authorization
    # ========================================================================

    def test_properties_crud_and_landlord_isolation(self) -> None:
        """Test creating, listing, and retrieving properties with landlord isolation."""
        with Session(self.engine) as session:
            landlord1, token1 = self._create_user(session, "landlord_alpha", role="landlord")
            landlord2, token2 = self._create_user(session, "landlord_beta", role="landlord")
            tenant, tenant_token = self._create_user(session, "tenant_charlie", role="tenant")

            # 1. Landlord 1 creates a property
            create_resp = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Binh Thanh", "address": "123 Dien Bien Phu, TP.HCM"},
                headers=self._auth_headers(token1),
                session=session,
            )
            self.assertEqual(create_resp.status_code, 201)
            prop1_data = create_resp.json()
            self.assertEqual(prop1_data["name"], "Khu Tro Binh Thanh")
            self.assertEqual(prop1_data["landlord_id"], landlord1.id)
            prop1_id = prop1_data["id"]

            # 2. Tenant forbidden from creating property (HTTP 403)
            tenant_resp = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Illicit", "address": "Forbidden Street"},
                headers=self._auth_headers(tenant_token),
                session=session,
            )
            self.assertEqual(tenant_resp.status_code, 403)

            # 3. Unauthenticated request rejected (HTTP 401)
            unauth_resp = self.client.post(
                "/api/v1/properties",
                json={"name": "Anonymous Prop"},
                session=session,
            )
            self.assertEqual(unauth_resp.status_code, 401)

            # 4. Landlord 2 creates their own property
            self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Quan 1", "address": "456 Le Loi, TP.HCM"},
                headers=self._auth_headers(token2),
                session=session,
            )

            # 5. Landlord 1 lists properties -> sees only their own property
            list_resp1 = self.client.get(
                "/api/v1/properties",
                headers=self._auth_headers(token1),
                session=session,
            )
            self.assertEqual(list_resp1.status_code, 200)
            props1 = list_resp1.json()
            self.assertEqual(len(props1), 1)
            self.assertEqual(props1[0]["name"], "Khu Tro Binh Thanh")

            # 6. Landlord 1 gets specific property
            get_resp = self.client.get(
                f"/api/v1/properties/{prop1_id}",
                headers=self._auth_headers(token1),
                session=session,
            )
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(get_resp.json()["id"], prop1_id)

            # 7. Landlord 2 forbidden from accessing Landlord 1's property (HTTP 403)
            cross_resp = self.client.get(
                f"/api/v1/properties/{prop1_id}",
                headers=self._auth_headers(token2),
                session=session,
            )
            self.assertEqual(cross_resp.status_code, 403)

            # 8. Non-existent property returns HTTP 404
            not_found_resp = self.client.get(
                "/api/v1/properties/999999",
                headers=self._auth_headers(token1),
                session=session,
            )
            self.assertEqual(not_found_resp.status_code, 404)

    # ========================================================================
    # 3. Rooms (Phòng trọ) CRUD & RBAC
    # ========================================================================

    def test_rooms_crud_and_rbac(self) -> None:
        """Test room creation within property, invite code generation, and access control."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_dan", role="landlord")
            other_landlord, other_token = self._create_user(session, "host_other", role="landlord")
            tenant, t_token = self._create_user(session, "renter_eva", role="tenant")

            # Create property
            p_resp = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Nha Tro Dan", "address": "100 Nguyen Hue"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_resp.json()["id"]

            # 1. Landlord creates room in property
            r_resp = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "101", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(r_resp.status_code, 201)
            room_data = r_resp.json()
            room_id = room_data["id"]
            self.assertEqual(room_data["room_number"], "101")
            self.assertEqual(room_data["property_id"], prop_id)
            self.assertEqual(room_data["status"], "empty")
            self.assertIsNotNone(room_data["invite_code"])
            self.assertEqual(len(room_data["invite_code"]), 8)

            # 2. Tenant forbidden from creating room (HTTP 403)
            tenant_r_resp = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "102"},
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(tenant_r_resp.status_code, 403)

            # 3. Other landlord forbidden from creating room in someone else's property (HTTP 403)
            cross_r_resp = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "102"},
                headers=self._auth_headers(other_token),
                session=session,
            )
            self.assertEqual(cross_r_resp.status_code, 403)

            # 4. Duplicate room number in same property rejected (HTTP 400)
            dup_resp = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "101"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(dup_resp.status_code, 400)

            # 5. List rooms in property
            list_rooms_resp = self.client.get(
                f"/api/v1/properties/{prop_id}/rooms",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(list_rooms_resp.status_code, 200)
            self.assertEqual(len(list_rooms_resp.json()), 1)

            # 6. Retrieve single room by id
            get_room_resp = self.client.get(
                f"/api/v1/rooms/{room_id}",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(get_room_resp.status_code, 200)
            self.assertEqual(get_room_resp.json()["room_number"], "101")

            # 7. Unassigned tenant accessing room -> HTTP 403
            unassigned_resp = self.client.get(
                f"/api/v1/rooms/{room_id}",
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(unassigned_resp.status_code, 403)

            # 8. Non-existent room -> HTTP 404
            missing_room = self.client.get(
                "/api/v1/rooms/999999",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(missing_room.status_code, 404)

    # ========================================================================
    # 4. Meter Readings Recording & Listing
    # ========================================================================

    def test_meter_readings_workflow(self) -> None:
        """Test recording monthly meter readings, handling rollovers, and read queries."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_frank", role="landlord")
            tenant, t_token = self._create_user(session, "tenant_grace", role="tenant")

            # Create property and room
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Frank"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "201", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # 1. Landlord records regular meter reading
            read_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/readings",
                json={
                    "month_year": "2026-09",
                    "elec_start": 100.0,
                    "elec_end": 220.0,
                    "water_start": 10.0,
                    "water_end": 22.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(read_resp.status_code, 201)
            read_data = read_resp.json()
            self.assertEqual(read_data["month_year"], "2026-09")
            self.assertEqual(read_data["elec_start"], 100.0)
            self.assertEqual(read_data["elec_end"], 220.0)

            # 2. Tenant cannot record reading (HTTP 403)
            tenant_read_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/readings",
                json={"month_year": "2026-10", "elec_start": 220.0, "elec_end": 300.0},
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(tenant_read_resp.status_code, 403)

            # 3. List readings for room
            list_resp = self.client.get(
                f"/api/v1/rooms/{room_id}/readings",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(list_resp.status_code, 200)
            self.assertEqual(len(list_resp.json()), 1)

    # ========================================================================
    # 5. Invoicing Workflow & Core Calculator Mathematical Precision
    # ========================================================================

    def test_invoice_calculation_and_core_engine_parity(self) -> None:
        """Test invoice generation parity with core calculator: tiered electricity, water, dispute."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_helen", role="landlord")

            # Create property and room (4 people registered = 1 quota)
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Helen"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "301", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Pre-calculate expected results using pure Core Calculator:
            # 120 kWh, 1 quota (4 people / 4 = 1.0)
            # Tier 1: 50 kWh @ 1984 = 99.200
            # Tier 2: 50 kWh @ 2050 = 102.500
            # Tier 3: 20 kWh @ 2380 = 47.600
            # Pre-tax elec = 249.300, 8% VAT = 19.944, Total elec = 269.244
            # Water 12 m3 @ 8500 = 102.000 pre-tax, 5% VAT = 5.100, 10% env fee = 10.200, Total water = 117.300
            # Total statutory = 269.244 + 117.300 = 386.544
            # Actual collected = 450.000
            # Overcharge dispute diff = 450.000 - 386.544 = +63.456
            expected_elec = calculate_electricity_tiered(120, quota=calculate_quota(4))
            expected_water = calculate_water(12)
            expected_total = expected_elec.total_amount + expected_water.total_amount
            expected_dispute = calculate_dispute(expected_total, 450000)

            # Generate invoice via API
            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 100.0,
                    "elec_end": 220.0,
                    "water_start": 10.0,
                    "water_end": 22.0,
                    "actual_collected": 450000.0,
                    "has_registered_quota": True,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_resp.status_code, 201)
            inv_data = calc_resp.json()

            # Verify statutory figures match core engine down to the single đồng
            self.assertEqual(Decimal(str(inv_data["elec_kwh"])), Decimal("120"))
            self.assertEqual(Decimal(str(inv_data["elec_amount"])), expected_elec.total_amount)
            self.assertEqual(Decimal(str(inv_data["water_usage"])), Decimal("12"))
            self.assertEqual(Decimal(str(inv_data["water_amount"])), expected_water.total_amount)
            self.assertEqual(Decimal(str(inv_data["total_statutory_amount"])), expected_total)
            self.assertEqual(Decimal(str(inv_data["actual_collected_amount"])), Decimal("450000"))
            self.assertEqual(Decimal(str(inv_data["diff_amount"])), expected_dispute.diff_amount)
            self.assertTrue(inv_data["diff_amount"] > 0)  # Landlord overcharged

            # Verify breakdown JSON structure
            breakdown = inv_data.get("breakdown")
            self.assertIsNotNone(breakdown)
            self.assertEqual(breakdown["electricity"]["method"], "TIERED")
            self.assertEqual(len(breakdown["electricity"]["tiers"]), 3)
            self.assertEqual(breakdown["dispute"]["is_overcharged"], True)

            # Verify invoice listing and detail retrieval
            inv_id = inv_data["id"]
            list_inv = self.client.get(
                f"/api/v1/rooms/{room_id}/invoices",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(list_inv.status_code, 200)
            self.assertEqual(len(list_inv.json()), 1)

            get_inv = self.client.get(
                f"/api/v1/invoices/{inv_id}",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(get_inv.status_code, 200)
            self.assertEqual(get_inv.json()["id"], inv_id)

    def test_invoice_calculation_undeclared_tenants_uses_flat_tier3(self) -> None:
        """When tenants are undeclared, invoice must fall back to flat Tier 3 per TT 60/2025."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_ian", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Ian"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "302", "current_people_count": 0},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Calculate with has_registered_quota=False (Tier 3 flat calculation)
            # 120 kWh @ 2380 đ/kWh = 285.600 đ; 8% VAT = 22.848 đ; Total = 308.448 đ
            expected_tier3 = calculate_electricity_tier3(120)

            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 1000.0,
                    "elec_end": 1120.0,
                    "water_start": 0.0,
                    "water_end": 5.0,
                    "has_registered_quota": False,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_resp.status_code, 201)
            inv_data = calc_resp.json()
            self.assertEqual(Decimal(str(inv_data["elec_amount"])), expected_tier3.total_amount)
            self.assertEqual(inv_data["breakdown"]["electricity"]["method"], "TIER_3")

    def test_invoice_calculation_with_meter_rollover(self) -> None:
        """Invoice calculation handles meter rollover (e.g. 99850 to 120 kWh on 5-digit meter)."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_jack", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Jack"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "401", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Rollover: 99850 -> 120 = 270 kWh consumption
            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 99850.0,
                    "elec_end": 120.0,
                    "water_start": 99995.0,
                    "water_end": 15.0,
                    "max_meter": 99999.0,
                    "has_registered_quota": True,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_resp.status_code, 201)
            inv_data = calc_resp.json()
            self.assertEqual(Decimal(str(inv_data["elec_kwh"])), Decimal("270"))
            self.assertEqual(Decimal(str(inv_data["water_usage"])), Decimal("20"))

    # ========================================================================
    # 6. Feature 17: Public Invoice Lookup (No Authentication Required)
    # ========================================================================

    def test_public_invoice_lookup_by_share_token_without_auth(self) -> None:
        """Feature 17: Unauthenticated users can inspect full invoice and breakdown via share_token."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_public", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Public"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "501", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Create an invoice
            create_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 50.0,
                    "elec_end": 150.0,
                    "water_start": 0.0,
                    "water_end": 10.0,
                    "actual_collected": 350000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(create_resp.status_code, 201)
            share_token = create_resp.json()["share_token"]
            self.assertTrue(len(share_token) > 10)

            # Public query WITHOUT Authorization header
            public_resp = self.client.get(
                f"/api/v1/invoices/public/{share_token}",
                session=session,
            )
            self.assertEqual(public_resp.status_code, 200)
            pub_data = public_resp.json()

            # Verify public data integrity
            self.assertEqual(pub_data["share_token"], share_token)
            self.assertEqual(Decimal(str(pub_data["elec_kwh"])), Decimal("100"))
            self.assertIsNotNone(pub_data.get("breakdown"))
            self.assertIn("electricity", pub_data["breakdown"])
            self.assertIn("water", pub_data["breakdown"])
            self.assertIn("dispute", pub_data["breakdown"])

            # Invalid share token returns HTTP 404
            invalid_resp = self.client.get(
                "/api/v1/invoices/public/non-existent-token-xyz",
                session=session,
            )
            self.assertEqual(invalid_resp.status_code, 404)

    # ========================================================================
    # 7. Dynamic Pricing Configuration (/config) & Hot-Reload Parity
    # ========================================================================

    def test_dynamic_config_update_applies_immediately_to_new_invoices(self) -> None:
        """Modifying tariffs via PUT /config dynamically updates calculation for subsequent invoices."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_dynamic", role="landlord")
            tenant, t_token = self._create_user(session, "tenant_dynamic", role="tenant")

            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Dynamic"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "601", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # 1. View default pricing configuration
            cfg_get = self.client.get(
                "/api/v1/config",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(cfg_get.status_code, 200)
            self.assertAlmostEqual(cfg_get.json()["electricity_vat_rate"], 0.08)
            self.assertEqual(len(cfg_get.json()["tiers"]), 6)

            # 2. Tenant cannot modify pricing config (HTTP 403)
            tenant_put = self.client.put(
                "/api/v1/config",
                json={"electricity_vat_rate": 0.10},
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(tenant_put.status_code, 403)

            # 3. Baseline invoice with default config (8% VAT, 8.500 VND water)
            inv1 = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-08",
                    "elec_start": 0.0,
                    "elec_end": 100.0,
                    "water_start": 0.0,
                    "water_end": 10.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(inv1.status_code, 201)
            inv1_elec_amount = inv1.json()["elec_amount"]

            # 4. Landlord updates VAT to 10% and Tier 3 price to 3.000 VND
            update_resp = self.client.put(
                "/api/v1/config",
                json={
                    "electricity_vat_rate": 0.10,
                    "electricity_tier3_price": 3000.0,
                    "water_unit_price": 12000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(update_resp.status_code, 200)
            self.assertAlmostEqual(update_resp.json()["electricity_vat_rate"], 0.10)
            self.assertAlmostEqual(update_resp.json()["water_unit_price"], 12000.0)

            # 5. Subsequent invoice generated immediately reflects the updated tariffs
            inv2 = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 100.0,
                    "elec_end": 200.0,
                    "water_start": 10.0,
                    "water_end": 20.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(inv2.status_code, 201)
            inv2_elec_amount = inv2.json()["elec_amount"]

            # 10% VAT must result in higher electricity cost than 8% VAT for same 100 kWh
            self.assertGreater(inv2_elec_amount, inv1_elec_amount)
            self.assertEqual(inv2.json()["breakdown"]["water"]["unit_price"], 12000.0)

    def test_tenant_access_to_own_room_and_invoices(self) -> None:
        """Tenant assigned to room can view room details, readings, and invoices; unrelated tenant forbidden."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "landlord_rent", role="landlord")

            # Create property and room
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Nha Tro Cho Thue"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "701", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]
            invite_code = r_res.json()["invite_code"]

            # Tenant 1 registers with the room's invite code -> auto assigned
            tenant1, t1_token = self._create_user(
                session, "tenant_assigned", role="tenant", invite_code=invite_code
            )

            # Tenant 2 is unrelated
            tenant2, t2_token = self._create_user(session, "tenant_stranger", role="tenant")

            # Record reading and generate invoice
            self.client.post(
                f"/api/v1/rooms/{room_id}/readings",
                json={
                    "month_year": "2026-09",
                    "elec_start": 0.0,
                    "elec_end": 50.0,
                    "water_start": 0.0,
                    "water_end": 5.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            inv_res = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={"month_year": "2026-09"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            invoice_id = inv_res.json()["id"]

            # 1. Assigned tenant can access room, readings, and invoices
            t1_room = self.client.get(
                f"/api/v1/rooms/{room_id}",
                headers=self._auth_headers(t1_token),
                session=session,
            )
            self.assertEqual(t1_room.status_code, 200)

            t1_readings = self.client.get(
                f"/api/v1/rooms/{room_id}/readings",
                headers=self._auth_headers(t1_token),
                session=session,
            )
            self.assertEqual(t1_readings.status_code, 200)
            self.assertEqual(len(t1_readings.json()), 1)

            t1_invs = self.client.get(
                f"/api/v1/rooms/{room_id}/invoices",
                headers=self._auth_headers(t1_token),
                session=session,
            )
            self.assertEqual(t1_invs.status_code, 200)
            self.assertEqual(len(t1_invs.json()), 1)

            t1_single_inv = self.client.get(
                f"/api/v1/invoices/{invoice_id}",
                headers=self._auth_headers(t1_token),
                session=session,
            )
            self.assertEqual(t1_single_inv.status_code, 200)

            # 2. Unrelated tenant receives HTTP 403 on all of them
            self.assertEqual(
                self.client.get(
                    f"/api/v1/rooms/{room_id}",
                    headers=self._auth_headers(t2_token),
                    session=session,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/rooms/{room_id}/readings",
                    headers=self._auth_headers(t2_token),
                    session=session,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/rooms/{room_id}/invoices",
                    headers=self._auth_headers(t2_token),
                    session=session,
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/v1/invoices/{invoice_id}",
                    headers=self._auth_headers(t2_token),
                    session=session,
                ).status_code,
                403,
            )

    def test_invoice_calculation_with_pre_existing_reading_and_undercharge(self) -> None:
        """Invoice calculation from pre-saved reading and negative dispute diff when undercharged."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_undercharge", role="landlord")

            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Undercharge"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "801", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Save meter reading first
            read_res = self.client.post(
                f"/api/v1/rooms/{room_id}/readings",
                json={
                    "month_year": "2026-11",
                    "elec_start": 200.0,
                    "elec_end": 280.0,
                    "water_start": 50.0,
                    "water_end": 58.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(read_res.status_code, 201)

            # Landlord collects only 150.000 VND (less than statutory bill)
            calc_res = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-11",
                    "actual_collected": 150000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_res.status_code, 201)
            inv = calc_res.json()
            self.assertEqual(inv["elec_kwh"], 80.0)
            self.assertEqual(inv["water_usage"], 8.0)
            # Undercharged dispute: diff_amount < 0 and is_overcharged is False
            self.assertLess(inv["diff_amount"], 0)
            self.assertFalse(inv["breakdown"]["dispute"]["is_overcharged"])

    def test_invoice_with_water_per_person_pricing(self) -> None:
        """Water calculation configured with PER_PERSON uses room occupants count."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_water_person", role="landlord")

            # Update water configuration to PER_PERSON @ 80.000 VND / person
            self.client.put(
                "/api/v1/config",
                json={
                    "water_pricing_type": "PER_PERSON",
                    "water_unit_price": 80000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )

            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Water Person"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            # 3 people in room
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "901", "current_people_count": 3},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            calc_res = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-12",
                    "elec_start": 0.0,
                    "elec_end": 50.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_res.status_code, 201)
            inv = calc_res.json()
            # Water usage = 3 persons
            self.assertEqual(inv["water_usage"], 3.0)
            # 3 * 80.000 = 240.000 pre-tax; 5% VAT = 12.000; 10% env = 24.000 -> Total = 276.000
            self.assertEqual(inv["water_amount"], 276000.0)

    # ========================================================================
    # 8. Advanced Edge Cases: reading_id Validation, Cross-Isolation & Inputs
    # ========================================================================

    def test_invoice_calculation_with_reading_id_and_validation(self) -> None:
        """Verify reading_id resolution, cross-room mismatch rejection, and missing readings handling."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_reading_id", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Reading Test"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r1_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "R1", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room1_id = r1_res.json()["id"]

            r2_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "R2", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room2_id = r2_res.json()["id"]

            # Record reading for room 1
            read1 = self.client.post(
                f"/api/v1/rooms/{room1_id}/readings",
                json={
                    "month_year": "2026-05",
                    "elec_start": 100.0,
                    "elec_end": 180.0,
                    "water_start": 10.0,
                    "water_end": 18.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(read1.status_code, 201)
            reading1_id = read1.json()["id"]

            # Record reading for room 2
            read2 = self.client.post(
                f"/api/v1/rooms/{room2_id}/readings",
                json={
                    "month_year": "2026-05",
                    "elec_start": 500.0,
                    "elec_end": 600.0,
                    "water_start": 50.0,
                    "water_end": 60.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(read2.status_code, 201)
            reading2_id = read2.json()["id"]

            # 1. Successful calculation using valid reading_id
            calc_ok = self.client.post(
                f"/api/v1/rooms/{room1_id}/invoices/calculate",
                json={
                    "month_year": "2026-05",
                    "reading_id": reading1_id,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_ok.status_code, 201)
            self.assertEqual(calc_ok.json()["elec_kwh"], 80.0)
            self.assertEqual(calc_ok.json()["water_usage"], 8.0)

            # 2. Non-existent reading_id returns 404
            calc_not_found = self.client.post(
                f"/api/v1/rooms/{room1_id}/invoices/calculate",
                json={
                    "month_year": "2026-05",
                    "reading_id": 999999,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_not_found.status_code, 404)

            # 3. Reading belonging to a different room returns 400
            calc_mismatch = self.client.post(
                f"/api/v1/rooms/{room1_id}/invoices/calculate",
                json={
                    "month_year": "2026-05",
                    "reading_id": reading2_id,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_mismatch.status_code, 400)
            self.assertIn("does not belong to room", calc_mismatch.json()["detail"])

            # 4. Calculation without readings in request when no reading exists for month returns 400
            calc_missing = self.client.post(
                f"/api/v1/rooms/{room1_id}/invoices/calculate",
                json={"month_year": "2026-06"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_missing.status_code, 400)
            self.assertIn("No meter reading found", calc_missing.json()["detail"])

    def test_invalid_meter_readings_and_rollover_parameters(self) -> None:
        """Negative readings, max_meter <= 0, and bad inputs must be rejected gracefully with 400/422."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_invalid_input", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Invalid Input"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]
            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "Bad01", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # 1. Negative readings in calculation request
            neg_elec = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-07",
                    "elec_start": -10.0,
                    "elec_end": 50.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(neg_elec.status_code, [400, 422])

            # 2. max_meter <= 0
            bad_max = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-07",
                    "elec_start": 10.0,
                    "elec_end": 50.0,
                    "max_meter": 0.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(bad_max.status_code, [400, 422])

            # 3. Empty month_year
            empty_month = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "   ",
                    "elec_start": 10.0,
                    "elec_end": 50.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(empty_month.status_code, [400, 422])

    def test_cross_landlord_isolation_across_readings_and_invoices(self) -> None:
        """Landlord B is strictly prohibited from recording readings, calculating, or reading invoices for Landlord A's rooms."""
        with Session(self.engine) as session:
            landlord_a, token_a = self._create_user(session, "landlord_owner_a", role="landlord")
            landlord_b, token_b = self._create_user(session, "landlord_intruder_b", role="landlord")

            # Landlord A sets up property and room
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Landlord A"},
                headers=self._auth_headers(token_a),
                session=session,
            )
            prop_a_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_a_id}/rooms",
                json={"room_number": "A101", "current_people_count": 3},
                headers=self._auth_headers(token_a),
                session=session,
            )
            room_a_id = r_res.json()["id"]

            # 1. Landlord B cannot record meter readings for Landlord A's room (HTTP 403)
            rec_b = self.client.post(
                f"/api/v1/rooms/{room_a_id}/readings",
                json={
                    "month_year": "2026-08",
                    "elec_start": 0.0,
                    "elec_end": 100.0,
                },
                headers=self._auth_headers(token_b),
                session=session,
            )
            self.assertEqual(rec_b.status_code, 403)

            # Landlord A records reading
            self.client.post(
                f"/api/v1/rooms/{room_a_id}/readings",
                json={
                    "month_year": "2026-08",
                    "elec_start": 0.0,
                    "elec_end": 100.0,
                    "water_start": 0.0,
                    "water_end": 10.0,
                },
                headers=self._auth_headers(token_a),
                session=session,
            )

            # 2. Landlord B cannot calculate invoice for Landlord A's room (HTTP 403)
            calc_b = self.client.post(
                f"/api/v1/rooms/{room_a_id}/invoices/calculate",
                json={"month_year": "2026-08"},
                headers=self._auth_headers(token_b),
                session=session,
            )
            self.assertEqual(calc_b.status_code, 403)

            # Landlord A calculates invoice
            inv_a = self.client.post(
                f"/api/v1/rooms/{room_a_id}/invoices/calculate",
                json={"month_year": "2026-08"},
                headers=self._auth_headers(token_a),
                session=session,
            )
            self.assertEqual(inv_a.status_code, 201)
            invoice_a_id = inv_a.json()["id"]

            # 3. Landlord B cannot list invoices for Landlord A's room (HTTP 403)
            list_inv_b = self.client.get(
                f"/api/v1/rooms/{room_a_id}/invoices",
                headers=self._auth_headers(token_b),
                session=session,
            )
            self.assertEqual(list_inv_b.status_code, 403)

            # 4. Landlord B cannot get Landlord A's invoice directly (HTTP 403)
            get_inv_b = self.client.get(
                f"/api/v1/invoices/{invoice_a_id}",
                headers=self._auth_headers(token_b),
                session=session,
            )
            self.assertEqual(get_inv_b.status_code, 403)

    def test_property_and_room_whitespace_validation(self) -> None:
        """Whitespace-only property names and room numbers must be rejected with HTTP 400 or 422."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_whitespace", role="landlord")

            # Whitespace property name rejected
            prop_bad = self.client.post(
                "/api/v1/properties",
                json={"name": "   ", "address": "Valid Address"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(prop_bad.status_code, [400, 422])

            # Create valid property
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Valid Property"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            # Whitespace room number rejected
            room_bad = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "   "},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(room_bad.status_code, [400, 422])

    def test_public_share_token_edge_cases_and_breakdown_metadata(self) -> None:
        """Public invoice lookup returns room and property metadata, and rejects whitespace tokens."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_pub_meta", role="landlord")
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Nha Tro Minh Bach", "address": "123 Xuan Thuy"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "VIP-01", "current_people_count": 4},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            inv_res = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 0.0,
                    "elec_end": 100.0,
                    "water_start": 0.0,
                    "water_end": 10.0,
                    "actual_collected": 300000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(inv_res.status_code, 201)
            token = inv_res.json()["share_token"]

            # Public unauthenticated lookup
            pub_res = self.client.get(f"/api/v1/invoices/public/{token}", session=session)
            self.assertEqual(pub_res.status_code, 200)
            data = pub_res.json()

            # Breakdown has room and property metadata
            self.assertEqual(data["room_number"], "VIP-01")
            self.assertEqual(data["property_name"], "Nha Tro Minh Bach")
            self.assertEqual(data["breakdown"]["room_number"], "VIP-01")
            self.assertEqual(data["breakdown"]["property_name"], "Nha Tro Minh Bach")

            # Empty / whitespace token returns 404
            empty_token_res = self.client.get("/api/v1/invoices/public/%20%20", session=session)
            self.assertEqual(empty_token_res.status_code, 404)

    def test_dynamic_config_validation_rules(self) -> None:
        """PUT /config rejects invalid water_pricing_type, empty tiers, or malformed tier items."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_cfg_val", role="landlord")

            # 1. Invalid water pricing type
            bad_water = self.client.put(
                "/api/v1/config",
                json={"water_pricing_type": "PER_LITER"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(bad_water.status_code, [400, 422])

            # 2. Empty tiers list
            empty_tiers = self.client.put(
                "/api/v1/config",
                json={"tiers": []},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(empty_tiers.status_code, [400, 422])

            # 3. Malformed tier (missing unit_price)
            bad_tier = self.client.put(
                "/api/v1/config",
                json={"tiers": [{"tier_number": 1, "max_threshold": 50.0}]},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(bad_tier.status_code, [400, 422])

            # 4. Tier with negative unit_price
            neg_price = self.client.put(
                "/api/v1/config",
                json={"tiers": [{"tier_number": 1, "unit_price": -500.0}]},
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertIn(neg_price.status_code, [400, 422])


if __name__ == "__main__":
    unittest.main()


