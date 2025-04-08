"""Tests for the scheduler module."""

import datetime
import unittest
from unittest import mock

import pytz

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
            active_days=[Weekday.MON, Weekday.TUE,
                         Weekday.WED, Weekday.THU, Weekday.FRI],
            timezone="UTC"
        )
        self.k8s_client = mock.Mock(spec=KubernetesClient)
        self.scheduler = Scheduler(
            config=self.config, kubernetes_client=self.k8s_client)

    def test_parse_time(self):
        """Test that time parsing works correctly."""
        time = self.scheduler._parse_time("13:45")
        self.assertEqual(time.hour, 13)
        self.assertEqual(time.minute, 45)

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_should_be_active_weekday_work_hours(self, mock_datetime):
        """Test that cluster should be active during work hours on weekdays."""
        # Create a timezone-aware datetime
        dt = datetime.datetime(2023, 1, 3, 10, 0)  # Tuesday at 10:00
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.assertTrue(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_should_be_inactive_weekday_night(self, mock_datetime):
        """Test that cluster should be inactive during night hours on weekdays."""
        # Wednesday at 20:00
        dt = datetime.datetime(2023, 1, 4, 20, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_should_be_inactive_weekend(self, mock_datetime):
        """Test that cluster should be inactive on weekends."""
        # Saturday at 12:00
        dt = datetime.datetime(2023, 1, 7, 12, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_timezone_support(self, mock_datetime):
        """Test that timezone support works correctly."""
        # Create a scheduler with Paris timezone
        config = TarnfuiConfig(
            shutdown_time="19:00",
            startup_time="07:00",
            active_days=[Weekday.MON, Weekday.TUE,
                         Weekday.WED, Weekday.THU, Weekday.FRI],
            timezone="Europe/Paris"
        )
        scheduler = Scheduler(config=config, kubernetes_client=self.k8s_client)

        # Tuesday at 08:00 UTC (09:00 in Paris - should be active)
        dt = datetime.datetime(2023, 1, 3, 8, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.assertTrue(scheduler.should_be_active())

        # Same day at 18:00 UTC (19:00 in Paris - should be inactive)
        dt = datetime.datetime(2023, 1, 3, 18, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.assertFalse(scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_reconcile_active_hours(self, mock_datetime):
        """Test that reconcile starts deployments during active hours."""
        # Monday at 09:00
        dt = datetime.datetime(2023, 1, 2, 9, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.scheduler.reconcile()
        self.k8s_client.start_deployments.assert_called_once()
        self.k8s_client.stop_deployments.assert_not_called()

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_reconcile_inactive_hours(self, mock_datetime):
        """Test that reconcile stops deployments during inactive hours."""
        # Friday at 22:00
        dt = datetime.datetime(2023, 1, 6, 22, 0)
        dt_utc = pytz.UTC.localize(dt)
        mock_datetime.now.return_value = dt_utc

        self.scheduler.reconcile()
        self.k8s_client.stop_deployments.assert_called_once()
        self.k8s_client.start_deployments.assert_not_called()


if __name__ == "__main__":
    unittest.main()
