"""Scheduler module for Tarnfui.

This module handles the scheduling of operations based on time of day and day of week.
"""

import datetime
import logging
import time

import pytz

from tarnfui.config import TarnfuiConfig, Weekday
from tarnfui.kubernetes import KubernetesClient

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for time-based operations.

    This class determines when to stop and start deployments based on configured times.
    """

    def __init__(self, config: TarnfuiConfig, kubernetes_client: KubernetesClient):
        """Initialize the scheduler.

        Args:
            config: The configuration for the scheduler.
            kubernetes_client: The Kubernetes client to use for operations.
        """
        self.config = config
        self.kubernetes_client = kubernetes_client
        self.timezone = pytz.timezone(config.timezone)

    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse a time string into a datetime.time object.

        Args:
            time_str: Time string in format HH:MM.

        Returns:
            The parsed time object.
        """
        hour, minute = map(int, time_str.split(":"))
        return datetime.time(hour=hour, minute=minute)

    def get_current_datetime(self) -> datetime.datetime:
        """Get the current datetime in the configured timezone.

        Returns:
            Current datetime in the configured timezone.
        """
        return datetime.datetime.now(self.timezone)

    def should_be_active(self) -> bool:
        """Determine if the cluster should be active based on current time and day.

        Returns:
            True if the cluster should be active, False otherwise.
        """
        now = self.get_current_datetime()
        current_day_num = now.weekday()  # 0 is Monday, 6 is Sunday
        current_time = now.time().replace(tzinfo=None)  # Remove tzinfo for comparison

        # Convert active_days enum values to integers for comparison
        active_day_nums = [Weekday.to_integer(day) for day in self.config.active_days]

        # Check if today is an active day
        if current_day_num not in active_day_nums:
            logger.info(f"Today (day {Weekday.from_integer(current_day_num)}) is not an active day")
            return False

        # Parse configured times
        shutdown_time = self._parse_time(self.config.shutdown_time)
        startup_time = self._parse_time(self.config.startup_time)

        # If shutdown is before startup, active hours are considered to be between startup and shutdown
        # Otherwise, it's active except between shutdown and startup
        if shutdown_time < startup_time:
            # Special case: shutdown is before startup (e.g., 19:00 to 07:00)
            if startup_time <= current_time < shutdown_time:
                logger.info(f"Current time {now} is within active hours")
                return True
            else:
                logger.info(f"Current time {now} is outside active hours")
                return False
        else:
            # Special case: shutdown is after startup (e.g., 07:00 to 19:00)
            if shutdown_time <= current_time or current_time < startup_time:
                logger.info(f"Current time {now} is outside active hours")
                return False
            else:
                logger.info(f"Current time {now} is within active hours")
                return True

    def reconcile(self) -> None:
        """Reconcile the cluster state based on the current time.

        This method is the main entry point for the scheduling logic, determining
        whether to stop or start deployments based on the current time.
        """
        should_be_active = self.should_be_active()

        if should_be_active:
            logger.info("Cluster should be active, starting deployments")
            self.kubernetes_client.start_deployments(self.config.namespace)
        else:
            logger.info("Cluster should be inactive, stopping deployments")
            self.kubernetes_client.stop_deployments(self.config.namespace)

    def run_reconciliation_loop(self) -> None:
        """Run the reconciliation loop continuously.

        This method runs in an infinite loop, periodically checking if deployments
        should be stopped or started based on the current time.
        """
        logger.info(f"Starting reconciliation loop with interval {self.config.reconciliation_interval} seconds")
        logger.info(f"Using timezone: {self.config.timezone}")
        logger.info(f"Active days: {', '.join(day.value for day in self.config.active_days)}")
        logger.info(f"Startup time: {self.config.startup_time}")
        logger.info(f"Shutdown time: {self.config.shutdown_time}")

        try:
            while True:
                logger.info("Running reconciliation")
                self.reconcile()
                time.sleep(self.config.reconciliation_interval)
        except KeyboardInterrupt:
            logger.info("Reconciliation loop interrupted, shutting down")
        except Exception as e:
            logger.exception(f"Error in reconciliation loop: {str(e)}")

    def ensure_naive_datetime(self, dt: datetime.datetime) -> datetime.datetime:
        """Ensure the datetime object is naive before localizing.

        Args:
            dt: The datetime object to check.

        Returns:
            The naive datetime object.
        """
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
