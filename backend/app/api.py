# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""RESTful API router for properties, rooms, meter readings, invoices, and dynamic pricing."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from .auth import get_current_user, require_landlord, require_tenant
from .compat import APIRouter, Depends, HTTPException, Session, select, status
from .database import get_session
from .models import Invoice, MeterReading, Property, Room, SystemConfig, User
from .schemas import (
    AssignTenantRequest,
    InvoiceCalculateRequest,
    InvoiceOut,
    MeterReadingCreate,
    MeterReadingOut,
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
    RoomCreate,
    RoomJoinRequest,
    RoomOut,
    SystemConfigOut,
    SystemConfigUpdate,
    TenantRoomOut,
)
from core.calculator import (
    calculate_consumption,
    calculate_dispute,
    calculate_electricity_tier3,
    calculate_electricity_tiered,
    calculate_quota,
    calculate_water,
)
from core.models import WaterPricingType

router = APIRouter(prefix="/api/v1", tags=["api"])


# ============================================================================
# Authorization & Room Access Verification Helpers
# ============================================================================


def _verify_room_landlord_access(
    room_id: int, user: User, session: Session
) -> Tuple[Room, Optional[Property]]:
    """Verify room existence and landlord authorization."""
    if not user.is_landlord:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Landlord privilege required",
        )
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {room_id} not found",
        )
    prop = None
    if room.property_id is not None:
        prop = session.get(Property, room.property_id)
        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with id {room.property_id} not found",
            )
        if prop.landlord_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this room",
            )
    return room, prop


def _verify_room_read_access(
    room_id: int, user: User, session: Session
) -> Tuple[Room, Optional[Property]]:
    """Verify room existence and read authorization for landlord or assigned tenant."""
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {room_id} not found",
        )
    prop = None
    if room.property_id is not None:
        prop = session.get(Property, room.property_id)
        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with id {room.property_id} not found",
            )

    if user.is_landlord:
        if prop is not None and prop.landlord_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this room's property",
            )
    elif user.is_tenant:
        if room.tenant_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this room",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized role",
        )
    return room, prop


def _enrich_room_out(room: Room, session: Session) -> RoomOut:
    """Enrich Room entity with tenant and property/landlord metadata for output."""
    tenant_name: Optional[str] = None
    tenant_phone: Optional[str] = None
    if room.tenant_id is not None:
        tenant = session.get(User, room.tenant_id)
        if tenant:
            tenant_name = tenant.full_name or tenant.username
            tenant_phone = tenant.phone

    prop_name: Optional[str] = None
    prop_address: Optional[str] = None
    landlord_name: Optional[str] = None
    landlord_phone: Optional[str] = None

    if room.property_id is not None:
        prop = session.get(Property, room.property_id)
        if prop:
            prop_name = prop.name
            prop_address = prop.address
            if prop.landlord_id is not None:
                landlord = session.get(User, prop.landlord_id)
                if landlord:
                    landlord_name = landlord.full_name or landlord.username
                    landlord_phone = landlord.phone

    return RoomOut(
        id=room.id,
        room_number=room.room_number,
        property_id=room.property_id,
        invite_code=room.invite_code,
        status=room.status,
        current_people_count=room.current_people_count,
        tenant_id=room.tenant_id,
        tenant_name=tenant_name,
        tenant_phone=tenant_phone,
        property_name=prop_name,
        property_address=prop_address,
        landlord_name=landlord_name,
        landlord_phone=landlord_phone,
    )


# ============================================================================
# Properties (Khu trọ) Endpoints
# ============================================================================


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> PropertyOut:
    """Create a new rental property managed by the current landlord."""
    cleaned_name = property_data.name.strip()
    if not cleaned_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property name cannot be empty or whitespace",
        )
    prop = Property(
        name=cleaned_name,
        address=property_data.address.strip() if property_data.address else None,
        landlord_id=current_user.id,
        tariff_type=property_data.tariff_type or "statutory",
        custom_elec_rate=property_data.custom_elec_rate,
        custom_water_rate=property_data.custom_water_rate,
        custom_water_type=property_data.custom_water_type or "PER_M3",
    )
    session.add(prop)
    session.commit()
    session.refresh(prop)
    return PropertyOut.model_validate(prop)


@router.get("/properties", response_model=List[PropertyOut])
def list_properties(
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> List[PropertyOut]:
    """List all properties owned by the authenticated landlord."""
    statement = select(Property).where(Property.landlord_id == current_user.id).order_by(Property.id.asc())
    props = session.exec(statement).all()
    return [PropertyOut.model_validate(p) for p in props]


@router.get("/properties/{id}", response_model=PropertyOut)
def get_property(
    id: int,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> PropertyOut:
    """Retrieve details of a specific property owned by the landlord."""
    prop = session.get(Property, id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with id {id} not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this property",
        )
    return PropertyOut.model_validate(prop)


@router.put("/properties/{id}", response_model=PropertyOut)
def update_property(
    id: int,
    property_data: PropertyUpdate,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> PropertyOut:
    """Update details and tariff configuration of a specific property owned by the landlord."""
    prop = session.get(Property, id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with id {id} not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit this property",
        )
    if property_data.name is not None:
        cleaned_name = property_data.name.strip()
        if not cleaned_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Property name cannot be empty or whitespace",
            )
        prop.name = cleaned_name
    if property_data.address is not None:
        prop.address = property_data.address.strip() if property_data.address else None
    if property_data.tariff_type is not None:
        prop.tariff_type = property_data.tariff_type
    if property_data.custom_elec_rate is not None:
        prop.custom_elec_rate = property_data.custom_elec_rate
    if property_data.custom_water_rate is not None:
        prop.custom_water_rate = property_data.custom_water_rate
    if property_data.custom_water_type is not None:
        prop.custom_water_type = property_data.custom_water_type

    session.add(prop)
    session.commit()
    session.refresh(prop)
    return PropertyOut.model_validate(prop)


# ============================================================================
# Rooms (Phòng trọ) Endpoints
# ============================================================================


@router.post(
    "/properties/{property_id}/rooms",
    response_model=RoomOut,
    status_code=status.HTTP_201_CREATED,
)
def create_room(
    property_id: int,
    room_data: RoomCreate,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Create a new room in a property managed by the landlord."""
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with id {property_id} not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this property",
        )

    cleaned_number = room_data.room_number.strip()
    if not cleaned_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room number cannot be empty or whitespace",
        )

    # Check duplicate room number within property
    existing = session.exec(
        select(Room).where(
            Room.property_id == property_id,
            Room.room_number == cleaned_number,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room '{cleaned_number}' already exists in property {property_id}",
        )

    room = Room(
        room_number=cleaned_number,
        property_id=property_id,
        current_people_count=room_data.current_people_count,
        status=room_data.status or "empty",
    )
    if room_data.invite_code:
        room.invite_code = room_data.invite_code
    if room_data.tenant_id:
        room.assign_tenant(room_data.tenant_id)

    session.add(room)
    session.commit()
    session.refresh(room)
    return _enrich_room_out(room, session)


@router.get("/properties/{property_id}/rooms", response_model=List[RoomOut])
def list_rooms_in_property(
    property_id: int,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> List[RoomOut]:
    """List all rooms belonging to a property managed by the landlord."""
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with id {property_id} not found",
        )
    if prop.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this property",
        )

    rooms = session.exec(
        select(Room).where(Room.property_id == property_id).order_by(Room.room_number.asc())
    ).all()
    return [_enrich_room_out(r, session) for r in rooms]


@router.get("/tenant/rooms", response_model=List[RoomOut])
@router.get("/rooms/my", response_model=List[RoomOut])
def get_tenant_rooms(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[RoomOut]:
    """Retrieve all rooms currently assigned to the authenticated user."""
    statement = select(Room).where(Room.tenant_id == current_user.id).order_by(Room.id.asc())
    rooms = session.exec(statement).all()
    return [_enrich_room_out(r, session) for r in rooms]


@router.get("/rooms/{id}", response_model=RoomOut)
def get_room(
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Retrieve details for a specific room (accessible by landlord or assigned tenant)."""
    room, _ = _verify_room_read_access(id, current_user, session)
    return _enrich_room_out(room, session)


@router.post(
    "/properties/{property_id}/rooms/{room_id}/assign-tenant",
    response_model=RoomOut,
)
@router.post(
    "/rooms/{room_id}/assign-tenant",
    response_model=RoomOut,
)
def assign_tenant_to_room(
    room_id: int,
    property_id: Optional[int] = None,
    assign_data: Optional[AssignTenantRequest] = None,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Assign a tenant directly to a room via username or phone number (Landlord only)."""
    room, prop = _verify_room_landlord_access(room_id, current_user, session)
    if property_id is not None:
        try:
            pid = int(property_id)
        except (ValueError, TypeError):
            pid = property_id
        if room.property_id != pid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id} does not belong to property {property_id}",
            )

    if not assign_data or (not assign_data.username and not assign_data.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either username or phone must be provided to assign tenant",
        )

    tenant: Optional[User] = None
    if assign_data.username:
        clean_user = assign_data.username.strip().lstrip("@")
        tenant = session.exec(
            select(User).where(User.username == clean_user)
        ).first()
        if not tenant:
            tenant = session.exec(
                select(User).where(User.phone == clean_user)
            ).first()
    elif assign_data.phone:
        clean_phone = assign_data.phone.strip()
        tenant = session.exec(
            select(User).where(User.phone == clean_phone)
        ).first()
        if not tenant:
            tenant = session.exec(
                select(User).where(User.username == clean_phone)
            ).first()

    if not tenant:
        identifier = assign_data.username or assign_data.phone
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant account '{identifier}' not found",
        )

    if tenant.role != "tenant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{tenant.username}' does not have tenant role (role is '{tenant.role}')",
        )

    room.assign_tenant(tenant.id)
    session.add(room)
    session.commit()
    session.refresh(room)

    return _enrich_room_out(room, session)


@router.post(
    "/properties/{property_id}/rooms/{room_id}/remove-tenant",
    response_model=RoomOut,
)
@router.post(
    "/rooms/{room_id}/remove-tenant",
    response_model=RoomOut,
)
def remove_tenant_from_room(
    room_id: int,
    property_id: Optional[int] = None,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Landlord removes a tenant from a room, resets status to 'empty', and regenerates invite code."""
    room, prop = _verify_room_landlord_access(room_id, current_user, session)
    if property_id is not None:
        try:
            pid = int(property_id)
        except (ValueError, TypeError):
            pid = property_id
        if room.property_id != pid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {room_id} does not belong to property {property_id}",
            )

    room.remove_tenant()
    session.add(room)
    session.commit()
    session.refresh(room)
    return _enrich_room_out(room, session)


@router.post("/rooms/join", response_model=RoomOut)
def join_room(
    join_data: RoomJoinRequest,
    current_user: User = Depends(require_tenant),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Associate authenticated tenant with a room using its invite code."""
    cleaned_code = join_data.invite_code.strip().upper()
    room = session.exec(select(Room).where(Room.invite_code == cleaned_code)).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid invite code: '{cleaned_code}'. Room not found.",
        )

    if room.tenant_id == current_user.id:
        return _enrich_room_out(room, session)

    if room.tenant_id is not None or room.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room with invite code '{cleaned_code}' is already occupied.",
        )

    room.assign_tenant(current_user.id)
    session.add(room)
    session.commit()
    session.refresh(room)

    return _enrich_room_out(room, session)


# ============================================================================
# Meter Readings (Chỉ số công tơ) Endpoints
# ============================================================================


@router.post(
    "/rooms/{room_id}/readings",
    response_model=MeterReadingOut,
    status_code=status.HTTP_201_CREATED,
)
def record_meter_reading(
    room_id: int,
    reading_data: MeterReadingCreate,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> MeterReadingOut:
    """Record monthly electricity and water start and end meter readings for a room."""
    _verify_room_landlord_access(room_id, current_user, session)

    cleaned_month = reading_data.month_year.strip()
    if not cleaned_month:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month_year cannot be empty",
        )

    existing = session.exec(
        select(MeterReading).where(
            MeterReading.room_id == room_id,
            MeterReading.month_year == cleaned_month,
        )
    ).first()

    if existing:
        existing.elec_start = float(reading_data.elec_start)
        existing.elec_end = float(reading_data.elec_end)
        existing.water_start = float(reading_data.water_start)
        existing.water_end = float(reading_data.water_end)
        existing.recorded_at = datetime.now(timezone.utc)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return MeterReadingOut.model_validate(existing)

    reading = MeterReading(
        room_id=room_id,
        month_year=cleaned_month,
        elec_start=float(reading_data.elec_start),
        elec_end=float(reading_data.elec_end),
        water_start=float(reading_data.water_start),
        water_end=float(reading_data.water_end),
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return MeterReadingOut.model_validate(reading)


@router.get("/rooms/{room_id}/readings", response_model=List[MeterReadingOut])
def list_meter_readings(
    room_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[MeterReadingOut]:
    """Retrieve all recorded meter readings for a room ordered by month."""
    _verify_room_read_access(room_id, current_user, session)
    readings = session.exec(
        select(MeterReading).where(MeterReading.room_id == room_id).order_by(MeterReading.month_year.desc())
    ).all()
    return [MeterReadingOut.model_validate(r) for r in readings]


# ============================================================================
# Invoices (Tính tiền & Sinh hóa đơn) Endpoints
# ============================================================================


@router.post(
    "/rooms/{room_id}/invoices/calculate",
    response_model=InvoiceOut,
    status_code=status.HTTP_201_CREATED,
)
def calculate_and_generate_invoice(
    room_id: int,
    calc_data: InvoiceCalculateRequest,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> InvoiceOut:
    """Calculate utility bills using core calculator engine, compare dispute, and persist invoice."""
    room, prop = _verify_room_landlord_access(room_id, current_user, session)

    cleaned_month = calc_data.month_year.strip()
    if not cleaned_month:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month_year cannot be empty",
        )

    # 1. Resolve meter readings
    elec_start: Optional[float] = calc_data.elec_start
    elec_end: Optional[float] = calc_data.elec_end
    water_start: Optional[float] = calc_data.water_start
    water_end: Optional[float] = calc_data.water_end

    # If reading_id is explicitly passed, fetch and validate it
    if calc_data.reading_id is not None:
        reading = session.get(MeterReading, calc_data.reading_id)
        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meter reading with id {calc_data.reading_id} not found",
            )
        if reading.room_id != room_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Meter reading {calc_data.reading_id} does not belong to room {room_id}",
            )
        if elec_start is None:
            elec_start = reading.elec_start
        if elec_end is None:
            elec_end = reading.elec_end
        if water_start is None:
            water_start = reading.water_start
        if water_end is None:
            water_end = reading.water_end

    # If readings remain missing, look up recorded MeterReading by room_id and month_year
    if (
        elec_start is None
        or elec_end is None
        or (water_start is None and water_end is None and calc_data.water_usage is None)
    ):
        reading = session.exec(
            select(MeterReading).where(
                MeterReading.room_id == room_id,
                MeterReading.month_year == cleaned_month,
            )
        ).first()

        if reading:
            if elec_start is None:
                elec_start = reading.elec_start
            if elec_end is None:
                elec_end = reading.elec_end
            if water_start is None:
                water_start = reading.water_start
            if water_end is None:
                water_end = reading.water_end

    if elec_start is None or elec_end is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No meter reading found for room {room_id} and month {cleaned_month}. Provide readings in request or record them first.",
        )

    # 2. Retrieve dynamic pricing system configuration
    sys_config = session.get(SystemConfig, 1)
    if not sys_config:
        sys_config = session.exec(select(SystemConfig)).first()
    if not sys_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System pricing configuration is uninitialized",
        )

    elec_cfg = sys_config.to_electricity_config()
    water_cfg = sys_config.to_water_config()

    try:
        # 3. Calculate electricity consumption with rollover handling
        max_m = Decimal(str(calc_data.max_meter if calc_data.max_meter is not None else 99999.0))
        elec_consumption = calculate_consumption(elec_start, elec_end, max_meter=max_m)

        # 4. Check whether room has registered quota or falls back to flat Tier 3 per TT 60/2025
        has_quota = calc_data.has_registered_quota
        if has_quota is None:
            if calc_data.registered_quota is not None:
                has_quota = calc_data.registered_quota
            elif calc_data.use_tier3 is not None:
                has_quota = not calc_data.use_tier3
            else:
                has_quota = room.current_people_count > 0

        people_count = room.current_people_count
        if calc_data.people_count is not None:
            people_count = calc_data.people_count

        if has_quota:
            p_count = people_count if people_count > 0 else 1
            quota = calculate_quota(p_count)
            elec_result = calculate_electricity_tiered(
                consumption=elec_consumption,
                quota=quota,
                config=elec_cfg,
            )
        else:
            elec_result = calculate_electricity_tier3(
                consumption=elec_consumption,
                config=elec_cfg,
            )

        # 5. Calculate water billing (PER_M3 with rollover, or PER_PERSON)
        if calc_data.water_usage is not None:
            water_usage = Decimal(str(calc_data.water_usage))
        elif water_cfg.pricing_type == WaterPricingType.PER_PERSON:
            water_usage = Decimal(str(people_count))
        else:
            w_start = water_start if water_start is not None else 0.0
            w_end = water_end if water_end is not None else 0.0
            water_usage = calculate_consumption(w_start, w_end, max_meter=max_m)

        water_result = calculate_water(usage=water_usage, config=water_cfg)

        # 6. Statutory total & dispute calculation
        total_statutory = elec_result.total_amount + water_result.total_amount
        user_actual = (
            calc_data.actual_collected
            if calc_data.actual_collected is not None
            else calc_data.actual_collected_amount
        )
        if user_actual is not None:
            actual_collected = Decimal(str(user_actual))
        elif prop and getattr(prop, "tariff_type", None) == "custom" and getattr(prop, "custom_elec_rate", None) is not None:
            c_elec = Decimal(str(elec_result.consumption_kwh)) * Decimal(str(prop.custom_elec_rate))
            if getattr(prop, "custom_water_type", "PER_M3") == "PER_PERSON":
                c_water = Decimal(str(people_count)) * Decimal(str(prop.custom_water_rate or 0.0))
            else:
                c_water = Decimal(str(water_result.usage)) * Decimal(str(prop.custom_water_rate or 0.0))
            actual_collected = c_elec + c_water
        else:
            actual_collected = total_statutory

        dispute_result = calculate_dispute(
            calculated_total=total_statutory,
            actual_collected=actual_collected,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid calculation parameter: {str(exc)}",
        )

    # 7. Construct detailed breakdown json enriched with room, meter readings, and property information
    breakdown_data: Dict[str, Any] = {
        "room_id": room.id,
        "room_number": room.room_number,
        "property_id": room.property_id,
        "property_name": prop.name if prop else None,
        "property_address": prop.address if prop else None,
        "property_tariff": {
            "tariff_type": getattr(prop, "tariff_type", "statutory") if prop else "statutory",
            "custom_elec_rate": getattr(prop, "custom_elec_rate", None) if prop else None,
            "custom_water_rate": getattr(prop, "custom_water_rate", None) if prop else None,
            "custom_water_type": getattr(prop, "custom_water_type", "PER_M3") if prop else "PER_M3",
        },
        "meter_reading": {
            "elec_start": float(elec_start) if elec_start is not None else 0.0,
            "elec_end": float(elec_end) if elec_end is not None else 0.0,
            "water_start": float(water_start) if water_start is not None else 0.0,
            "water_end": float(water_end) if water_end is not None else 0.0,
        },
        "electricity": {
            "method": elec_result.method,
            "consumption_kwh": float(elec_result.consumption_kwh),
            "quota": float(elec_result.quota),
            "pre_tax_amount": float(elec_result.pre_tax_amount),
            "vat_amount": float(elec_result.vat_amount),
            "total_amount": float(elec_result.total_amount),
            "tiers": [
                {
                    "tier_number": t.tier_number,
                    "threshold_applied": float(t.threshold_applied) if t.threshold_applied is not None else None,
                    "kwh_used": float(t.kwh_used),
                    "unit_price": float(t.unit_price),
                    "amount": float(t.amount),
                }
                for t in elec_result.breakdown
            ],
        },
        "water": {
            "pricing_type": water_cfg.pricing_type.value if hasattr(water_cfg.pricing_type, "value") else str(water_cfg.pricing_type),
            "usage": float(water_result.usage),
            "unit_price": float(water_cfg.unit_price),
            "pre_tax_amount": float(water_result.pre_tax_amount),
            "vat_amount": float(water_result.vat_amount),
            "env_fee_amount": float(water_result.env_fee_amount),
            "total_amount": float(water_result.total_amount),
        },
        "dispute": {
            "calculated_amount": float(dispute_result.calculated_amount),
            "actual_amount": float(dispute_result.actual_amount),
            "diff_amount": float(dispute_result.diff_amount),
            "is_overcharged": bool(dispute_result.is_overcharged),
        },
    }

    invoice = Invoice(
        room_id=room_id,
        month_year=cleaned_month,
        elec_kwh=float(elec_result.consumption_kwh),
        elec_amount=float(elec_result.total_amount),
        water_usage=float(water_result.usage),
        water_amount=float(water_result.total_amount),
        total_statutory_amount=float(total_statutory),
        actual_collected_amount=float(actual_collected),
        diff_amount=float(dispute_result.diff_amount),
        status="draft",
    )
    invoice.set_breakdown(breakdown_data)

    session.add(invoice)
    session.commit()
    session.refresh(invoice)

    return InvoiceOut.model_validate(invoice)


@router.post("/invoices/{id}/publish", response_model=InvoiceOut)
def publish_invoice(
    id: int,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> InvoiceOut:
    """Publish a draft invoice and notify tenant (Landlord only)."""
    invoice = session.get(Invoice, id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {id} not found",
        )
    _verify_room_landlord_access(invoice.room_id, current_user, session)
    invoice.status = "published"
    invoice.published_at = datetime.now(timezone.utc)
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return InvoiceOut.model_validate(invoice)


@router.get("/rooms/{room_id}/invoices", response_model=List[InvoiceOut])
def list_invoices_for_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[InvoiceOut]:
    """List all invoices generated for a specific room.

    Landlords can view all invoices (including drafts).
    Tenants can view all invoices for their assigned room (client filters to published).
    """
    _verify_room_read_access(room_id, current_user, session)
    statement = (
        select(Invoice)
        .where(Invoice.room_id == room_id)
        .order_by(Invoice.month_year.desc(), Invoice.id.desc())
    )
    invoices = session.exec(statement).all()
    return [InvoiceOut.model_validate(inv) for inv in invoices]


@router.get("/invoices/{id}", response_model=InvoiceOut)
def get_invoice(
    id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InvoiceOut:
    """Retrieve full details of an invoice (accessible by landlord or room tenant)."""
    invoice = session.get(Invoice, id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {id} not found",
        )

    _verify_room_read_access(invoice.room_id, current_user, session)
    return InvoiceOut.model_validate(invoice)


# ============================================================================
# Public Share Portal (Tính năng 17 - Tra cứu công khai)
# ============================================================================


@router.get("/invoices/public/{share_token}", response_model=InvoiceOut)
def get_public_invoice(
    share_token: str,
    session: Session = Depends(get_session),
) -> InvoiceOut:
    """Public lookup endpoint allowing anyone with share_token or short_code to inspect invoice and breakdown without authentication."""
    decoded = unquote(share_token).strip()
    cleaned_token = decoded.lstrip("#").strip()
    if not cleaned_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice with empty share token not found",
        )
    invoice = session.exec(
        select(Invoice).where(
            (Invoice.share_token == cleaned_token)
            | (Invoice.short_code == cleaned_token.upper())
            | (Invoice.share_token == cleaned_token.lower())
        )
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with share token '{share_token}' not found",
        )
    return InvoiceOut.model_validate(invoice)


# ============================================================================
# Dynamic System Pricing Configuration (/config)
# ============================================================================


@router.get("/config", response_model=SystemConfigOut)
def get_system_config(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SystemConfigOut:
    """Retrieve active system pricing configuration (VAT, tiers, water rates)."""
    config = session.get(SystemConfig, 1)
    if not config:
        config = session.exec(select(SystemConfig)).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System pricing configuration not initialized",
        )
    return SystemConfigOut.model_validate(config)


@router.put("/config", response_model=SystemConfigOut)
def update_system_config(
    update_data: SystemConfigUpdate,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> SystemConfigOut:
    """Update dynamic electricity and water pricing configuration (Landlord privilege required)."""
    config = session.get(SystemConfig, 1)
    if not config:
        config = session.exec(select(SystemConfig)).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System pricing configuration not initialized",
        )

    if update_data.electricity_vat_rate is not None:
        config.electricity_vat_rate = float(update_data.electricity_vat_rate)
    if update_data.electricity_tier3_price is not None:
        config.electricity_tier3_price = float(update_data.electricity_tier3_price)
    if update_data.tiers is not None:
        config.set_tiers(update_data.tiers)
    elif update_data.tiers_json is not None:
        config.tiers_json = update_data.tiers_json

    if update_data.water_pricing_type is not None:
        config.water_pricing_type = update_data.water_pricing_type
    if update_data.water_unit_price is not None:
        config.water_unit_price = float(update_data.water_unit_price)
    if update_data.water_vat_rate is not None:
        config.water_vat_rate = float(update_data.water_vat_rate)
    if update_data.water_env_fee_rate is not None:
        config.water_env_fee_rate = float(update_data.water_env_fee_rate)

    session.add(config)
    session.commit()
    session.refresh(config)
    return SystemConfigOut.model_validate(config)


# ============================================================================
# Notifications API
# ============================================================================


@router.get("/notifications")
def get_notifications(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[Dict[str, Any]]:
    """Retrieve in-app notifications for the authenticated user.

    - Tenant: sees only published invoices for their rooms, newest first, max 20.
    - Landlord: sees all invoices (draft + published) for all their rooms, newest first, max 20.
      Each notification includes room_number and property_name for clarity.
    """
    notifs = []

    if current_user.is_tenant:
        my_rooms = session.exec(
            select(Room).where(Room.tenant_id == current_user.id)
        ).all()
        room_map = {r.id: r for r in my_rooms if r.id is not None}
        if room_map:
            invs = session.exec(
                select(Invoice)
                .where(
                    Invoice.room_id.in_(list(room_map.keys())),
                    Invoice.status == "published",
                )
                .order_by(Invoice.created_at.desc())
            ).all()
            for inv in invs[:20]:
                r = room_map.get(inv.room_id)
                room_label = f"Phòng {r.room_number}" if r else f"Phòng #{inv.room_id}"
                notifs.append({
                    "id": f"inv_{inv.id}",
                    "type": "invoice_published",
                    "title": f"Hóa đơn tháng {inv.month_year} — {room_label}",
                    "message": (
                        f"{room_label}: Tổng tiền {int(inv.total_statutory_amount):,} đ. "
                        f"Mã tra cứu: {inv.short_code or str(inv.id)}"
                    ),
                    "timestamp": (inv.published_at or inv.created_at).isoformat()
                    if (inv.published_at or inv.created_at)
                    else None,
                    "share_token": inv.share_token,
                    "short_code": inv.short_code,
                    "invoice_id": inv.id,
                    "read": False,
                })

    elif current_user.is_landlord:
        props = session.exec(
            select(Property).where(Property.landlord_id == current_user.id)
        ).all()
        prop_map = {p.id: p for p in props if p.id is not None}
        if prop_map:
            rooms = session.exec(
                select(Room).where(Room.property_id.in_(list(prop_map.keys())))
            ).all()
            room_map = {r.id: r for r in rooms if r.id is not None}
            if room_map:
                invs = session.exec(
                    select(Invoice)
                    .where(Invoice.room_id.in_(list(room_map.keys())))
                    .order_by(Invoice.created_at.desc())
                ).all()
                for inv in invs[:20]:
                    r = room_map.get(inv.room_id)
                    prop = prop_map.get(r.property_id) if r and r.property_id else None
                    room_label = f"Phòng {r.room_number}" if r else f"Phòng #{inv.room_id}"
                    prop_label = f" — {prop.name}" if prop else ""
                    is_published = inv.status == "published"
                    status_label = "Đã phát hành" if is_published else "Bản nháp"
                    notifs.append({
                        "id": f"inv_{inv.id}",
                        "type": "invoice_published" if is_published else "invoice_draft",
                        "title": f"Hóa đơn {inv.month_year} [{status_label}]{prop_label}",
                        "message": (
                            f"{room_label}: {int(inv.total_statutory_amount):,} đ — "
                            f"Mã: {inv.short_code or str(inv.id)}"
                        ),
                        "timestamp": (inv.published_at or inv.created_at).isoformat()
                        if (inv.published_at or inv.created_at)
                        else None,
                        "share_token": inv.share_token,
                        "short_code": inv.short_code,
                        "invoice_id": inv.id,
                        "read": False,
                    })

    return notifs
