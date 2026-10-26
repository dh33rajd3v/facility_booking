"""SQLAlchemy table definitions (the single source of truth for the schema).

Every change here must have a matching Alembic migration in ``alembic/versions``;
``tests/test_migrations.py`` fails if the two drift apart.

Constraint names are written out explicitly so the models and migrations always agree.
"""

from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Allowed values, shared by models, migrations and seed data.
GROUPS = ("LHC", "AUDITORIUM", "SPORTS")
SECTIONS = ("ACADEMIC", "SPORTS")
CATEGORIES = ("PRIVATE", "GOVT", "IIT")
UNITS = ("FULL_DAY", "HALF_DAY", "PER_DAY", "THREE_HOUR")
HALVES = ("FIRST", "SECOND")


def in_list(column: str, values: tuple[str, ...]) -> str:
    """SQL text for a CHECK constraint like ``section IN ('ACADEMIC','SPORTS')``."""
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Facility(TimestampMixin, Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    # "group" is an SQL keyword, so the column is called facility_group (exposed as "group" in the API).
    facility_group: Mapped[str] = mapped_column(String(20))
    section: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())

    slot_types: Mapped[list["FacilitySlotType"]] = relationship(
        back_populates="facility", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_facilities_code"),
        CheckConstraint(in_list("facility_group", GROUPS), name="ck_facilities_group_valid"),
        CheckConstraint(in_list("section", SECTIONS), name="ck_facilities_section_valid"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_facilities_capacity_positive"),
        Index("ix_facilities_active_group", "active", "facility_group"),
    )


class FacilitySlotType(Base):
    """Which booking units a facility supports (the Auditorium supports two)."""

    __tablename__ = "facility_slot_types"

    facility_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_type: Mapped[str] = mapped_column(String(20), primary_key=True)

    facility: Mapped[Facility] = relationship(back_populates="slot_types")

    __table_args__ = (
        ForeignKeyConstraint(
            ["facility_id"], ["facilities.id"], name="fk_facility_slot_types_facility_id", ondelete="CASCADE"
        ),
        CheckConstraint(in_list("slot_type", UNITS), name="ck_facility_slot_types_slot_type_valid"),
    )


class Tariff(TimestampMixin, Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(Integer)  # whole rupees; 0 means "No charges"
    display_label: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())

    __table_args__ = (
        ForeignKeyConstraint(["facility_id"], ["facilities.id"], name="fk_tariffs_facility_id"),
        # A tariff can only exist for a unit the facility actually supports.
        ForeignKeyConstraint(
            ["facility_id", "unit"],
            ["facility_slot_types.facility_id", "facility_slot_types.slot_type"],
            name="fk_tariffs_facility_unit",
        ),
        UniqueConstraint("facility_id", "category", "unit", "version", name="uq_tariffs_version"),
        CheckConstraint(in_list("category", CATEGORIES), name="ck_tariffs_category_valid"),
        CheckConstraint("amount >= 0", name="ck_tariffs_amount_non_negative"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="ck_tariffs_effective_range"
        ),
        Index("ix_tariffs_lookup", "facility_id", "category", "unit", "active", "effective_from"),
    )


class SlotWindow(Base):
    __tablename__ = "slot_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int] = mapped_column(Integer)
    slot_type: Mapped[str] = mapped_column(String(20))
    slot_key: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    half: Mapped[str | None] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())

    __table_args__ = (
        ForeignKeyConstraint(["facility_id"], ["facilities.id"], name="fk_slot_windows_facility_id"),
        ForeignKeyConstraint(
            ["facility_id", "slot_type"],
            ["facility_slot_types.facility_id", "facility_slot_types.slot_type"],
            name="fk_slot_windows_facility_slot_type",
        ),
        UniqueConstraint("facility_id", "slot_key", name="uq_slot_windows_facility_slot"),
        CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) OR (start_time < end_time)",
            name="ck_slot_windows_time_range",
        ),
        CheckConstraint("half IS NULL OR " + in_list("half", HALVES), name="ck_slot_windows_half_valid"),
    )
