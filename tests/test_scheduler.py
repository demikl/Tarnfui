"""Tests for the scheduler module."""

import datetime
import unittest
from unittest import mock

from tarnfui.config import TarnfuiConfig
from tarnfui.kubernetes import KubernetesClient
from tarnfui.scheduler import Scheduler


class TestScheduler(unittest.TestCase):
    """Test cases for the Scheduler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = TarnfuiConfig(
            shutdown_time="19:00",
            startup_time="07:00",
            active_days=[0, 1, 2, 3, 4]  # Monday to Friday
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
        # Tuesday at 10:00
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 3, 10, 0)
        self.assertTrue(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_should_be_inactive_weekday_night(self, mock_datetime):
        """Test that cluster should be inactive during night hours on weekdays."""
        # Wednesday at 20:00
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 4, 20, 0)
        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_should_be_inactive_weekend(self, mock_datetime):
        """Test that cluster should be inactive on weekends."""
        # Saturday at 12:00
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 7, 12, 0)
        self.assertFalse(self.scheduler.should_be_active())

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_reconcile_active_hours(self, mock_datetime):
        """Test that reconcile starts deployments during active hours."""
        # Monday at 09:00
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 2, 9, 0)
        self.scheduler.reconcile()
        self.k8s_client.start_deployments.assert_called_once()
        self.k8s_client.stop_deployments.assert_not_called()

    @mock.patch("tarnfui.scheduler.datetime.datetime")
    def test_reconcile_inactive_hours(self, mock_datetime):
        """Test that reconcile stops deployments during inactive hours."""
        # Friday at 22:00
        mock_datetime.now.return_value = datetime.datetime(2023, 1, 6, 22, 0)
        self.scheduler.reconcile()
        self.k8s_client.stop_deployments.assert_called_once()
        self.k8s_client.start_deployments.assert_not_called()


if __name__ == "__main__":
    unittest.main()
