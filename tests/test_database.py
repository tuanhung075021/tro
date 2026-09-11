# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Unit tests for SQLite database layer and dynamic pricing configuration."""

import os
import tempfile
import unittest
import uuid
from decimal import Decimal

from backend.app.compat import SQLModel, Session, create_engine, select
from backend.app.database import get_session, init_db
from backend.app.models import (
    DEFAULT_TIERS_JSON,
    Invoice,
    MeterReading,
    Property,
    Room,
    SystemConfig,
    User,
    generate_invite_code,
    get_default_tiers,
)
from core.calculator import (
    calculate_electricity_tiered,
    calculate_electricity_tier3,
    calculate_water,
)
from core.models import ElectricityConfig, WaterConfig, WaterPricingType


class TestDatabaseAndDynamicConfig(unittest.TestCase):
    """Test suite for database initialization, schema integrity, and dynamic config."""

    def setUp(self) -> None:
        """Create a fresh temporary SQLite database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_tro.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )


    def tearDown(self) -> None:
        """Clean up temporary test directory."""
        self.temp_dir.cleanup()

    def test_init_db_creates_tables_and_seeds_default_config(self) -> None:
        """init_db() must create tables and insert standard statutory pricing parameters."""
        init_db(self.engine)

        with Session(self.engine) as session:
            config = session.get(SystemConfig, 1)
            self.assertIsNotNone(config, "SystemConfig with id=1 must be seeded.")
            self.assertEqual(config.id, 1)

            # Statutory electricity values
            self.assertAlmostEqual(config.electricity_vat_rate, 0.08, places=4)
            self.assertAlmostEqual(config.electricity_tier3_price, 2380.0, places=2)

            # Verify 6 progressive tiers
            tiers = config.get_tiers()
            self.assertEqual(len(tiers), 6, "Must configure exactly 6 electricity tiers.")
            self.assertEqual(tiers[0]["tier_number"], 1)
            self.assertEqual(tiers[0]["max_threshold"], 50.0)
            self.assertEqual(tiers[0]["unit_price"], 1984.0)

            self.assertEqual(tiers[1]["tier_number"], 2)
            self.assertEqual(tiers[1]["max_threshold"], 50.0)
            self.assertEqual(tiers[1]["unit_price"], 2050.0)

            self.assertEqual(tiers[2]["tier_number"], 3)
            self.assertEqual(tiers[2]["max_threshold"], 100.0)
            self.assertEqual(tiers[2]["unit_price"], 2380.0)

            self.assertEqual(tiers[3]["tier_number"], 4)
            self.assertEqual(tiers[3]["max_threshold"], 100.0)
            self.assertEqual(tiers[3]["unit_price"], 2998.0)

            self.assertEqual(tiers[4]["tier_number"], 5)
            self.assertEqual(tiers[4]["max_threshold"], 100.0)
            self.assertEqual(tiers[4]["unit_price"], 3350.0)

            self.assertEqual(tiers[5]["tier_number"], 6)
            self.assertIsNone(tiers[5]["max_threshold"])
            self.assertEqual(tiers[5]["unit_price"], 3460.0)

            # Statutory water values
            self.assertEqual(config.water_pricing_type, "PER_M3")
            self.assertAlmostEqual(config.water_unit_price, 8500.0, places=2)
            self.assertAlmostEqual(config.water_vat_rate, 0.05, places=4)
            self.assertAlmostEqual(config.water_env_fee_rate, 0.10, places=4)

    def test_init_db_is_idempotent(self) -> None:
        """Calling init_db multiple times must not overwrite or duplicate existing configuration."""
        init_db(self.engine)

        # Modify configuration
        with Session(self.engine) as session:
            config = session.get(SystemConfig, 1)
            config.electricity_tier3_price = 2500.0
            session.add(config)
            session.commit()

        # Call init_db a second time
        init_db(self.engine)

        with Session(self.engine) as session:
            all_configs = session.exec(select(SystemConfig)).all()
            self.assertEqual(len(all_configs), 1, "Must not create duplicate SystemConfig entries.")
            config = session.get(SystemConfig, 1)
            self.assertAlmostEqual(config.electricity_tier3_price, 2500.0, places=2)

    def test_system_config_crud_and_dynamic_modifications(self) -> None:
        """Biểu giá, thuế suất, phí BVMT và các bậc phải đọc/ghi/sửa động từ CSDL."""
        init_db(self.engine)

        # 1. Update existing config parameters
        with Session(self.engine) as session:
            config = session.get(SystemConfig, 1)
            config.electricity_vat_rate = 0.10  # VAT changes from 8% to 10%
            config.electricity_tier3_price = 2400.0
            config.water_pricing_type = "PER_PERSON"
            config.water_unit_price = 80000.0  # 80.000 VND / person
            config.water_vat_rate = 0.08
            config.water_env_fee_rate = 0.12

            # Modify tier pricing
            tiers = config.get_tiers()
            tiers[0]["unit_price"] = 2100.0
            config.set_tiers(tiers)

            session.add(config)
            session.commit()

        # 2. Re-read and assert persistence in a fresh session
        with Session(self.engine) as session:
            updated = session.get(SystemConfig, 1)
            self.assertAlmostEqual(updated.electricity_vat_rate, 0.10, places=4)
            self.assertAlmostEqual(updated.electricity_tier3_price, 2400.0, places=2)
            self.assertEqual(updated.water_pricing_type, "PER_PERSON")
            self.assertAlmostEqual(updated.water_unit_price, 80000.0, places=2)
            self.assertAlmostEqual(updated.water_vat_rate, 0.08, places=4)
            self.assertAlmostEqual(updated.water_env_fee_rate, 0.12, places=4)

            persisted_tiers = updated.get_tiers()
            self.assertEqual(persisted_tiers[0]["unit_price"], 2100.0)
            self.assertEqual(len(persisted_tiers), 6)

    def test_user_property_room_crud(self) -> None:
        """CRUD operations for User, Property, and Room entities."""
        init_db(self.engine)

        with Session(self.engine) as session:
            # Create Landlord
            landlord = User(
                username="landlord_test",
                hashed_password="hashed_secret_pw",
                full_name="Nguyễn Văn Chủ",
                phone="0901234567",
                role="landlord",
            )
            session.add(landlord)
            session.commit()
            self.assertIsNotNone(landlord.id)

            # Create Tenant
            tenant = User(
                username="tenant_test",
                hashed_password="hashed_tenant_pw",
                full_name="Trần Thị Thuê",
                phone="0912345678",
                role="tenant",
            )
            session.add(tenant)
            session.commit()
            self.assertIsNotNone(tenant.id)

            # Create Property
            prop = Property(
                name="Nhà Trọ Minh Bạch Cầu Giấy",
                address="Số 10 Ngõ 50 Dịch Vọng Hậu, Cầu Giấy, Hà Nội",
                landlord_id=landlord.id,
            )
            session.add(prop)
            session.commit()
            self.assertIsNotNone(prop.id)

            # Create Room
            invite_code = generate_invite_code(8)
            self.assertEqual(len(invite_code), 8)
            self.assertTrue(invite_code.isalnum())

            room = Room(
                room_number="201",
                property_id=prop.id,
                invite_code=invite_code,
                status="active",
                current_people_count=3,
            )
            session.add(room)
            session.commit()
            self.assertIsNotNone(room.id)

        # Query back and verify relations
        with Session(self.engine) as session:
            queried_user = session.exec(select(User).where(User.username == "landlord_test")).first()
            self.assertIsNotNone(queried_user)
            self.assertEqual(queried_user.role, "landlord")

            queried_room = session.get(Room, room.id)
            self.assertIsNotNone(queried_room)
            self.assertEqual(queried_room.room_number, "201")
            self.assertEqual(queried_room.current_people_count, 3)
            self.assertEqual(queried_room.status, "active")

    def test_meter_reading_and_invoice_crud(self) -> None:
        """CRUD operations for MeterReading and Invoice entities with share_token."""
        init_db(self.engine)

        with Session(self.engine) as session:
            # Create room
            room = Room(
                room_number="101",
                property_id=None,
                invite_code=generate_invite_code(),
                status="active",
                current_people_count=2,
            )
            session.add(room)
            session.commit()

            # Record meter reading
            reading = MeterReading(
                room_id=room.id,
                month_year="2026-09",
                elec_start=150.0,
                elec_end=270.0,
                water_start=20.0,
                water_end=32.0,
            )
            session.add(reading)
            session.commit()
            self.assertIsNotNone(reading.id)
            self.assertEqual(reading.month_year, "2026-09")

            # Create Invoice
            invoice = Invoice(
                room_id=room.id,
                month_year="2026-09",
                elec_kwh=120.0,
                elec_amount=269244.0,
                water_usage=12.0,
                water_amount=117300.0,
                total_statutory_amount=386544.0,
                actual_collected_amount=480000.0,
                diff_amount=93456.0,
                breakdown_json='{"elec": "detail", "water": "detail"}',
            )
            session.add(invoice)
            session.commit()
            self.assertIsNotNone(invoice.id)

            # Verify share_token is valid UUID
            uuid_obj = uuid.UUID(invoice.share_token)
            self.assertEqual(str(uuid_obj), invoice.share_token)

        # Read back
        with Session(self.engine) as session:
            queried_inv = session.get(Invoice, invoice.id)
            self.assertIsNotNone(queried_inv)
            self.assertAlmostEqual(queried_inv.diff_amount, 93456.0, places=2)
            self.assertAlmostEqual(queried_inv.total_statutory_amount, 386544.0, places=2)
            self.assertIn("elec", queried_inv.breakdown_json)

    def test_get_session_dependency(self) -> None:
        """get_session generator yields an operational database session."""
        init_db(self.engine)
        session_gen = get_session(custom_engine=self.engine)
        session = next(session_gen)
        try:
            config = session.get(SystemConfig, 1)
            self.assertIsNotNone(config)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass


    def test_user_delete_and_rollback(self) -> None:
        """Test transaction rollback and entity deletion."""
        init_db(self.engine)

        with Session(self.engine) as session:
            user = User(
                username="rollback_user",
                hashed_password="pw",
                role="tenant",
            )
            session.add(user)
            # Rollback before commit
            session.rollback()

        with Session(self.engine) as session:
            queried = session.exec(select(User).where(User.username == "rollback_user")).first()
            self.assertIsNone(queried, "User must not exist after rollback.")

        # Commit then delete
        with Session(self.engine) as session:
            user = User(
                username="delete_me",
                hashed_password="pw",
                role="tenant",
            )
            session.add(user)
            session.commit()
            uid = user.id

        with Session(self.engine) as session:
            user_to_delete = session.get(User, uid)
            self.assertIsNotNone(user_to_delete)
            session.delete(user_to_delete)
            session.commit()

        with Session(self.engine) as session:
            deleted = session.get(User, uid)
            self.assertIsNone(deleted, "User must be None after deletion.")

    def test_query_filtering_multiple_rooms(self) -> None:
        """Test filtering rooms by property_id and status."""
        init_db(self.engine)

        with Session(self.engine) as session:
            prop1 = Property(name="Khu A", address="123 Duong A")
            prop2 = Property(name="Khu B", address="456 Duong B")
            session.add(prop1)
            session.add(prop2)
            session.commit()

            # Add rooms to Khu A
            r1 = Room(room_number="A101", property_id=prop1.id, status="active", current_people_count=2)
            r2 = Room(room_number="A102", property_id=prop1.id, status="empty", current_people_count=0)
            # Add room to Khu B
            r3 = Room(room_number="B101", property_id=prop2.id, status="active", current_people_count=4)
            session.add(r1)
            session.add(r2)
            session.add(r3)
            session.commit()

        with Session(self.engine) as session:
            rooms_a = session.exec(select(Room).where(Room.property_id == prop1.id)).all()
            self.assertEqual(len(rooms_a), 2)
            room_numbers = {r.room_number for r in rooms_a}
            self.assertEqual(room_numbers, {"A101", "A102"})

            active_rooms_a = session.exec(
                select(Room).where(Room.property_id == prop1.id, Room.status == "active")
            ).all()
            self.assertEqual(len(active_rooms_a), 1)
            self.assertEqual(active_rooms_a[0].room_number, "A101")

    def test_invite_code_generation_formats(self) -> None:
        """Test invite code generation length, character set, and randomness."""
        code_6 = generate_invite_code(6)
        self.assertEqual(len(code_6), 6)
        self.assertTrue(code_6.isalnum())
        self.assertTrue(code_6.isupper())

        code_8 = generate_invite_code(8)
        self.assertEqual(len(code_8), 8)

        codes = {generate_invite_code(8) for _ in range(50)}
        self.assertEqual(len(codes), 50, "Generated invite codes must be unique.")

    def test_system_config_helpers_and_non_existent_record(self) -> None:
        """Test helper methods on SystemConfig and querying non-existent primary key."""
        init_db(self.engine)

        with Session(self.engine) as session:
            # Query non-existent
            missing = session.get(SystemConfig, 999)
            self.assertIsNone(missing)

            # Test set_tiers with custom list
            config = session.get(SystemConfig, 1)
            custom_tiers = [
                {"tier_number": 1, "max_threshold": 100.0, "unit_price": 2000.0},
                {"tier_number": 2, "max_threshold": None, "unit_price": 3000.0},
            ]
            config.set_tiers(custom_tiers)
            session.add(config)
            session.commit()

        with Session(self.engine) as session:
            reloaded = session.get(SystemConfig, 1)
            tiers = reloaded.get_tiers()
            self.assertEqual(len(tiers), 2)
            self.assertEqual(tiers[0]["max_threshold"], 100.0)
            self.assertEqual(tiers[1]["unit_price"], 3000.0)

    def test_room_default_invite_code_and_custom_code(self) -> None:
        """Room automatically gets a random 8-character invite code if not provided."""
        init_db(self.engine)
        with Session(self.engine) as session:
            room_auto = Room(room_number="101")
            room_custom = Room(room_number="102", invite_code="CUSTOM99")
            session.add(room_auto)
            session.add(room_custom)
            session.commit()

            self.assertIsNotNone(room_auto.invite_code)
            self.assertEqual(len(room_auto.invite_code), 8)
            self.assertTrue(room_auto.invite_code.isalnum())
            self.assertEqual(room_custom.invite_code, "CUSTOM99")

    def test_user_role_properties(self) -> None:
        """User is_landlord and is_tenant helper properties."""
        landlord = User(username="ll", hashed_password="pw", role="landlord")
        tenant = User(username="tt", hashed_password="pw", role="tenant")
        self.assertTrue(landlord.is_landlord)
        self.assertFalse(landlord.is_tenant)
        self.assertTrue(tenant.is_tenant)
        self.assertFalse(tenant.is_landlord)

    def test_invoice_breakdown_helpers(self) -> None:
        """Invoice get_breakdown and set_breakdown helpers."""
        init_db(self.engine)
        with Session(self.engine) as session:
            room = Room(room_number="301")
            session.add(room)
            session.commit()

            inv = Invoice(room_id=room.id, month_year="2026-09")
            self.assertIsNone(inv.get_breakdown())

            sample_data = {"elec": {"kwh": 100, "cost": 200000}, "water": {"usage": 10, "cost": 85000}}
            inv.set_breakdown(sample_data)
            session.add(inv)
            session.commit()
            inv_id = inv.id

        with Session(self.engine) as session:
            loaded = session.get(Invoice, inv_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.get_breakdown(), sample_data)

    def test_system_config_bridge_with_core_calculator(self) -> None:
        """Bridge SystemConfig with core calculation engine and verify dynamic calculations."""
        init_db(self.engine)
        with Session(self.engine) as session:
            config = session.get(SystemConfig, 1)
            elec_cfg = config.to_electricity_config()
            water_cfg = config.to_water_config()

            self.assertIsInstance(elec_cfg, ElectricityConfig)
            self.assertIsInstance(water_cfg, WaterConfig)
            self.assertEqual(len(elec_cfg.tiers), 6)
            self.assertEqual(water_cfg.pricing_type, WaterPricingType.PER_M3)

            # Calculate electricity and water with standard config
            res_std = calculate_electricity_tiered(consumption=100, quota=1, config=elec_cfg)
            self.assertGreater(res_std.total_amount, Decimal("0"))

            res_water = calculate_water(usage=10, config=water_cfg)
            self.assertGreater(res_water.total_amount, Decimal("0"))

            # Dynamically modify VAT and tier prices in DB
            config.electricity_vat_rate = 0.10
            config.set_tiers([
                {"tier_number": 1, "max_threshold": 50.0, "unit_price": 2500.0},
                {"tier_number": 2, "max_threshold": None, "unit_price": 3000.0},
            ])
            session.add(config)
            session.commit()

        with Session(self.engine) as session:
            updated_config = session.get(SystemConfig, 1)
            updated_elec_cfg = updated_config.to_electricity_config()
            res_custom = calculate_electricity_tiered(consumption=100, quota=1, config=updated_elec_cfg)
            self.assertNotEqual(res_std.total_amount, res_custom.total_amount)

            # Test from_configs factory
            new_sys_config = SystemConfig.from_configs(updated_elec_cfg, water_cfg, id=2)
            self.assertEqual(new_sys_config.id, 2)
            self.assertAlmostEqual(new_sys_config.electricity_vat_rate, 0.10)
            self.assertEqual(len(new_sys_config.get_tiers()), 2)

    def test_system_config_corrupted_json_fallback_and_validation(self) -> None:
        """SystemConfig gracefully handles corrupted tiers_json and validates input."""
        config = SystemConfig(id=1, tiers_json="invalid json string")
        default_tiers = config.get_tiers()
        self.assertEqual(len(default_tiers), 6, "Must fall back to default tiers on corrupted JSON.")

        with self.assertRaises(TypeError):
            config.set_tiers("not a list")  # type: ignore

    def test_query_ordering_limit_and_offset(self) -> None:
        """Select query ordering, limit, and offset."""
        init_db(self.engine)
        with Session(self.engine) as session:
            for i in range(1, 6):
                session.add(Room(room_number=f"R{i:03d}"))
            session.commit()

        with Session(self.engine) as session:
            # Order by desc
            rooms_desc = session.exec(select(Room).order_by(Room.room_number.desc())).all()
            self.assertEqual([r.room_number for r in rooms_desc], ["R005", "R004", "R003", "R002", "R001"])

            # Limit and offset
            page = session.exec(select(Room).order_by(Room.room_number.asc()).limit(2).offset(1)).all()
            self.assertEqual([r.room_number for r in page], ["R002", "R003"])

    def test_query_null_and_not_null_conditions(self) -> None:
        """Query conditions with NULL values (IS NULL and IS NOT NULL)."""
        init_db(self.engine)
        with Session(self.engine) as session:
            prop = Property(name="Khu C")
            session.add(prop)
            session.commit()

            r_no_prop = Room(room_number="NO_PROP", property_id=None)
            r_with_prop = Room(room_number="WITH_PROP", property_id=prop.id)
            session.add(r_no_prop)
            session.add(r_with_prop)
            session.commit()

        with Session(self.engine) as session:
            null_rooms = session.exec(select(Room).where(Room.property_id == None)).all()
            self.assertTrue(any(r.room_number == "NO_PROP" for r in null_rooms))
            self.assertFalse(any(r.room_number == "WITH_PROP" for r in null_rooms))

            not_null_rooms = session.exec(select(Room).where(Room.property_id != None)).all()
            self.assertTrue(any(r.room_number == "WITH_PROP" for r in not_null_rooms))
            self.assertFalse(any(r.room_number == "NO_PROP" for r in not_null_rooms))

            is_null_rooms = session.exec(select(Room).where(Room.property_id.is_(None))).all()
            self.assertTrue(any(r.room_number == "NO_PROP" for r in is_null_rooms))

    def test_query_compound_and_in_conditions(self) -> None:
        """Compound condition (&) and in_ / not_in conditions."""
        init_db(self.engine)
        with Session(self.engine) as session:
            session.add(Room(room_number="A1", status="active", current_people_count=1))
            session.add(Room(room_number="A2", status="active", current_people_count=4))
            session.add(Room(room_number="E1", status="empty", current_people_count=0))
            session.commit()

        with Session(self.engine) as session:
            # Compound AND
            compound = session.exec(
                select(Room).where((Room.status == "active") & (Room.current_people_count > 2))
            ).all()
            self.assertEqual(len(compound), 1)
            self.assertEqual(compound[0].room_number, "A2")

            # IN list
            in_result = session.exec(select(Room).where(Room.status.in_(["empty"]))).all()
            self.assertEqual(len(in_result), 1)
            self.assertEqual(in_result[0].room_number, "E1")

            # Empty IN list (must return empty without crashing)
            empty_in = session.exec(select(Room).where(Room.status.in_([]))).all()
            self.assertEqual(len(empty_in), 0)

    def test_delete_uncommitted_object_does_not_insert(self) -> None:
        """Adding an object and then deleting it before commit must not insert into DB."""
        init_db(self.engine)
        with Session(self.engine) as session:
            ghost_user = User(username="ghost_user", hashed_password="pw", role="tenant")
            session.add(ghost_user)
            session.delete(ghost_user)
            session.commit()

        with Session(self.engine) as session:
            queried = session.exec(select(User).where(User.username == "ghost_user")).first()
            self.assertIsNone(queried, "Ghost user must never be inserted into the database.")

    def test_foreign_key_constraint_enforcement(self) -> None:
        """Enforcing foreign key constraints prevents orphan child records."""
        import sqlite3
        init_db(self.engine)
        with Session(self.engine) as session:
            inv = Invoice(room_id=99999, month_year="2026-09")
            session.add(inv)
            with self.assertRaises(sqlite3.IntegrityError):
                session.commit()

    def test_default_init_db_creates_tro_db(self) -> None:
        """Test calling init_db() without parameters initializes default tro.db database."""
        init_db()
        # Verify file exists
        self.assertTrue(os.path.exists("tro.db"), "Default tro.db file must be created.")
        session_gen = get_session()
        session = next(session_gen)
        try:
            config = session.get(SystemConfig, 1)
            self.assertIsNotNone(config, "Default tro.db must have seeded SystemConfig.")
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass


if __name__ == "__main__":
    unittest.main()

