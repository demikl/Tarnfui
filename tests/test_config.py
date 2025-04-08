"""Tests for the configuration module."""

import os
import unittest
from unittest import mock

from tarnfui.config import TarnfuiConfig, Weekday


class TestWeekday(unittest.TestCase):
    """Test cases for the Weekday enum."""

    def test_weekday_values(self):
        """Test that Weekday enum values are correct."""
        self.assertEqual(Weekday.MON.value, "mon")
        self.assertEqual(Weekday.TUE.value, "tue")
        self.assertEqual(Weekday.WED.value, "wed")
        self.assertEqual(Weekday.THU.value, "thu")
        self.assertEqual(Weekday.FRI.value, "fri")
        self.assertEqual(Weekday.SAT.value, "sat")
        self.assertEqual(Weekday.SUN.value, "sun")

    def test_to_integer(self):
        """Test conversion from Weekday to integer."""
        self.assertEqual(Weekday.to_integer(Weekday.MON), 0)
        self.assertEqual(Weekday.to_integer(Weekday.TUE), 1)
        self.assertEqual(Weekday.to_integer(Weekday.WED), 2)
        self.assertEqual(Weekday.to_integer(Weekday.THU), 3)
        self.assertEqual(Weekday.to_integer(Weekday.FRI), 4)
        self.assertEqual(Weekday.to_integer(Weekday.SAT), 5)
        self.assertEqual(Weekday.to_integer(Weekday.SUN), 6)

        # Test string conversion
        self.assertEqual(Weekday.to_integer("mon"), 0)
        self.assertEqual(Weekday.to_integer("tue"), 1)

    def test_from_integer(self):
        """Test conversion from integer to Weekday."""
        self.assertEqual(Weekday.from_integer(0), Weekday.MON)
        self.assertEqual(Weekday.from_integer(1), Weekday.TUE)
        self.assertEqual(Weekday.from_integer(2), Weekday.WED)
        self.assertEqual(Weekday.from_integer(3), Weekday.THU)
        self.assertEqual(Weekday.from_integer(4), Weekday.FRI)
        self.assertEqual(Weekday.from_integer(5), Weekday.SAT)
        self.assertEqual(Weekday.from_integer(6), Weekday.SUN)

        # Test invalid value
        with self.assertRaises(ValueError):
            Weekday.from_integer(7)


class TestTarnfuiConfig(unittest.TestCase):
    """Test cases for TarnfuiConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = TarnfuiConfig()
        self.assertEqual(config.shutdown_time, "19:00")
        self.assertEqual(config.startup_time, "07:00")
        self.assertEqual(config.active_days, [
                         Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI])
        self.assertEqual(config.timezone, "UTC")
        self.assertEqual(config.reconciliation_interval, 60)
        self.assertIsNone(config.namespace)

    def test_from_env(self):
        """Test that values are loaded from environment variables."""
        with mock.patch.dict(os.environ, {
            "TARNFUI_SHUTDOWN_TIME": "20:00",
            "TARNFUI_STARTUP_TIME": "08:30",
            "TARNFUI_ACTIVE_DAYS": "mon,wed,fri",
            "TARNFUI_TIMEZONE": "Europe/Paris",
            "TARNFUI_RECONCILIATION_INTERVAL": "30",
            "TARNFUI_NAMESPACE": "test-ns"
        }):
            config = TarnfuiConfig.from_env()

            self.assertEqual(config.shutdown_time, "20:00")
            self.assertEqual(config.startup_time, "08:30")
            self.assertEqual(config.active_days, [
                             Weekday.MON, Weekday.WED, Weekday.FRI])
            self.assertEqual(config.timezone, "Europe/Paris")
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

    def test_timezone_validation(self):
        """Test that timezone validation works correctly."""
        # Valid timezones should not raise exceptions
        TarnfuiConfig(timezone="UTC")
        TarnfuiConfig(timezone="Europe/Paris")
        TarnfuiConfig(timezone="America/New_York")

        # Invalid timezone
        with self.assertRaises(ValueError):
            TarnfuiConfig(timezone="Invalid/Timezone")


if __name__ == "__main__":
    unittest.main()
