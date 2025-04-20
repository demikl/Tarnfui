"""Tests for the CronJob resource handler."""

import unittest
from unittest.mock import MagicMock

from tarnfui.kubernetes.resources.cronjobs import CronJobResource


class TestCronJobResource(unittest.TestCase):
    """Tests for the CronJob resource handler."""

    def setUp(self):
        """Set up the test."""
        self.connection = MagicMock()
        self.connection.batch_v1_api = MagicMock()
        self.resource = CronJobResource(self.connection)

    def test_suspend_resource(self):
        """Test suspending a CronJob resource."""
        # Create a mock CronJob
        cronjob = MagicMock()
        cronjob.metadata.name = "test-cronjob"
        cronjob.metadata.namespace = "default"
        cronjob.metadata.annotations = {}
        cronjob.spec.suspend = False  # Initially not suspended

        # Suspend the CronJob
        self.resource.suspend_resource(cronjob)

        # Verify the patch was called correctly
        self.resource.api.patch_namespaced_cron_job.assert_called_once_with(
            name=cronjob.metadata.name,
            namespace=cronjob.metadata.namespace,
            body={"spec": {"suspend": True}},
        )

    def test_resume_resource_active(self):
        """Test resuming a CronJob resource that was active before."""
        # Create a mock CronJob
        cronjob = MagicMock()
        cronjob.metadata.name = "test-cronjob"
        cronjob.metadata.namespace = "default"
        cronjob.metadata.annotations = {}
        cronjob.spec.suspend = True  # Currently suspended by Tarnfui

        # Resume the CronJob that was active before Tarnfui suspended it
        self.resource.resume_resource(cronjob, False)

        # Verify the patch was called correctly to reactivate the CronJob
        self.resource.api.patch_namespaced_cron_job.assert_called_once_with(
            name=cronjob.metadata.name,
            namespace=cronjob.metadata.namespace,
            body={"spec": {"suspend": False}},
        )

    def test_resume_resource_suspended(self):
        """Test resuming a CronJob resource that was already suspended before."""
        # Create a mock CronJob
        cronjob = MagicMock()
        cronjob.metadata.name = "test-cronjob-suspended"
        cronjob.metadata.namespace = "default"
        cronjob.metadata.annotations = {}
        cronjob.spec.suspend = True  # Currently suspended by Tarnfui

        # Resume the CronJob that was already suspended before Tarnfui
        # (should remain suspended)
        self.resource.resume_resource(cronjob, True)

        # Verify the patch was called correctly to keep the CronJob suspended
        self.resource.api.patch_namespaced_cron_job.assert_called_once_with(
            name=cronjob.metadata.name,
            namespace=cronjob.metadata.namespace,
            body={"spec": {"suspend": True}},
        )

    def test_is_suspended(self):
        """Test checking if a CronJob is suspended."""
        # Create a mock CronJob that is suspended
        suspended_cronjob = MagicMock()
        suspended_cronjob.spec.suspend = True

        # Create a mock CronJob that is not suspended
        active_cronjob = MagicMock()
        active_cronjob.spec.suspend = False

        # Verify the suspension check
        self.assertTrue(self.resource.is_suspended(suspended_cronjob))
        self.assertFalse(self.resource.is_suspended(active_cronjob))

    def test_get_current_state(self):
        """Test getting the current state of a CronJob."""
        # Create a mock CronJob with suspend=True
        cronjob = MagicMock()
        cronjob.spec.suspend = True

        # Verify the current state
        self.assertTrue(self.resource.get_current_state(cronjob))

        # Change the suspension state
        cronjob.spec.suspend = False
        self.assertFalse(self.resource.get_current_state(cronjob))

    def test_convert_state_from_string(self):
        """Test converting a state string to a boolean."""
        self.assertTrue(self.resource.convert_state_from_string("true"))
        self.assertTrue(self.resource.convert_state_from_string("TRUE"))
        self.assertTrue(self.resource.convert_state_from_string("True"))
        self.assertFalse(self.resource.convert_state_from_string("false"))
        self.assertFalse(self.resource.convert_state_from_string("FALSE"))
        self.assertFalse(self.resource.convert_state_from_string("False"))
        # Any other value should return False
        self.assertFalse(self.resource.convert_state_from_string("invalid"))


if __name__ == "__main__":
    unittest.main()
