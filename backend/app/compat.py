# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Compatibility layer providing SQLModel interface with SQLite fallback.

If sqlmodel is installed, standard sqlmodel exports are re-exported.
If not, a lightweight Pydantic v2 + sqlite3 engine is provided with identical API.
"""

from datetime import datetime, timezone
import json
import os
import sqlite3
import sys
import types
from typing import Any, Callable, ClassVar, Dict, Generator, List, Optional, Set, Type, Union, get_args, get_origin
import pydantic
from pydantic import BaseModel, ConfigDict
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

try:
    import sqlmodel
    from sqlmodel import SQLModel, Field, Session, create_engine, select, col
    SQLMODEL_INSTALLED = True
except ImportError:
    SQLMODEL_INSTALLED = False

    _TABLE_REGISTRY: Dict[str, Type["SQLModel"]] = {}

    class ColumnOrdering:
        """Represents column ordering (ASC or DESC)."""
        def __init__(self, col: str, is_desc: bool = False):
            self.col = col
            self.is_desc = is_desc

    class BinaryCondition:
        """Represents a SQL comparison condition."""
        def __init__(self, col: str, op: str, value: Any):
            self.col = col
            self.op = op
            self.value = value

        def __and__(self, other: Any) -> "CompoundCondition":
            return CompoundCondition("AND", [self, other])

        def __or__(self, other: Any) -> "CompoundCondition":
            return CompoundCondition("OR", [self, other])

    class CompoundCondition:
        """Represents logical conjunction (AND / OR) of conditions."""
        def __init__(self, op: str, conditions: List[Any]):
            self.op = op
            self.conditions = conditions

        def __and__(self, other: Any) -> "CompoundCondition":
            return CompoundCondition("AND", [self, other])

        def __or__(self, other: Any) -> "CompoundCondition":
            return CompoundCondition("OR", [self, other])

    class ColumnAttribute:
        """Column proxy returned during class attribute access for query building."""
        def __init__(self, name: str, field_info: Any):
            self.name = name
            self.field_info = field_info

        def __eq__(self, other: Any) -> BinaryCondition:  # type: ignore[override]
            return BinaryCondition(self.name, "=", other)

        def __ne__(self, other: Any) -> BinaryCondition:  # type: ignore[override]
            return BinaryCondition(self.name, "!=", other)

        def __lt__(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "<", other)

        def __le__(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "<=", other)

        def __gt__(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, ">", other)

        def __ge__(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, ">=", other)

        def in_(self, values: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "IN", list(values))

        def not_in(self, values: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "NOT IN", list(values))

        def like(self, pattern: str) -> BinaryCondition:
            return BinaryCondition(self.name, "LIKE", pattern)

        def is_(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "=", other)

        def is_not(self, other: Any) -> BinaryCondition:
            return BinaryCondition(self.name, "!=", other)

        def desc(self) -> ColumnOrdering:
            return ColumnOrdering(self.name, is_desc=True)

        def asc(self) -> ColumnOrdering:
            return ColumnOrdering(self.name, is_desc=False)

    def col(attribute: Any) -> Any:
        return attribute

    class SQLModelMetaclass(type(BaseModel)):
        """Metaclass intercepting class-level column access for query expressions."""
        def __getattr__(cls, name: str) -> Any:
            if name.startswith("_") or name in ("metadata", "model_config", "model_fields"):
                raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")
            fields = cls.__dict__.get("__pydantic_fields__")
            if fields is None:
                for base in cls.__mro__:
                    if "__pydantic_fields__" in base.__dict__:
                        fields = base.__dict__["__pydantic_fields__"]
                        break
            if fields and name in fields:
                return ColumnAttribute(name, fields[name])
            raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")

    def _get_field_meta(field_info: Any, key: str, default: Any = None) -> Any:
        """Extract metadata from FieldInfo or its json_schema_extra."""
        if hasattr(field_info, key):
            return getattr(field_info, key)
        extra = getattr(field_info, "json_schema_extra", None)
        if isinstance(extra, dict):
            return extra.get(key, default)
        return default

    def Field(
        default: Any = PydanticUndefined,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        primary_key: bool = False,
        foreign_key: Optional[str] = None,
        unique: bool = False,
        index: bool = False,
        **kwargs: Any,
    ) -> Any:
        """SQLModel-compatible Field with database column metadata."""
        extra = kwargs.pop("json_schema_extra", {})
        if not isinstance(extra, dict):
            extra = {}
        extra.update({
            "primary_key": primary_key,
            "foreign_key": foreign_key,
            "unique": unique,
            "index": index,
        })
        if default_factory is not None:
            return pydantic.Field(default_factory=default_factory, json_schema_extra=extra, **kwargs)
        elif default is not PydanticUndefined:
            return pydantic.Field(default=default, json_schema_extra=extra, **kwargs)
        else:
            return pydantic.Field(json_schema_extra=extra, **kwargs)

    class Metadata:
        """Table schema generator and executor for SQLite."""
        def create_all(self, engine: "Engine") -> None:
            conn = engine.get_connection()
            cursor = conn.cursor()
            for tablename, model_cls in _TABLE_REGISTRY.items():
                cols: List[str] = []
                fk_clauses: List[str] = []

                for fname, finfo in model_cls.model_fields.items():
                    is_pk = _get_field_meta(finfo, "primary_key", False)
                    sql_type = _python_type_to_sqlite(finfo.annotation)
                    col_def = f"{fname} {sql_type}"

                    if is_pk:
                        col_def += " PRIMARY KEY"
                        if sql_type == "INTEGER":
                            col_def += " AUTOINCREMENT"
                    elif _get_field_meta(finfo, "unique", False):
                        col_def += " UNIQUE"
                    cols.append(col_def)

                    fk = _get_field_meta(finfo, "foreign_key", None)
                    if fk:
                        target_table, target_col = fk.split(".")
                        fk_clauses.append(f"FOREIGN KEY ({fname}) REFERENCES {target_table}({target_col})")

                all_defs = cols + fk_clauses
                sql = f"CREATE TABLE IF NOT EXISTS {tablename} (\n  " + ",\n  ".join(all_defs) + "\n);"
                cursor.execute(sql)

                for fname, finfo in model_cls.model_fields.items():
                    if _get_field_meta(finfo, "index", False) and not _get_field_meta(finfo, "primary_key", False):
                        idx_sql = f"CREATE INDEX IF NOT EXISTS idx_{tablename}_{fname} ON {tablename} ({fname});"
                        cursor.execute(idx_sql)

            conn.commit()
            if engine._shared_conn is None:
                conn.close()

    class SQLModel(BaseModel, metaclass=SQLModelMetaclass):
        """Base SQLModel supporting Pydantic validation and SQLite table mapping."""
        model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
        metadata: ClassVar[Metadata] = Metadata()

        @classmethod
        def __init_subclass__(cls, table: bool = False, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            cls.__is_table__ = table
            if table:
                if not hasattr(cls, "__tablename__"):
                    cls.__tablename__ = cls.__name__.lower()
                _TABLE_REGISTRY[cls.__tablename__] = cls

    def _python_type_to_sqlite(ann: Any) -> str:
        origin = get_origin(ann)
        is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
        if is_union:
            args = [a for a in get_args(ann) if a is not type(None)]
            if args:
                ann = args[0]
        if ann in (int,):
            return "INTEGER"
        if ann in (float,):
            return "REAL"
        if ann in (bool,):
            return "INTEGER"
        return "TEXT"

    class Select:
        """Select query builder."""
        def __init__(self, model_cls: Type[SQLModel]):
            self.model_cls = model_cls
            self.conditions: List[Any] = []
            self.order_bys: List[Any] = []
            self._limit: Optional[int] = None
            self._offset: Optional[int] = None

        def where(self, *conditions: Any) -> "Select":
            self.conditions.extend(conditions)
            return self

        def order_by(self, *cols: Any) -> "Select":
            self.order_bys.extend(cols)
            return self

        def limit(self, limit: int) -> "Select":
            self._limit = limit
            return self

        def offset(self, offset: int) -> "Select":
            self._offset = offset
            return self

    def select(model_cls: Type[SQLModel]) -> Select:
        return Select(model_cls)

    class ExecResult:
        """Query execution result wrapper."""
        def __init__(self, items: List[Any]):
            self._items = items

        def all(self) -> List[Any]:
            return list(self._items)

        def first(self) -> Optional[Any]:
            return self._items[0] if self._items else None

        def one_or_none(self) -> Optional[Any]:
            if not self._items:
                return None
            if len(self._items) > 1:
                raise ValueError("Multiple rows were found when one or none was expected")
            return self._items[0]

        def __iter__(self):
            return iter(self._items)

        def __len__(self):
            return len(self._items)

    class Engine:
        """Database connection provider."""
        def __init__(self, url: str, echo: bool = False, connect_args: Optional[Dict[str, Any]] = None):
            self.url = url
            self.echo = echo
            self.connect_args = connect_args or {}

            if url.startswith("sqlite:///"):
                self.db_path = url[len("sqlite:///"):]
            elif url == "sqlite://" or url == "sqlite:///:memory:":
                self.db_path = ":memory:"
            else:
                self.db_path = url

            self._shared_conn: Optional[sqlite3.Connection] = None
            if self.db_path == ":memory:":
                self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row

        def get_connection(self) -> sqlite3.Connection:
            if self._shared_conn is not None:
                return self._shared_conn
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=self.connect_args.get("check_same_thread", True)
            )
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA foreign_keys = ON;")
            except Exception:
                pass
            return conn

    def create_engine(url: str, echo: bool = False, connect_args: Optional[Dict[str, Any]] = None) -> Engine:
        return Engine(url, echo=echo, connect_args=connect_args)

    class Session:
        """Database session executing operations against SQLite."""
        def __init__(self, engine: Engine):
            self.engine = engine
            self.conn = engine.get_connection()
            self._new_objects: List[Any] = []
            self._deleted_objects: List[Any] = []
            self._is_active = True

        def __enter__(self) -> "Session":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            if exc_type is not None:
                self.rollback()
            self.close()

        def add(self, obj: Any) -> None:
            if obj in self._deleted_objects:
                self._deleted_objects.remove(obj)
            if obj not in self._new_objects:
                self._new_objects.append(obj)

        def delete(self, obj: Any) -> None:
            if obj in self._new_objects:
                self._new_objects.remove(obj)
            if obj not in self._deleted_objects:
                self._deleted_objects.append(obj)

        def commit(self) -> None:
            cursor = self.conn.cursor()

            # Handle deletes
            for obj in self._deleted_objects:
                tablename = obj.__tablename__
                pk_col = _get_primary_key(obj.__class__)
                pk_val = getattr(obj, pk_col, None)
                if pk_val is not None:
                    cursor.execute(f'DELETE FROM "{tablename}" WHERE "{pk_col}" = ?', (pk_val,))
            self._deleted_objects.clear()

            # Handle adds / updates
            for obj in self._new_objects:
                if obj in self._deleted_objects:
                    continue
                tablename = obj.__tablename__
                pk_col = _get_primary_key(obj.__class__)
                pk_val = getattr(obj, pk_col, None)

                data: Dict[str, Any] = {}
                for fname in obj.__class__.model_fields.keys():
                    val = getattr(obj, fname, None)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    elif isinstance(val, bool):
                        val = 1 if val else 0
                    data[fname] = val

                exists = False
                if pk_val is not None:
                    cursor.execute(f'SELECT 1 FROM "{tablename}" WHERE "{pk_col}" = ?', (pk_val,))
                    exists = cursor.fetchone() is not None

                if exists:
                    update_cols = [f'"{k}" = ?' for k in data.keys() if k != pk_col]
                    params = [data[k] for k in data.keys() if k != pk_col] + [pk_val]
                    if update_cols:
                        cursor.execute(f'UPDATE "{tablename}" SET {", ".join(update_cols)} WHERE "{pk_col}" = ?', params)
                else:
                    if pk_val is None:
                        insert_data = {k: v for k, v in data.items() if k != pk_col}
                    else:
                        insert_data = data
                    cols = list(insert_data.keys())
                    placeholders = ["?"] * len(cols)
                    quoted_cols = [f'"{c}"' for c in cols]
                    params = [insert_data[c] for c in cols]
                    sql = f'INSERT INTO "{tablename}" ({", ".join(quoted_cols)}) VALUES ({", ".join(placeholders)})'
                    cursor.execute(sql, params)
                    if pk_val is None and pk_col:
                        setattr(obj, pk_col, cursor.lastrowid)

            self._new_objects.clear()
            self.conn.commit()

        def rollback(self) -> None:
            self.conn.rollback()
            self._new_objects.clear()
            self._deleted_objects.clear()

        def close(self) -> None:
            if self._is_active:
                self._is_active = False
                if self.engine._shared_conn is None:
                    self.conn.close()

        def refresh(self, obj: Any) -> None:
            tablename = obj.__tablename__
            pk_col = _get_primary_key(obj.__class__)
            pk_val = getattr(obj, pk_col, None)
            if pk_val is not None:
                cursor = self.conn.cursor()
                cursor.execute(f'SELECT * FROM "{tablename}" WHERE "{pk_col}" = ?', (pk_val,))
                row = cursor.fetchone()
                if row:
                    for k in row.keys():
                        val = _deserialize_val(obj.__class__, k, row[k])
                        setattr(obj, k, val)

        def get(self, model_cls: Type[SQLModel], pk_val: Any) -> Optional[Any]:
            pk_col = _get_primary_key(model_cls)
            for obj in self._deleted_objects:
                if isinstance(obj, model_cls) and getattr(obj, pk_col, None) == pk_val:
                    return None
            for obj in self._new_objects:
                if isinstance(obj, model_cls) and getattr(obj, pk_col, None) == pk_val:
                    return obj
            tablename = model_cls.__tablename__
            cursor = self.conn.cursor()
            cursor.execute(f'SELECT * FROM "{tablename}" WHERE "{pk_col}" = ?', (pk_val,))
            row = cursor.fetchone()
            if not row:
                return None
            return _instantiate_model(model_cls, row)

        def exec(self, select_stmt: Select) -> ExecResult:
            model_cls = select_stmt.model_cls
            tablename = model_cls.__tablename__

            sql = f'SELECT * FROM "{tablename}"'
            params: List[Any] = []

            def _render_condition(cond: Any) -> str:
                if isinstance(cond, CompoundCondition):
                    rendered = [_render_condition(c) for c in cond.conditions]
                    return f"({f' {cond.op} '.join(rendered)})"
                if isinstance(cond, BinaryCondition):
                    col_name = f'"{cond.col}"'
                    if cond.value is None:
                        if cond.op in ("=", "IS"):
                            return f"{col_name} IS NULL"
                        elif cond.op in ("!=", "<>", "IS NOT"):
                            return f"{col_name} IS NOT NULL"
                    if cond.op in ("IN", "NOT IN"):
                        vals = list(cond.value)
                        if not vals:
                            return "1=0" if cond.op == "IN" else "1=1"
                        placeholders = ",".join(["?"] * len(vals))
                        params.extend(vals)
                        return f"{col_name} {cond.op} ({placeholders})"
                    params.append(cond.value)
                    return f"{col_name} {cond.op} ?"
                return str(cond)

            if select_stmt.conditions:
                cond_clauses = [_render_condition(cond) for cond in select_stmt.conditions]
                sql += " WHERE " + " AND ".join(cond_clauses)

            if select_stmt.order_bys:
                order_clauses = []
                for o in select_stmt.order_bys:
                    if isinstance(o, ColumnOrdering):
                        direction = "DESC" if o.is_desc else "ASC"
                        order_clauses.append(f'"{o.col}" {direction}')
                    elif isinstance(o, ColumnAttribute):
                        order_clauses.append(f'"{o.name}" ASC')
                    elif isinstance(o, str):
                        order_clauses.append(o)
                if order_clauses:
                    sql += " ORDER BY " + ", ".join(order_clauses)

            if select_stmt._limit is not None:
                sql += f" LIMIT {int(select_stmt._limit)}"
            if select_stmt._offset is not None:
                sql += f" OFFSET {int(select_stmt._offset)}"

            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            items = [_instantiate_model(model_cls, r) for r in rows]
            return ExecResult(items)

    def _get_primary_key(model_cls: Type[SQLModel]) -> str:
        for fname, finfo in model_cls.model_fields.items():
            if _get_field_meta(finfo, "primary_key", False):
                return fname
        return "id"

    def _deserialize_val(model_cls: Type[SQLModel], field_name: str, raw_val: Any) -> Any:
        if raw_val is None:
            return None
        field_info = model_cls.model_fields.get(field_name)
        if not field_info:
            return raw_val
        ann = field_info.annotation
        origin = get_origin(ann)
        is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
        if is_union:
            args = [a for a in get_args(ann) if a is not type(None)]
            if args:
                ann = args[0]
        if ann is datetime and isinstance(raw_val, str):
            return datetime.fromisoformat(raw_val)
        if ann is bool and isinstance(raw_val, int):
            return bool(raw_val)
        return raw_val

    def _instantiate_model(model_cls: Type[SQLModel], row: sqlite3.Row) -> Any:
        d = {}
        for k in row.keys():
            d[k] = _deserialize_val(model_cls, k, row[k])
        return model_cls(**d)

    # Register virtual sqlmodel module in sys.modules so standard imports work everywhere
    mod = types.ModuleType("sqlmodel")
    mod.SQLModel = SQLModel
    mod.Field = Field
    mod.Session = Session
    mod.create_engine = create_engine
    mod.select = select
    mod.col = col
    sys.modules["sqlmodel"] = mod
