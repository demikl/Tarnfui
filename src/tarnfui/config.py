"""Configuration module for Tarnfui.

This module handles the configuration of Tarnfui through environment variables.
"""
import os

from pydantic import BaseModel, Field, validator


class TarnfuiConfig(BaseModel):
    """Configuration class for Tarnfui.

    Attributes:
        shutdown_time: Time to shut down deployments in 24-hour format (HH:MM).
        startup_time: Time to start up deployments in 24-hour format (HH:MM).
        active_days: List of days when the cluster should be active (0-6, where 0 is Monday).
    """
    shutdown_time: str = Field(default="19:00", env="TARNFUI_SHUTDOWN_TIME")
    startup_time: str = Field(default="07:00", env="TARNFUI_STARTUP_TIME")
    active_days: list[int] = Field(
        default=[0, 1, 2, 3, 4], env="TARNFUI_ACTIVE_DAYS")
    reconciliation_interval: int = Field(
        default=60, env="TARNFUI_RECONCILIATION_INTERVAL")
    namespace: str | None = Field(default=None, env="TARNFUI_NAMESPACE")

    @validator("shutdown_time", "startup_time")
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

    @validator("active_days")
    def validate_active_days(cls, v):
        """Validate active days are between 0-6"""
        if not all(0 <= day <= 6 for day in v):
            raise ValueError("Active days must be between 0-6 (Monday-Sunday)")
        return sorted(v)

    @classmethod
    def from_env(cls):
        """Create a config instance from environment variables."""
        shutdown_time = os.getenv("TARNFUI_SHUTDOWN_TIME", "19:00")
        startup_time = os.getenv("TARNFUI_STARTUP_TIME", "07:00")

        active_days_str = os.getenv("TARNFUI_ACTIVE_DAYS", "0,1,2,3,4")
        try:
            active_days = [int(day) for day in active_days_str.split(",")]
        except ValueError:
            active_days = [0, 1, 2, 3, 4]  # Default to weekdays

        reconciliation_interval = int(
            os.getenv("TARNFUI_RECONCILIATION_INTERVAL", "60"))
        namespace = os.getenv("TARNFUI_NAMESPACE")

        return cls(
            shutdown_time=shutdown_time,
            startup_time=startup_time,
            active_days=active_days,
            reconciliation_interval=reconciliation_interval,
            namespace=namespace,
        )
