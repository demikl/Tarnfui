"""Configuration module for Tarnfui.

This module handles the configuration of Tarnfui through environment variables.
"""
import os
from enum import Enum
from typing import Union

import pytz
from pydantic import BaseModel, Field, field_validator


class Weekday(str, Enum):
    """Enumeration of weekdays using English abbreviations.

    This provides a more readable way to specify days compared to using integers.
    """
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"

    @classmethod
    def to_integer(cls, day: Union[str, "Weekday"]) -> int:
        """Convert a weekday abbreviation to its integer representation.

        Args:
            day: The weekday abbreviation or enum value.

        Returns:
            Integer representation (0-6, where 0 is Monday).
        """
        mapping = {
            cls.MON: 0,
            cls.TUE: 1,
            cls.WED: 2,
            cls.THU: 3,
            cls.FRI: 4,
            cls.SAT: 5,
            cls.SUN: 6,
        }
        return mapping[cls(day) if isinstance(day, str) else day]

    @classmethod
    def from_integer(cls, day_num: int) -> "Weekday":
        """Convert an integer day to its weekday abbreviation.

        Args:
            day_num: The integer day (0-6, where 0 is Monday).

        Returns:
            Weekday enum value.
        """
        mapping = {
            0: cls.MON,
            1: cls.TUE,
            2: cls.WED,
            3: cls.THU,
            4: cls.FRI,
            5: cls.SAT,
            6: cls.SUN,
        }
        if day_num not in mapping:
            raise ValueError("Day number must be between 0-6")
        return mapping[day_num]


class TarnfuiConfig(BaseModel):
    """Configuration class for Tarnfui.

    Attributes:
        shutdown_time: Time to shut down deployments in 24-hour format (HH:MM).
        startup_time: Time to start up deployments in 24-hour format (HH:MM).
        active_days: List of days when the cluster should be active (using Weekday enum).
        timezone: Timezone to use for time calculations.
    """
    shutdown_time: str = Field(default="19:00", env="TARNFUI_SHUTDOWN_TIME")
    startup_time: str = Field(default="07:00", env="TARNFUI_STARTUP_TIME")
    active_days: list[Weekday] = Field(
        default=[Weekday.MON, Weekday.TUE,
                 Weekday.WED, Weekday.THU, Weekday.FRI],
        env="TARNFUI_ACTIVE_DAYS"
    )
    timezone: str = Field(default="UTC", env="TARNFUI_TIMEZONE")
    reconciliation_interval: int = Field(
        default=60, env="TARNFUI_RECONCILIATION_INTERVAL")
    namespace: str | None = Field(default=None, env="TARNFUI_NAMESPACE")

    @field_validator("shutdown_time", "startup_time")
    def validate_time_format(cls, v):
        """Validate time format as HH:MM"""
        try:
            hour, minute = v.split(":")
            hour, minute = int(hour), int(minute)
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("Time must be in range 00:00-23:59")
        except ValueError:
            raise ValueError("Time must be in format HH:MM")
        return v

    @field_validator("timezone")
    def validate_timezone(cls, v):
        """Validate that the timezone is valid"""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {v}")
        return v

    @classmethod
    def from_env(cls):
        """Create a config instance from environment variables."""
        shutdown_time = os.getenv("TARNFUI_SHUTDOWN_TIME", "19:00")
        startup_time = os.getenv("TARNFUI_STARTUP_TIME", "07:00")
        timezone = os.getenv("TARNFUI_TIMEZONE", "UTC")

        active_days_str = os.getenv(
            "TARNFUI_ACTIVE_DAYS", "mon,tue,wed,thu,fri")
        try:
            active_days = [Weekday(day.lower())
                           for day in active_days_str.split(",")]
        except ValueError:
            active_days = [Weekday.MON, Weekday.TUE,
                           Weekday.WED, Weekday.THU, Weekday.FRI]

        reconciliation_interval = int(
            os.getenv("TARNFUI_RECONCILIATION_INTERVAL", "60"))
        namespace = os.getenv("TARNFUI_NAMESPACE")

        return cls(
            shutdown_time=shutdown_time,
            startup_time=startup_time,
            active_days=active_days,
            timezone=timezone,
            reconciliation_interval=reconciliation_interval,
            namespace=namespace,
        )
