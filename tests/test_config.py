"""Tests for the configuration module."""

import os
import unittest
from unittest import mock

from tarnfui.config import TarnfuiConfig


class TestTarnfuiConfig(unittest.TestCase):
    """Test cases for TarnfuiConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = TarnfuiConfig()
        self.assertEqual(config.shutdown_time, "19:00")
        self.assertEqual(config.startup_time, "07:00")
        self.assertEqual(config.active_days, [0, 1, 2, 3, 4])
        self.assertEqual(config.reconciliation_interval, 60)
        self.assertIsNone(config.namespace)

    def test_from_env(self):
        """Test that values are loaded from environment variables."""
        with mock.patch.dict(os.environ, {
            "TARNFUI_SHUTDOWN_TIME": "20:00",
            "TARNFUI_STARTUP_TIME": "08:30",
            "TARNFUI_ACTIVE_DAYS": "1,3,5",
            "TARNFUI_RECONCILIATION_INTERVAL": "30",
            "TARNFUI_NAMESPACE": "test-ns"
        }):
            config = TarnfuiConfig.from_env()

            self.assertEqual(config.shutdown_time, "20:00")
            self.assertEqual(config.startup_time, "08:30")
            self.assertEqual(config.active_days, [1, 3, 5])
            self.assertEqual(config.reconciliation_interval, 30)
            self.assertEqual(config.namespace, "test-ns")

    def test_time_format_validation(self):
        """Test that time format validation works correctly."""
        # Valid times should not raise exceptions
        TarnfuiConfig(shutdown_time="00:00", startup_time="23:59")

        # Invalid hour
        with self.assertRaises(ValueError):
            TarnfuiConfig(shutdown_time="24:00")

        # Invalid minute
        with self.assertRaises(ValueError):
            TarnfuiConfig(startup_time="12:60")

        # Invalid format
        with self.assertRaises(ValueError):
            TarnfuiConfig(shutdown_time="19-00")

    def test_active_days_validation(self):
        """Test that active days validation works correctly."""
        # Valid days should not raise exceptions
        TarnfuiConfig(active_days=[0, 1, 2, 3, 4, 5, 6])

        # Invalid day (negative)
        with self.assertRaises(ValueError):
            TarnfuiConfig(active_days=[-1, 1, 2])

        # Invalid day (too large)
        with self.assertRaises(ValueError):
            TarnfuiConfig(active_days=[1, 7, 2])


if __name__ == "__main__":
    unittest.main()
