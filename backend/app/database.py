# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Database engine, session management, and initialization for tro backend."""

import os
from typing import Any, Generator, Optional
from .compat import SQLModel, Session, create_engine, select
from .models import (
    DEFAULT_TIERS_JSON,
    Invoice,
    MeterReading,
    Property,
    Room,
    SystemConfig,
    User,
)

# Database file configuration
DEFAULT_DB_FILE = "tro.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


def get_session(custom_engine: Optional[Any] = None) -> Generator[Session, None, None]:
    """Dependency injection generator producing a database session for FastAPI."""
    target_engine = custom_engine or engine
    with Session(target_engine) as session:
        yield session


def init_db(target_engine: Optional[Any] = None) -> None:
    """Initialize database tables and seed default pricing configuration if empty."""
    db_engine = target_engine or engine
    SQLModel.metadata.create_all(db_engine)

    with Session(db_engine) as session:
        config = session.get(SystemConfig, 1)
        if config is None:
            statement = select(SystemConfig)
            existing = session.exec(statement).first()
            if existing is None:
                default_config = SystemConfig(
                    id=1,
                    electricity_vat_rate=0.08,
                    electricity_tier3_price=2380.0,
                    tiers_json=DEFAULT_TIERS_JSON,
                    water_pricing_type="PER_M3",
                    water_unit_price=8500.0,
                    water_vat_rate=0.05,
                    water_env_fee_rate=0.10,
                )
                session.add(default_config)
                session.commit()
