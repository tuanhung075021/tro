# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Unit tests for authentication, JWT security, RBAC, and room invite code lifecycle."""

from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest
from typing import Optional

from backend.app.auth import (
    get_current_user,
    login,
    register,
    remove_tenant_from_room,
    require_landlord,
    require_tenant,
    router,
)
from backend.app.compat import (
    FastAPI,
    HTTPException,
    Session,
    TestClient,
    create_engine,
    select,
    status,
)
from backend.app.database import init_db
from backend.app.models import Property, Room, User, generate_invite_code
from backend.app.schemas import (
    PropertyCreate,
    PropertyOut,
    RoomCreate,
    RoomOut,
    SystemConfigUpdate,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from backend.app.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestSecurityAndCrypto(unittest.TestCase):
    """Test password hashing, verification, and JWT token lifecycle."""

    def test_password_hashing_produces_unique_hashes(self) -> None:
        """Salts must be cryptographically random; distinct hashes for identical passwords."""
        pw = "superSecretPassword123!"
        hash1 = get_password_hash(pw)
        hash2 = get_password_hash(pw)

        self.assertNotEqual(hash1, hash2, "Identical passwords must have distinct salts/hashes.")
        self.assertTrue(hash1.startswith("pbkdf2_sha256$"))
        self.assertTrue(hash2.startswith("pbkdf2_sha256$"))

    def test_verify_password_correct_and_incorrect(self) -> None:
        """verify_password must return True only for matching passwords."""
        pw = "correctHorseBatteryStaple"
        hashed = get_password_hash(pw)

        self.assertTrue(verify_password(pw, hashed))
        self.assertFalse(verify_password("wrongPassword", hashed))
        self.assertFalse(verify_password("", hashed))
        self.assertFalse(verify_password(pw, ""))
        self.assertFalse(verify_password(pw, "corrupted$hash$value"))

    def test_verify_password_rejects_empty_and_tampered_inputs(self) -> None:
        """verify_password must safely return False on malformed or empty inputs."""
        self.assertFalse(verify_password("pw", "pbkdf2_sha256$notanint$salt$hash"))
        self.assertFalse(verify_password("pw", "invalid_format"))
        self.assertFalse(verify_password("", ""))

    def test_get_password_hash_type_validation(self) -> None:
        """Non-string inputs to get_password_hash must raise TypeError."""
        with self.assertRaises(TypeError):
            get_password_hash(12345)  # type: ignore[arg-type]

    def test_create_and_decode_access_token(self) -> None:
        """Access token must encode data, sign HS256, and decode back accurately."""
        data = {"sub": "landlord_user", "user_id": 42, "role": "landlord"}
        token = create_access_token(data)

        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3, "JWT must contain 3 dot-separated parts.")

        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "landlord_user")
        self.assertEqual(payload.get("user_id"), 42)
        self.assertEqual(payload.get("role"), "landlord")
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    def test_expired_token_is_rejected(self) -> None:
        """Token with an expiration time in the past must decode to None."""
        data = {"sub": "expired_user", "user_id": 10, "role": "tenant"}
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-10))

        payload = decode_access_token(expired_token)
        self.assertIsNone(payload, "Expired token must be rejected and return None.")

    def test_forged_and_tampered_tokens_are_rejected(self) -> None:
        """Any tampering with header, payload, or signature must invalidate the token."""
        data = {"sub": "legit_user", "user_id": 1, "role": "tenant"}
        valid_token = create_access_token(data)
        parts = valid_token.split(".")

        # Tamper payload (part 1)
        tampered_token = f"{parts[0]}.eyJob2NrcmVkIjogdHJ1ZX0.{parts[2]}"
        self.assertIsNone(decode_access_token(tampered_token))

        # Tamper signature (part 2)
        tampered_sig_token = f"{parts[0]}.{parts[1]}.badSignatureHere123"
        self.assertIsNone(decode_access_token(tampered_sig_token))

        # Malformed format (only 2 parts or empty)
        self.assertIsNone(decode_access_token(f"{parts[0]}.{parts[1]}"))
        self.assertIsNone(decode_access_token(""))
        self.assertIsNone(decode_access_token("completely_random_garbage"))
        self.assertIsNone(decode_access_token(None))  # type: ignore[arg-type]

    def test_verify_password_pbkdf2_malformed_parts_rejected(self) -> None:
        """Malformed PBKDF2 strings must be rejected without falling through to legacy format."""
        self.assertFalse(verify_password("pw", "pbkdf2_sha256$100000$salt$hash$extra"))
        self.assertFalse(verify_password("pw", "pbkdf2_sha256$only_two"))
        self.assertFalse(verify_password("pw", "pbkdf2_sha256$notanint$salt$hash"))

    def test_decode_access_token_custom_exp_and_nbf(self) -> None:
        """create_access_token respects custom exp and decode_access_token validates nbf."""
        custom_exp = int(datetime.now(timezone.utc).timestamp()) + 3600
        token = create_access_token({"sub": "user1", "exp": custom_exp})
        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["exp"], custom_exp)

        # Future not-before (nbf) token must be rejected
        future_nbf = int(datetime.now(timezone.utc).timestamp()) + 600
        nbf_token = create_access_token({"sub": "future_user", "nbf": future_nbf})
        self.assertIsNone(decode_access_token(nbf_token))

    def test_decode_access_token_non_dict_payload(self) -> None:
        """Token with non-dictionary JSON payload must be rejected."""
        import base64
        import hashlib
        import hmac
        import json
        header = {"alg": "HS256", "typ": "JWT"}
        h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        p_b64 = base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode()).decode().rstrip("=")
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        sig = hmac.new(b"tro-secret-key-super-secure-olp-pmnm-2026-minh-bach-dien-nuoc", signing_input, hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        bad_token = f"{h_b64}.{p_b64}.{sig_b64}"
        self.assertIsNone(decode_access_token(bad_token))


class TestAuthAndRBAC(unittest.TestCase):
    """Test registration, login, authorization dependencies, and room invite code lifecycle."""

    def setUp(self) -> None:
        """Set up fresh SQLite database in temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_auth.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_register_landlord_success(self) -> None:
        """Registering a landlord persists user with role 'landlord' and hashed password."""
        with Session(self.engine) as session:
            reg_data = UserRegister(
                username="landlord_john",
                password="secretPassword123",
                full_name="John Landlord",
                phone="0901112222",
                role="landlord",
            )
            result = register(reg_data, session=session)

            self.assertEqual(result.username, "landlord_john")
            self.assertEqual(result.role, "landlord")
            self.assertEqual(result.full_name, "John Landlord")
            self.assertEqual(result.phone, "0901112222")
            self.assertIsNotNone(result.id)

            # Verify in database: password must be hashed, not plaintext
            db_user = session.get(User, result.id)
            self.assertIsNotNone(db_user)
            self.assertNotEqual(db_user.hashed_password, "secretPassword123")
            self.assertTrue(verify_password("secretPassword123", db_user.hashed_password))
            self.assertTrue(db_user.is_landlord)
            self.assertFalse(db_user.is_tenant)

    def test_register_tenant_without_invite_code(self) -> None:
        """Registering a tenant without invite code creates an unassigned tenant."""
        with Session(self.engine) as session:
            reg_data = UserRegister(
                username="tenant_mary",
                password="tenantPassword456",
                full_name="Mary Tenant",
                phone="0903334444",
                role="tenant",
            )
            result = register(reg_data, session=session)

            self.assertEqual(result.username, "tenant_mary")
            self.assertEqual(result.role, "tenant")
            db_user = session.get(User, result.id)
            self.assertTrue(db_user.is_tenant)
            self.assertFalse(db_user.is_landlord)

    def test_register_duplicate_username_fails(self) -> None:
        """Attempting to register an existing username must raise HTTP 400 Bad Request."""
        with Session(self.engine) as session:
            reg_data = UserRegister(
                username="duplicate_user",
                password="password123",
                role="landlord",
            )
            register(reg_data, session=session)

            # Second attempt with same username
            with self.assertRaises(HTTPException) as ctx:
                register(reg_data, session=session)
            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already registered", ctx.exception.detail)

    def test_register_invalid_role_fails_validation(self) -> None:
        """UserRegister schema must reject invalid roles other than landlord or tenant."""
        with self.assertRaises(ValueError):
            UserRegister(
                username="hacker",
                password="password123",
                role="superadmin",
            )

    def test_login_success_and_token_generation(self) -> None:
        """Successful login returns a TokenResponse with valid JWT token containing user identity."""
        with Session(self.engine) as session:
            # Register user
            register(
                UserRegister(
                    username="login_test_user",
                    password="validPassword789",
                    full_name="Login Tester",
                    role="landlord",
                ),
                session=session,
            )

            # Attempt valid login
            token_resp = login(
                UserLogin(username="login_test_user", password="validPassword789"),
                session=session,
            )
            self.assertIsInstance(token_resp, TokenResponse)
            self.assertEqual(token_resp.token_type, "bearer")
            self.assertEqual(token_resp.username, "login_test_user")
            self.assertEqual(token_resp.role, "landlord")
            self.assertIsNotNone(token_resp.user_id)

            # Decode token and verify claims
            claims = decode_access_token(token_resp.access_token)
            self.assertIsNotNone(claims)
            self.assertEqual(claims.get("sub"), "login_test_user")
            self.assertEqual(claims.get("role"), "landlord")
            self.assertEqual(claims.get("user_id"), token_resp.user_id)

    def test_login_wrong_password_rejected(self) -> None:
        """Login with incorrect password raises HTTP 401 Unauthorized."""
        with Session(self.engine) as session:
            register(
                UserRegister(
                    username="wrong_pw_user",
                    password="correctPassword",
                    role="tenant",
                ),
                session=session,
            )

            with self.assertRaises(HTTPException) as ctx:
                login(
                    UserLogin(username="wrong_pw_user", password="incorrectPassword"),
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn("Incorrect username or password", ctx.exception.detail)

    def test_login_nonexistent_user_rejected(self) -> None:
        """Login with non-existent username raises HTTP 401 Unauthorized."""
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as ctx:
                login(
                    UserLogin(username="ghost_user", password="anyPassword"),
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user_valid_token(self) -> None:
        """get_current_user resolves User from Bearer authorization header or token param."""
        with Session(self.engine) as session:
            registered = register(
                UserRegister(
                    username="token_user",
                    password="password123",
                    role="tenant",
                ),
                session=session,
            )

            token = create_access_token({"sub": "token_user", "user_id": registered.id, "role": "tenant"})

            # Pass token via authorization header
            resolved_user = get_current_user(
                authorization=f"Bearer {token}",
                session=session,
            )
            self.assertEqual(resolved_user.id, registered.id)
            self.assertEqual(resolved_user.username, "token_user")

            # Pass token directly via token argument
            resolved_user2 = get_current_user(
                token=token,
                session=session,
            )
            self.assertEqual(resolved_user2.id, registered.id)

    def test_get_current_user_expired_or_forged_token_fails(self) -> None:
        """get_current_user raises HTTP 401 on expired or forged tokens."""
        with Session(self.engine) as session:
            # Expired token
            expired_tok = create_access_token(
                {"sub": "someone", "user_id": 1, "role": "tenant"},
                expires_delta=timedelta(seconds=-30),
            )
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(authorization=f"Bearer {expired_tok}", session=session)
            self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)

            # Forged token
            forged_tok = "invalid.bearer.token"
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(authorization=f"Bearer {forged_tok}", session=session)
            self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)

            # Missing credentials
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(session=session)
            self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rbac_require_landlord_and_require_tenant(self) -> None:
        """require_landlord and require_tenant enforce role boundaries with HTTP 403."""
        landlord = User(username="ll", hashed_password="pw", role="landlord")
        tenant = User(username="tt", hashed_password="pw", role="tenant")

        # Landlord accessing landlord endpoint -> OK
        self.assertEqual(require_landlord(landlord).username, "ll")

        # Tenant accessing landlord endpoint -> HTTP 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            require_landlord(tenant)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("landlord", ctx.exception.detail.lower())

        # Tenant accessing tenant endpoint -> OK
        self.assertEqual(require_tenant(tenant).username, "tt")

        # Landlord accessing tenant endpoint -> HTTP 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            require_tenant(landlord)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("tenant", ctx.exception.detail.lower())

    def test_room_invite_code_auto_assignment_and_lifecycle(self) -> None:
        """Comprehensive room invite code lifecycle:
        1. Room created with unique invite_code, status='empty', tenant_id=None.
        2. New tenant registers with valid invite_code -> automatically assigned to room, status='active'.
        3. Landlord removes tenant -> room vacated, status='empty', invite_code automatically rotated.
        4. Old invite_code rejected.
        5. Next tenant registers with NEW invite_code -> successfully assigned to room.
        """
        with Session(self.engine) as session:
            # Step 1: Create Landlord, Property, and Room
            ll = register(
                UserRegister(username="host_boss", password="pw123456", role="landlord"),
                session=session,
            )
            prop = Property(name="Khu Trọ An Cư", landlord_id=ll.id)
            session.add(prop)
            session.commit()

            room_code_1 = generate_invite_code(8)
            room = Room(
                room_number="P101",
                property_id=prop.id,
                invite_code=room_code_1,
                status="empty",
            )
            session.add(room)
            session.commit()
            room_id = room.id
            self.assertEqual(room.status, "empty")
            self.assertIsNone(room.tenant_id)

            # Step 2: Tenant 1 registers with valid invite_code
            tenant1 = register(
                UserRegister(
                    username="tenant_one",
                    password="pwTenant1",
                    role="tenant",
                    invite_code=room_code_1,
                ),
                session=session,
            )
            self.assertEqual(tenant1.role, "tenant")

            # Room must now be active with tenant_one assigned
            refreshed_room = session.get(Room, room_id)
            self.assertEqual(refreshed_room.status, "active")
            self.assertEqual(refreshed_room.tenant_id, tenant1.id)

            # Step 3: Landlord removes tenant from room
            landlord_user = session.get(User, ll.id)
            vacated_room = remove_tenant_from_room(
                room_id=room_id,
                current_user=landlord_user,
                session=session,
            )
            self.assertEqual(vacated_room.status, "empty")
            self.assertIsNone(vacated_room.tenant_id)
            new_code = vacated_room.invite_code
            self.assertNotEqual(new_code, room_code_1, "Invite code must be refreshed upon tenant removal.")
            self.assertEqual(len(new_code), 8)

            # Step 4: Attempting to register with old invite code must fail with HTTP 404
            with self.assertRaises(HTTPException) as ctx:
                register(
                    UserRegister(
                        username="intruder",
                        password="password123",
                        role="tenant",
                        invite_code=room_code_1,
                    ),
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn("Invalid invite code", ctx.exception.detail)

            # Step 5: Tenant 2 registers with NEW invite code -> succeeds
            tenant2 = register(
                UserRegister(
                    username="tenant_two",
                    password="pwTenant2",
                    role="tenant",
                    invite_code=new_code,
                ),
                session=session,
            )
            refreshed_room2 = session.get(Room, room_id)
            self.assertEqual(refreshed_room2.status, "active")
            self.assertEqual(refreshed_room2.tenant_id, tenant2.id)

    def test_tenant_cannot_remove_tenant_from_room(self) -> None:
        """A tenant role user is prohibited from removing a tenant from a room (HTTP 403)."""
        with Session(self.engine) as session:
            tenant_user = User(username="rogue_tenant", hashed_password="pw", role="tenant")
            session.add(tenant_user)
            session.commit()

            room = Room(room_number="P999", status="active", tenant_id=tenant_user.id)
            session.add(room)
            session.commit()

            with self.assertRaises(HTTPException) as ctx:
                remove_tenant_from_room(
                    room_id=room.id,
                    current_user=tenant_user,
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_tenant_nonexistent_room_returns_404(self) -> None:
        """Attempting to remove tenant from non-existent room raises HTTP 404."""
        with Session(self.engine) as session:
            landlord = User(username="admin_boss", hashed_password="pw", role="landlord")
            session.add(landlord)
            session.commit()

            with self.assertRaises(HTTPException) as ctx:
                remove_tenant_from_room(
                    room_id=999999,
                    current_user=landlord,
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_schemas_data_models_and_validation(self) -> None:
        """Test schemas instantiation, defaults, and validation."""
        # Property schemas
        p_create = PropertyCreate(name="Khu Tro Test", address="123 Duong Test", landlord_id=1)
        self.assertEqual(p_create.name, "Khu Tro Test")
        p_out = PropertyOut(id=10, name="Khu Tro Test", address="123 Duong Test", landlord_id=1)
        self.assertEqual(p_out.id, 10)

        # Room schemas
        r_create = RoomCreate(room_number="101", property_id=10, current_people_count=2)
        self.assertEqual(r_create.room_number, "101")
        self.assertEqual(r_create.status, "empty")
        r_out = RoomOut(
            id=5,
            room_number="101",
            property_id=10,
            invite_code="CODE1234",
            status="active",
            current_people_count=2,
            tenant_id=7,
        )
        self.assertEqual(r_out.tenant_id, 7)

        # SystemConfigUpdate schema
        cfg_up = SystemConfigUpdate(
            electricity_vat_rate=0.10,
            electricity_tier3_price=2450.0,
            water_pricing_type="PER_PERSON",
            water_unit_price=80000.0,
        )
        self.assertEqual(cfg_up.water_pricing_type, "PER_PERSON")
        self.assertEqual(cfg_up.electricity_vat_rate, 0.10)

        # Invalid water_pricing_type rejected
        with self.assertRaises(ValueError):
            SystemConfigUpdate(water_pricing_type="INVALID_TYPE")

    def test_api_router_end_to_end_via_test_client(self) -> None:
        """End-to-end HTTP integration tests via TestClient."""
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with Session(self.engine) as session:
            # 1. Register Landlord via HTTP POST
            reg_resp = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "api_landlord",
                    "password": "apiPassword123",
                    "full_name": "API Landlord",
                    "role": "landlord",
                },
                session=session,
            )
            self.assertEqual(reg_resp.status_code, 201)
            self.assertEqual(reg_resp.json()["username"], "api_landlord")
            self.assertEqual(reg_resp.json()["role"], "landlord")

            # 2. Login Landlord via HTTP POST
            login_resp = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "api_landlord",
                    "password": "apiPassword123",
                },
                session=session,
            )
            self.assertEqual(login_resp.status_code, 200)
            token_data = login_resp.json()
            access_token = token_data["access_token"]
            self.assertIsNotNone(access_token)

            # 3. Access GET /me with Bearer token
            me_resp = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
                session=session,
            )
            self.assertEqual(me_resp.status_code, 200)
            self.assertEqual(me_resp.json()["username"], "api_landlord")

            # 4. Access GET /me without token -> 401
            unauth_resp = client.get("/api/v1/auth/me", session=session)
            self.assertEqual(unauth_resp.status_code, 401)

            # 5. Create room in DB for invite test
            room = Room(room_number="API-101", status="empty")
            session.add(room)
            session.commit()
            invite_code = room.invite_code

            # 6. Register Tenant with invite_code via HTTP POST
            tenant_reg = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "api_tenant",
                    "password": "apiTenantPassword",
                    "role": "tenant",
                    "invite_code": invite_code,
                },
                session=session,
            )
            self.assertEqual(tenant_reg.status_code, 201)

            # Verify room is active in DB
            db_room = session.get(Room, room.id)
            self.assertEqual(db_room.status, "active")
            self.assertEqual(db_room.tenant_id, tenant_reg.json()["id"])

            # 7. Landlord vacates room via POST /rooms/{id}/remove-tenant
            vacate_resp = client.post(
                f"/api/v1/auth/rooms/{room.id}/remove-tenant",
                headers={"Authorization": f"Bearer {access_token}"},
                session=session,
            )
            self.assertEqual(vacate_resp.status_code, 200)
            vacated_data = vacate_resp.json()
            self.assertEqual(vacated_data["status"], "empty")
            self.assertIsNone(vacated_data["tenant_id"])
            self.assertNotEqual(vacated_data["invite_code"], invite_code)

    def test_get_current_user_lowercase_bearer_scheme(self) -> None:
        """get_current_user resolves user with lowercase 'bearer <token>' authorization header."""
        with Session(self.engine) as session:
            u = register(
                UserRegister(username="lower_bearer_user", password="password123", role="tenant"),
                session=session,
            )
            tok = create_access_token({"sub": "lower_bearer_user", "user_id": u.id, "role": "tenant"})
            resolved = get_current_user(
                authorization=f"bearer {tok}",
                session=session,
            )
            self.assertEqual(resolved.id, u.id)
            self.assertEqual(resolved.username, "lower_bearer_user")

    def test_register_tenant_with_already_occupied_room_rejected(self) -> None:
        """Attempting to register with invite code of an already occupied room must raise HTTP 400."""
        with Session(self.engine) as session:
            # Create room and first tenant
            ll = register(UserRegister(username="ll_occupy", password="password123", role="landlord"), session=session)
            prop = Property(name="Tro A", landlord_id=ll.id)
            session.add(prop)
            session.commit()

            room = Room(room_number="101", property_id=prop.id, status="empty")
            session.add(room)
            session.commit()
            code = room.invite_code

            # First tenant registers into room
            t1 = register(UserRegister(username="tenant_first", password="password123", role="tenant", invite_code=code), session=session)
            db_room = session.get(Room, room.id)
            self.assertEqual(db_room.status, "active")
            self.assertEqual(db_room.tenant_id, t1.id)

            # Second tenant attempts to use same invite code while room is occupied
            with self.assertRaises(HTTPException) as ctx:
                register(UserRegister(username="tenant_second", password="password123", role="tenant", invite_code=code), session=session)
            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already occupied", ctx.exception.detail)

            # Confirm original tenant was not displaced
            db_room_after = session.get(Room, room.id)
            self.assertEqual(db_room_after.tenant_id, t1.id)
            self.assertEqual(db_room_after.status, "active")

    def test_register_tenant_with_whitespace_invite_code(self) -> None:
        """Registering with whitespace-only invite code succeeds as unassigned tenant."""
        with Session(self.engine) as session:
            t = register(
                UserRegister(username="ws_code_user", password="password123", role="tenant", invite_code="   "),
                session=session,
            )
            self.assertEqual(t.username, "ws_code_user")
            self.assertEqual(t.role, "tenant")

    def test_remove_tenant_cross_landlord_property_forbidden(self) -> None:
        """Landlord A cannot remove tenant from room belonging to Landlord B (HTTP 403)."""
        with Session(self.engine) as session:
            ll_owner = register(UserRegister(username="ll_owner", password="password123", role="landlord"), session=session)
            ll_attacker = register(UserRegister(username="ll_attacker", password="password123", role="landlord"), session=session)
            prop = Property(name="Prop Owner", landlord_id=ll_owner.id)
            session.add(prop)
            session.commit()

            room = Room(room_number="202", property_id=prop.id, status="active")
            session.add(room)
            session.commit()

            attacker_user = session.get(User, ll_attacker.id)
            with self.assertRaises(HTTPException) as ctx:
                remove_tenant_from_room(
                    room_id=room.id,
                    current_user=attacker_user,
                    session=session,
                )
            self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("not authorized", ctx.exception.detail)

    def test_remove_tenant_standalone_room_without_property(self) -> None:
        """Landlord can remove tenant from a standalone room with property_id=None."""
        with Session(self.engine) as session:
            ll = register(UserRegister(username="ll_standalone", password="password123", role="landlord"), session=session)
            t = register(UserRegister(username="t_standalone", password="password123", role="tenant"), session=session)
            room = Room(room_number="303", property_id=None, status="active", tenant_id=t.id)
            session.add(room)
            session.commit()

            landlord_user = session.get(User, ll.id)
            vacated = remove_tenant_from_room(
                room_id=room.id,
                current_user=landlord_user,
                session=session,
            )
            self.assertEqual(vacated.status, "empty")
            self.assertIsNone(vacated.tenant_id)

    def test_room_create_with_tenant_id_schema(self) -> None:
        """RoomCreate schema accepts optional tenant_id."""
        rc = RoomCreate(room_number="404", tenant_id=12)
        self.assertEqual(rc.tenant_id, 12)


if __name__ == "__main__":
    unittest.main()
