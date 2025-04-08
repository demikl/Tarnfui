"""Scheduler module for Tarnfui.

This module handles the scheduling of operations based on time of day and day of week.
"""
import datetime
import logging
import time

from tarnfui.config import TarnfuiConfig
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

    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse a time string into a datetime.time object.

        Args:
            time_str: Time string in format HH:MM.

        Returns:
            The parsed time object.
        """
        hour, minute = map(int, time_str.split(":"))
        return datetime.time(hour=hour, minute=minute)

    def should_be_active(self) -> bool:
        """Determine if the cluster should be active based on current time and day.

        Returns:
            True if the cluster should be active, False otherwise.
        """
        now = datetime.datetime.now()
        current_day = now.weekday()  # 0 is Monday, 6 is Sunday
        current_time = now.time()

        # Check if today is an active day
        if current_day not in self.config.active_days:
            logger.info(f"Today (day {current_day}) is not an active day")
            return False

        # Parse configured times
        shutdown_time = self._parse_time(self.config.shutdown_time)
        startup_time = self._parse_time(self.config.startup_time)

        # If shutdown is before startup, active hours are considered to be between startup and shutdown
        # Otherwise, it's active except between shutdown and startup
        if shutdown_time < startup_time:
            # Special case: shutdown is before startup (e.g., 19:00 to 07:00)
            if startup_time <= current_time < shutdown_time:
                logger.info("Current time is within active hours")
                return True
            else:
                logger.info("Current time is outside active hours")
                return False
        else:
            # Special case: shutdown is after startup (e.g., 07:00 to 19:00)
            if shutdown_time <= current_time or current_time < startup_time:
                logger.info("Current time is outside active hours")
                return False
            else:
                logger.info("Current time is within active hours")
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
        logger.info(
            f"Starting reconciliation loop with interval {self.config.reconciliation_interval} seconds")

        try:
            while True:
                logger.info("Running reconciliation")
                self.reconcile()
                time.sleep(self.config.reconciliation_interval)
        except KeyboardInterrupt:
            logger.info("Reconciliation loop interrupted, shutting down")
        except Exception as e:
            logger.exception(f"Error in reconciliation loop: {str(e)}")
