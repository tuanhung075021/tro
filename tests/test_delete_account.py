# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Unit and integration tests for account deletion safety, password verification, and foreign key cascades."""

import os
import tempfile
import unittest
from typing import Dict, Tuple

from backend.app.auth import (
    delete_account,
    get_current_user,
    register,
    reset_rate_limits,
)
from backend.app.compat import HTTPException, Session, TestClient, create_engine, select, status
from backend.app.database import init_db
from backend.app.main import app
from backend.app.models import (
    AdminApprovalRequest,
    AdminSecretKey,
    Invoice,
    MeterReading,
    Property,
    Room,
    TariffChangeLog,
    User,
    generate_invite_code,
)
from backend.app.schemas import DeleteAccountIn, UserRegister
from backend.app.security import create_access_token


class TestDeleteAccountSafety(unittest.TestCase):
    """Test suite covering account deletion safeguards, role constraints, and data cascades."""

    def setUp(self) -> None:
        """Create an isolated temporary SQLite database for each test case."""
        reset_rate_limits()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_delete.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)

    def tearDown(self) -> None:
        """Clean up temporary test artifacts."""
        reset_rate_limits()
        self.temp_dir.cleanup()

    def _create_user(
        self,
        session: Session,
        username: str,
        password: str = "securePassword123",
        role: str = "tenant",
    ) -> Tuple[User, str]:
        """Helper to create and authenticate a user."""
        user_reg = UserRegister(
            username=username,
            password=password,
            full_name=f"Full {username}",
            phone="0901234567",
            role="tenant" if role in ("admin", "root_admin", "pending_admin") else role,
        )
        registered = register(user_reg, session=session)
        db_user = session.get(User, registered.id)
        if role in ("admin", "root_admin", "pending_admin"):
            db_user.role = role
            session.add(db_user)
            session.commit()
            session.refresh(db_user)

        token = create_access_token(
            {"sub": db_user.username, "user_id": db_user.id, "role": db_user.role}
        )
        return db_user, token

    def test_delete_account_wrong_password_fails(self) -> None:
        """Deleting account with incorrect password must return HTTP 400 Bad Request."""
        with Session(self.engine) as session:
            user, _ = self._create_user(session, "tenant_pw_test", password="correctPassword")

            with self.assertRaises(HTTPException) as ctx:
                delete_account(
                    payload=DeleteAccountIn(password="incorrectPassword"),
                    current_user=user,
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Mật khẩu xác nhận không chính xác", ctx.exception.detail)

            # User must still exist in DB
            db_user = session.get(User, user.id)
            self.assertIsNotNone(db_user)

    def test_delete_tenant_account_vacates_room(self) -> None:
        """When a tenant deletes their account, any occupied room must be reset to empty with a new invite code."""
        with Session(self.engine) as session:
            landlord, _ = self._create_user(session, "landlord_for_tenant", role="landlord")
            prop = Property(name="Khu Trọ Hoàng Gia", landlord_id=landlord.id)
            session.add(prop)
            session.commit()
            session.refresh(prop)

            room = Room(room_number="101", property_id=prop.id)
            session.add(room)
            session.commit()
            session.refresh(room)
            initial_invite_code = room.invite_code

            tenant, _ = self._create_user(session, "room_tenant", password="tenantPass123", role="tenant")
            room.assign_tenant(tenant.id)
            session.add(room)
            session.commit()
            session.refresh(room)

            self.assertEqual(room.tenant_id, tenant.id)
            self.assertEqual(room.status, "active")

            # Tenant deletes account
            result = delete_account(
                payload=DeleteAccountIn(password="tenantPass123"),
                current_user=tenant,
                session=session,
            )
            self.assertIn("Tài khoản của bạn đã được xóa thành công", result["message"])

            # Verify tenant is removed from database
            deleted_tenant = session.get(User, tenant.id)
            self.assertIsNone(deleted_tenant)

            # Verify room is now empty and has a new invite code
            session.refresh(room)
            self.assertIsNone(room.tenant_id)
            self.assertEqual(room.status, "empty")
            self.assertNotEqual(room.invite_code, initial_invite_code)

    def test_delete_landlord_with_active_tenants_fails(self) -> None:
        """Landlord account deletion must be blocked if any room still has active tenants."""
        with Session(self.engine) as session:
            landlord, _ = self._create_user(session, "busy_landlord", password="landlordPass", role="landlord")
            prop = Property(name="Khu Trọ Hòa Bình", landlord_id=landlord.id)
            session.add(prop)
            session.commit()
            session.refresh(prop)

            room = Room(room_number="201", property_id=prop.id)
            session.add(room)
            session.commit()
            session.refresh(room)

            tenant, _ = self._create_user(session, "active_tenant", role="tenant")
            room.assign_tenant(tenant.id)
            session.add(room)
            session.commit()

            with self.assertRaises(HTTPException) as ctx:
                delete_account(
                    payload=DeleteAccountIn(password="landlordPass"),
                    current_user=landlord,
                    session=session,
                )

            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Không thể xóa tài khoản", ctx.exception.detail)
            self.assertIn("1 phòng đang có người thuê", ctx.exception.detail)

            # Verify landlord and property still exist
            self.assertIsNotNone(session.get(User, landlord.id))
            self.assertIsNotNone(session.get(Property, prop.id))

    def test_delete_landlord_empty_rooms_cascades_cleanly(self) -> None:
        """When a landlord with vacant rooms deletes account, properties, rooms, readings, and invoices cascade cleanly."""
        with Session(self.engine) as session:
            landlord, _ = self._create_user(session, "vacant_landlord", password="cleanPassword", role="landlord")
            prop = Property(name="Khu Trọ Trống", landlord_id=landlord.id)
            session.add(prop)
            session.commit()
            session.refresh(prop)

            room = Room(room_number="301", property_id=prop.id)
            session.add(room)
            session.commit()
            session.refresh(room)

            reading = MeterReading(room_id=room.id, month_year="2026-09", elec_start=100, elec_end=150)
            session.add(reading)
            session.commit()
            session.refresh(reading)

            invoice = Invoice(
                room_id=room.id,
                month_year="2026-09",
                elec_kwh=50,
                elec_amount=100000,
                water_usage=5,
                water_amount=42500,
                total_statutory_amount=142500,
                actual_collected_amount=142500,
            )
            session.add(invoice)
            session.commit()
            session.refresh(invoice)

            # Perform deletion
            result = delete_account(
                payload=DeleteAccountIn(password="cleanPassword"),
                current_user=landlord,
                session=session,
            )
            self.assertIn("Tài khoản của bạn đã được xóa thành công", result["message"])

            # Verify everything is cascade-deleted
            self.assertIsNone(session.get(User, landlord.id))
            self.assertIsNone(session.get(Property, prop.id))
            self.assertIsNone(session.get(Room, room.id))
            self.assertIsNone(session.get(MeterReading, reading.id))
            self.assertIsNone(session.get(Invoice, invoice.id))

    def test_delete_sole_root_admin_fails(self) -> None:
        """The sole Root Admin in the system cannot delete their account."""
        with Session(self.engine) as session:
            root_admin, _ = self._create_user(session, "the_sole_root", password="rootPass123", role="root_admin")

            with self.assertRaises(HTTPException) as ctx:
                delete_account(
                    payload=DeleteAccountIn(password="rootPass123"),
                    current_user=root_admin,
                    session=session,
                )

            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Không thể xóa tài khoản Root Admin duy nhất của hệ thống", ctx.exception.detail)
            self.assertIsNotNone(session.get(User, root_admin.id))

    def test_delete_admin_with_tariff_changelog_reassigns_to_root_admin(self) -> None:
        """When an Admin who changed tariffs deletes account, TariffChangeLog is reassigned to Root Admin to preserve audit trail."""
        with Session(self.engine) as session:
            root_admin, _ = self._create_user(session, "root_keeper", role="root_admin")
            sub_admin, _ = self._create_user(session, "sub_editor", password="subAdminPass", role="admin")

            # Create a TariffChangeLog record authored by sub_admin
            log = TariffChangeLog(
                changed_by_id=sub_admin.id,
                tariff_version="CUSTOM-2026-09",
                snapshot_json='{"tier1": 2000}',
                note="Cập nhật bởi sub_editor",
            )
            session.add(log)
            session.commit()
            session.refresh(log)

            # sub_admin deletes account
            result = delete_account(
                payload=DeleteAccountIn(password="subAdminPass"),
                current_user=sub_admin,
                session=session,
            )
            self.assertIn("Tài khoản của bạn đã được xóa thành công", result["message"])

            # sub_admin is gone
            self.assertIsNone(session.get(User, sub_admin.id))

            # log record is preserved and reassigned to root_admin
            session.refresh(log)
            self.assertEqual(log.changed_by_id, root_admin.id)
            self.assertIn("[Chuyển giao từ @sub_editor]", log.note)

    def test_delete_root_admin_when_multiple_root_admins_exist(self) -> None:
        """When multiple Root Admins exist, a Root Admin can delete their account cleanly."""
        with Session(self.engine) as session:
            root1, _ = self._create_user(session, "root_one", password="rootPassOne", role="root_admin")
            root2, _ = self._create_user(session, "root_two", role="root_admin")

            result = delete_account(
                payload=DeleteAccountIn(password="rootPassOne"),
                current_user=root1,
                session=session,
            )
            self.assertIn("Tài khoản của bạn đã được xóa thành công", result["message"])

            self.assertIsNone(session.get(User, root1.id))
            self.assertIsNotNone(session.get(User, root2.id))
