# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Unit and integration tests for new features in tro.:
- Duplicate username Vietnamese error message & test assertion preservation
- In-memory sliding-window rate limiting (HTTP 429)
- Property-level tariff configuration & PUT /properties/{id}
- Invoice Draft/Publish workflow (POST /invoices/{id}/publish)
- Public lookup by short code (HD-XXXX)
- User notifications endpoint (GET /notifications)
"""

from decimal import Decimal
import os
import tempfile
import unittest
from typing import Dict, Tuple

from backend.app.auth import (
    check_rate_limit,
    register,
    reset_rate_limits,
)
from backend.app.compat import (
    HTTPException,
    Session,
    TestClient,
    create_engine,
    select,
)
from backend.app.database import init_db
from backend.app.main import app
from backend.app.models import Invoice, Property, Room, User
from backend.app.schemas import (
    InvoiceCalculateRequest,
    PropertyCreate,
    PropertyUpdate,
    RoomCreate,
    UserRegister,
)
from backend.app.security import create_access_token


class TestNewFeaturesAndSecurity(unittest.TestCase):
    """Test suite covering newly introduced security, tariff, invoice, and lookup features."""

    def setUp(self) -> None:
        """Create an isolated temporary SQLite database for each test case."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_new_features.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)
        self.client = TestClient(app)
        reset_rate_limits()

    def tearDown(self) -> None:
        """Clean up temporary test artifacts."""
        reset_rate_limits()
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
            password="securePassword123!",
            full_name=f"User {username}",
            phone="0912345678",
            role=role,
            invite_code=invite_code,
        )
        registered = register(user_reg, session=session, client_ip="127.0.0.1")
        token = create_access_token(
            {"sub": registered.username, "user_id": registered.id, "role": registered.role}
        )
        return session.get(User, registered.id), token

    def _auth_headers(self, token: str) -> Dict[str, str]:
        """Helper to generate standard Bearer authorization headers."""
        return {"Authorization": f"Bearer {token}"}

    # ========================================================================
    # 1. Duplicate Username Vietnamese Error Message
    # ========================================================================

    def test_duplicate_username_returns_vietnamese_message_and_legacy_marker(self) -> None:
        """Duplicate username registration returns HTTP 400 with Vietnamese error message."""
        with Session(self.engine) as session:
            reg_data = UserRegister(
                username="duplicate_user_1",
                password="passWord123!",
                full_name="Duplicate User",
                role="landlord",
            )
            # First registration succeeds
            register(reg_data, session=session, client_ip="10.0.0.1")

            # Second registration with identical username raises HTTP 400
            with self.assertRaises(HTTPException) as ctx:
                register(reg_data, session=session, client_ip="10.0.0.1")

            self.assertEqual(ctx.exception.status_code, 400)
            detail = ctx.exception.detail
            self.assertIn("Tên đăng nhập đã tồn tại, vui lòng chọn tên khác", detail)
            self.assertIn("already registered", detail)

    # ========================================================================
    # 2. Sliding-Window Rate Limiting (HTTP 429)
    # ========================================================================

    def test_sliding_window_rate_limiting_enforcement(self) -> None:
        """Sliding-window rate limiter raises HTTP 429 after exceeding max requests."""
        # Test low-level check_rate_limit function
        key = "ip_198.51.100.42"
        for _ in range(5):
            self.assertTrue(check_rate_limit(key, max_requests=5, window_seconds=60))
        # 6th request must return False
        self.assertFalse(check_rate_limit(key, max_requests=5, window_seconds=60))

        # Different identifier is not blocked
        other_key = "ip_198.51.100.43"
        self.assertTrue(check_rate_limit(other_key, max_requests=5, window_seconds=60))

        # Reset rate limits clears the block
        reset_rate_limits()
        self.assertTrue(check_rate_limit(key, max_requests=5, window_seconds=60))

        # Integration test: register endpoint rate limiting triggers HTTP 429
        with Session(self.engine) as session:
            spam_ip = "203.0.113.99"
            for i in range(20):
                reg_payload = UserRegister(
                    username=f"spam_user_{i}",
                    password="Password123!",
                    full_name=f"Spam User {i}",
                    role="tenant",
                )
                register(reg_payload, session=session, client_ip=spam_ip)

            # 21st registration from same IP triggers HTTP 429
            with self.assertRaises(HTTPException) as ctx:
                spam_payload = UserRegister(
                    username="spam_user_overflow",
                    password="Password123!",
                    full_name="Spam Overflow",
                    role="tenant",
                )
                register(spam_payload, session=session, client_ip=spam_ip)

            self.assertEqual(ctx.exception.status_code, 429)
            self.assertIn("Quá nhiều yêu cầu", ctx.exception.detail)

    # ========================================================================
    # 3. Property-Level Tariff Configuration & PUT Endpoint
    # ========================================================================

    def test_property_tariff_creation_and_update(self) -> None:
        """Landlord can configure custom tariff on create and update via PUT /properties/{id}."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "landlord_tariff", role="landlord")
            other_landlord, other_token = self._create_user(session, "landlord_other", role="landlord")
            tenant, t_token = self._create_user(session, "tenant_tariff", role="tenant")

            # 1. Create property with custom tariff
            create_resp = self.client.post(
                "/api/v1/properties",
                json={
                    "name": "Khu Tro Dynamic Tariff",
                    "address": "789 CMT8, Q10",
                    "tariff_type": "custom",
                    "custom_elec_rate": 3500.0,
                    "custom_water_rate": 25000.0,
                    "custom_water_type": "per_m3",
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(create_resp.status_code, 201)
            prop_data = create_resp.json()
            prop_id = prop_data["id"]
            self.assertEqual(prop_data["tariff_type"], "custom")
            self.assertEqual(prop_data["custom_elec_rate"], 3500.0)
            self.assertEqual(prop_data["custom_water_rate"], 25000.0)

            # 2. Update property tariff via PUT /api/v1/properties/{id}
            update_resp = self.client.put(
                f"/api/v1/properties/{prop_id}",
                json={
                    "name": "Khu Tro Dynamic Tariff Updated",
                    "tariff_type": "custom",
                    "custom_elec_rate": 3800.0,
                    "custom_water_rate": 28000.0,
                    "custom_water_type": "per_m3",
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(update_resp.status_code, 200)
            updated_data = update_resp.json()
            self.assertEqual(updated_data["name"], "Khu Tro Dynamic Tariff Updated")
            self.assertEqual(updated_data["custom_elec_rate"], 3800.0)
            self.assertEqual(updated_data["custom_water_rate"], 28000.0)

            # 3. Tenant forbidden from updating property (HTTP 403)
            tenant_put_resp = self.client.put(
                f"/api/v1/properties/{prop_id}",
                json={"name": "Hacked Property"},
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(tenant_put_resp.status_code, 403)

            # 4. Other landlord forbidden from updating this property (HTTP 403)
            other_put_resp = self.client.put(
                f"/api/v1/properties/{prop_id}",
                json={"name": "Unauthorized Update"},
                headers=self._auth_headers(other_token),
                session=session,
            )
            self.assertEqual(other_put_resp.status_code, 403)

    # ========================================================================
    # 4. Invoice Draft / Publish Workflow & Short Code
    # ========================================================================

    def test_invoice_draft_to_publish_workflow(self) -> None:
        """Invoice is generated as 'draft' by default, then published via POST /invoices/{id}/publish."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_draft_pub", role="landlord")
            other_landlord, other_token = self._create_user(session, "host_intruder", role="landlord")
            tenant, t_token = self._create_user(session, "tenant_workflow", role="tenant")

            # Create property and room
            p_res = self.client.post(
                "/api/v1/properties",
                json={
                    "name": "Khu Tro Workflow",
                    "tariff_type": "custom",
                    "custom_elec_rate": 3500.0,
                    "custom_water_rate": 20000.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "101", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # 1. Calculate and generate invoice -> defaults to DRAFT
            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 100.0,
                    "elec_end": 200.0,
                    "water_start": 10.0,
                    "water_end": 15.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_resp.status_code, 201)
            inv_data = calc_resp.json()
            inv_id = inv_data["id"]

            self.assertEqual(inv_data["status"], "draft")
            self.assertIsNone(inv_data.get("published_at"))
            self.assertIsNotNone(inv_data.get("short_code"))
            self.assertTrue(inv_data["short_code"].startswith("HD-"))

            # 2. Tenant forbidden from publishing invoice (HTTP 403)
            tenant_pub_resp = self.client.post(
                f"/api/v1/invoices/{inv_id}/publish",
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(tenant_pub_resp.status_code, 403)

            # 3. Other landlord forbidden from publishing this invoice (HTTP 403)
            other_pub_resp = self.client.post(
                f"/api/v1/invoices/{inv_id}/publish",
                headers=self._auth_headers(other_token),
                session=session,
            )
            self.assertEqual(other_pub_resp.status_code, 403)

            # 4. Property landlord publishes invoice -> status becomes 'published'
            pub_resp = self.client.post(
                f"/api/v1/invoices/{inv_id}/publish",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(pub_resp.status_code, 200)
            published_data = pub_resp.json()
            self.assertEqual(published_data["status"], "published")
            self.assertIsNotNone(published_data.get("published_at"))

    # ========================================================================
    # 5. Public Invoice Lookup by Short Code (HD-XXXX)
    # ========================================================================

    def test_public_invoice_lookup_by_short_code(self) -> None:
        """Anyone can look up an invoice publicly using short_code without authentication."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_short_code", role="landlord")

            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Tro Short Code"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "202", "current_people_count": 3},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 0.0,
                    "elec_end": 80.0,
                    "water_start": 0.0,
                    "water_end": 4.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            inv_data = calc_resp.json()
            short_code = inv_data["short_code"]
            share_token = inv_data["share_token"]

            # Lookup by exact uppercase short_code
            sc_resp = self.client.get(
                f"/api/v1/invoices/public/{short_code}",
                session=session,
            )
            self.assertEqual(sc_resp.status_code, 200)
            self.assertEqual(sc_resp.json()["id"], inv_data["id"])
            self.assertEqual(sc_resp.json()["short_code"], short_code)

            # Lookup by lowercase short_code (case-insensitive)
            sc_lower_resp = self.client.get(
                f"/api/v1/invoices/public/{short_code.lower()}",
                session=session,
            )
            self.assertEqual(sc_lower_resp.status_code, 200)
            self.assertEqual(sc_lower_resp.json()["id"], inv_data["id"])

            # Lookup by share_token still works
            token_resp = self.client.get(
                f"/api/v1/invoices/public/{share_token}",
                session=session,
            )
            self.assertEqual(token_resp.status_code, 200)
            self.assertEqual(token_resp.json()["id"], inv_data["id"])

            # Non-existent short_code returns 404
            not_found_resp = self.client.get(
                "/api/v1/invoices/public/HD-999999",
                session=session,
            )
            self.assertEqual(not_found_resp.status_code, 404)

    # ========================================================================
    # 6. User Notifications Endpoint
    # ========================================================================

    def test_user_notifications_endpoint(self) -> None:
        """GET /notifications returns user notifications; unauthenticated returns 401."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_notif", role="landlord")
            tenant, t_token = self._create_user(session, "tenant_notif", role="tenant")

            # Initially, empty lists when no properties/invoices exist
            empty_resp = self.client.get(
                "/api/v1/notifications",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(empty_resp.status_code, 200)
            self.assertEqual(empty_resp.json(), [])

            # Create property and room
            p_res = self.client.post(
                "/api/v1/properties",
                json={"name": "Khu Notif"},
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "301", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Assign tenant to room
            room = session.get(Room, room_id)
            room.tenant_id = tenant.id
            session.add(room)
            session.commit()

            # Create invoice
            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 0.0,
                    "elec_end": 50.0,
                    "water_start": 0.0,
                    "water_end": 2.0,
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            inv_id = calc_resp.json()["id"]

            # Landlord now sees notification about draft invoice
            l_resp = self.client.get(
                "/api/v1/notifications",
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(l_resp.status_code, 200)
            notifs = l_resp.json()
            self.assertTrue(len(notifs) > 0)
            self.assertIn("title", notifs[0])
            self.assertIn("message", notifs[0])

            # Tenant does NOT see draft invoice in notifications
            t_draft_resp = self.client.get(
                "/api/v1/notifications",
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(t_draft_resp.status_code, 200)
            self.assertEqual(len(t_draft_resp.json()), 0)

            # Landlord publishes invoice
            self.client.post(
                f"/api/v1/invoices/{inv_id}/publish",
                headers=self._auth_headers(l_token),
                session=session,
            )

            # Tenant now sees notification about published invoice
            t_resp = self.client.get(
                "/api/v1/notifications",
                headers=self._auth_headers(t_token),
                session=session,
            )
            self.assertEqual(t_resp.status_code, 200)
            t_notifs = t_resp.json()
            self.assertTrue(len(t_notifs) > 0)
            self.assertIn("title", t_notifs[0])

            # Unauthenticated returns 401
            unauth_resp = self.client.get(
                "/api/v1/notifications",
                session=session,
            )
            self.assertEqual(unauth_resp.status_code, 401)

    # ========================================================================
    # 7. Additional Verification: Custom Tariff Calculation & Meter Readings
    # ========================================================================

    def test_property_custom_tariff_applied_to_invoice_and_breakdown_meter_readings(self) -> None:
        """Property custom tariff is automatically applied to invoice calculation and breakdown stores meter readings."""
        with Session(self.engine) as session:
            landlord, l_token = self._create_user(session, "host_tariff_calc", role="landlord")

            # Create property with custom tariff (4,000 đ/kWh, 20,000 đ/m³)
            p_res = self.client.post(
                "/api/v1/properties",
                json={
                    "name": "Khu Tro Custom Tariff",
                    "tariff_type": "custom",
                    "custom_elec_rate": 4000.0,
                    "custom_water_rate": 20000.0,
                    "custom_water_type": "PER_M3",
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            prop_id = p_res.json()["id"]

            r_res = self.client.post(
                f"/api/v1/properties/{prop_id}/rooms",
                json={"room_number": "T101", "current_people_count": 2},
                headers=self._auth_headers(l_token),
                session=session,
            )
            room_id = r_res.json()["id"]

            # Calculate invoice without entering actual_collected_amount
            calc_resp = self.client.post(
                f"/api/v1/rooms/{room_id}/invoices/calculate",
                json={
                    "month_year": "2026-09",
                    "elec_start": 100.0,
                    "elec_end": 200.0,  # 100 kWh
                    "water_start": 10.0,
                    "water_end": 15.0,  # 5 m³
                },
                headers=self._auth_headers(l_token),
                session=session,
            )
            self.assertEqual(calc_resp.status_code, 201)
            inv = calc_resp.json()

            # Expected custom calculation: 100 kWh * 4,000 + 5 m³ * 20,000 = 400,000 + 100,000 = 500,000 đ
            expected_custom_collected = 500000.0
            self.assertEqual(inv["actual_collected_amount"], expected_custom_collected)
            self.assertTrue(inv["diff_amount"] > 0)  # Overcharge detected!

            # Breakdown must contain meter_reading with correct numbers
            b = inv["breakdown"]
            self.assertIn("meter_reading", b)
            self.assertEqual(b["meter_reading"]["elec_start"], 100.0)
            self.assertEqual(b["meter_reading"]["elec_end"], 200.0)
            self.assertEqual(b["meter_reading"]["water_start"], 10.0)
            self.assertEqual(b["meter_reading"]["water_end"], 15.0)

            # Public lookup by short_code in lowercase and with # prefix
            short_code = inv["short_code"]
            sc_lower_resp = self.client.get(
                f"/api/v1/invoices/public/{short_code.lower()}",
                session=session,
            )
            self.assertEqual(sc_lower_resp.status_code, 200)
            self.assertEqual(sc_lower_resp.json()["id"], inv["id"])

            sc_hash_resp = self.client.get(
                f"/api/v1/invoices/public/%23{short_code}",
                session=session,
            )
            self.assertEqual(sc_hash_resp.status_code, 200)
            self.assertEqual(sc_hash_resp.json()["id"], inv["id"])


if __name__ == "__main__":
    unittest.main()
