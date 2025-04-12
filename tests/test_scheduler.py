"""Tests for the scheduler module."""

import datetime
import unittest
from unittest import mock

from tarnfui.config import TarnfuiConfig, Weekday
from tarnfui.kubernetes import KubernetesClient
from tarnfui.scheduler import Scheduler


class TestScheduler(unittest.TestCase):
    """Test cases for the Scheduler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = TarnfuiConfig(
            shutdown_time="19:00",
            startup_time="07:00",
            active_days=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
            timezone="UTC",
        )
        self.k8s_client = mock.Mock(spec=KubernetesClient)
        self.scheduler = Scheduler(config=self.config, kubernetes_client=self.k8s_client)

    def test_parse_time(self):
        """Test that time parsing works correctly."""
        time = self.scheduler._parse_time("13:45")
        self.assertEqual(time.hour, 13)
        self.assertEqual(time.minute, 45)

    @mock.patch("tarnfui.scheduler.Scheduler.should_be_active")
    def test_reconcile_active_hours(self, mock_should_be_active):
        """Test that reconcile starts deployments during active hours."""
        # Configure should_be_active to return True
        mock_should_be_active.return_value = True

        # Call reconcile
        self.scheduler.reconcile()

        # Verify that start_deployments was called and stop_deployments was not
        self.k8s_client.start_deployments.assert_called_once()
        self.k8s_client.stop_deployments.assert_not_called()

    @mock.patch("tarnfui.scheduler.Scheduler.should_be_active")
    def test_reconcile_inactive_hours(self, mock_should_be_active):
        """Test that reconcile stops deployments during inactive hours."""
        # Configure should_be_active to return False
        mock_should_be_active.return_value = False

        # Call reconcile
        self.scheduler.reconcile()

        # Verify that stop_deployments was called and start_deployments was not
        self.k8s_client.stop_deployments.assert_called_once()
        self.k8s_client.start_deployments.assert_not_called()

    @mock.patch("tarnfui.scheduler.Scheduler.get_current_datetime")
    def test_should_be_active_weekday_work_hours(self, mock_get_current_datetime):
        """Test that cluster should be active during work hours on weekdays."""
        # Tuesday at 10:00 (during work hours)
        dt = datetime.datetime(2023, 1, 3, 10, 0, tzinfo=None)
        mock_get_current_datetime.return_value = dt

        self.assertTrue(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.Scheduler.get_current_datetime")
    def test_should_be_inactive_weekday_night(self, mock_get_current_datetime):
        """Test that cluster should be inactive during night hours on weekdays."""
        # Wednesday at 20:00 (after work hours)
        dt = datetime.datetime(2023, 1, 4, 20, 0, tzinfo=None)
        mock_get_current_datetime.return_value = dt

        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.Scheduler.get_current_datetime")
    def test_should_be_inactive_weekend(self, mock_get_current_datetime):
        """Test that cluster should be inactive on weekends."""
        # Saturday at 12:00
        dt = datetime.datetime(2023, 1, 7, 12, 0, tzinfo=None)
        mock_get_current_datetime.return_value = dt

        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.Scheduler.get_current_datetime")
    def test_timezone_support(self, mock_get_current_datetime):
        """Test that timezone support works correctly."""
        # Create a scheduler with Paris timezone
        config = TarnfuiConfig(
            shutdown_time="19:00",
            startup_time="07:00",
            active_days=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
            timezone="Europe/Paris",
        )
        scheduler = Scheduler(config=config, kubernetes_client=self.k8s_client)

        # Tuesday at 08:00 UTC (09:00 in Paris - should be active)
        dt = datetime.datetime(2023, 1, 3, 9, 0, tzinfo=None)
        mock_get_current_datetime.return_value = dt

        self.assertTrue(scheduler.should_be_active())

        # Same day at 19:00 Paris time (should be inactive)
        dt = datetime.datetime(2023, 1, 3, 19, 0, tzinfo=None)
        mock_get_current_datetime.return_value = dt

        self.assertFalse(scheduler.should_be_active())


if __name__ == "__main__":
    unittest.main()
