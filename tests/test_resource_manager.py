"""Tests for the ResourceManager functionality."""

import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_owner_reference import V1OwnerReference

from tarnfui.kubernetes.base import ResourceManager
from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.managers import ApplicationManager


class TestResourceManager(unittest.TestCase):
    """Unit tests for the ResourceManager base class and implementations."""

    def setUp(self):
        """Set up test environment before each test method."""
        # Create a mock KubernetesConnection with the necessary attributes
        self.mock_connection = MagicMock(spec=KubernetesConnection)
        self.mock_connection.custom_objects_api = MagicMock()

        # Create an ApplicationManager instance
        self.app_manager = ApplicationManager(self.mock_connection, namespace="default")

        # Create a mock resource that would typically be managed
        self.mock_deployment = MagicMock(spec=V1Deployment)
        self.mock_deployment.metadata = MagicMock(spec=V1ObjectMeta)
        self.mock_deployment.metadata.name = "test-deployment"
        self.mock_deployment.metadata.namespace = "default"
        self.mock_deployment.metadata.labels = {"app.kubernetes.io/managed-by": "test-app-manager"}

        # Create another mock resource without the managed-by label
        self.unmanaged_deployment = MagicMock(spec=V1Deployment)
        self.unmanaged_deployment.metadata = MagicMock(spec=V1ObjectMeta)
        self.unmanaged_deployment.metadata.name = "unmanaged-deployment"
        self.unmanaged_deployment.metadata.namespace = "default"
        self.unmanaged_deployment.metadata.labels = {}

        # Create a mock resource with owner reference
        self.owner_ref_deployment = MagicMock(spec=V1Deployment)
        self.owner_ref_deployment.metadata = MagicMock(spec=V1ObjectMeta)
        self.owner_ref_deployment.metadata.name = "owner-ref-deployment"
        self.owner_ref_deployment.metadata.namespace = "default"
        self.owner_ref_deployment.metadata.labels = {}

        owner_ref = MagicMock(spec=V1OwnerReference)
        owner_ref.kind = "Application"
        owner_ref.api_version = "tarnfui.io/v1"
        owner_ref.name = "test-app-manager"

        self.owner_ref_deployment.metadata.owner_references = [owner_ref]

    def test_find_manager_by_label(self):
        """Test finding a manager for a resource using labels."""
        # Patch the get_resource method to return a mock manager
        with patch.object(ApplicationManager, "get_resource") as mock_get_resource:
            mock_get_resource.return_value = {
                "metadata": {
                    "name": "test-app-manager",
                    "namespace": "default",
                    "annotations": {},
                },
                "spec": {"suspended": False},
            }

            # Test finding a manager for a resource with the managed-by label
            manager = ApplicationManager.find_manager_for_resource(self.mock_deployment, self.mock_connection)

            # Verify that a manager was found
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, ApplicationManager)

            # Verify that get_resource was called with the correct arguments
            mock_get_resource.assert_called_once_with("test-app-manager", "default")

            # Test finding a manager for a resource without the managed-by label
            manager = ApplicationManager.find_manager_for_resource(self.unmanaged_deployment, self.mock_connection)

            # Verify that no manager was found
            self.assertIsNone(manager)

    def test_find_manager_by_owner_reference(self):
        """Test finding a manager for a resource using owner references."""
        # Patch the get_resource method to return a mock manager
        with patch.object(ApplicationManager, "get_resource") as mock_get_resource:
            mock_get_resource.return_value = {
                "metadata": {
                    "name": "test-app-manager",
                    "namespace": "default",
                    "annotations": {},
                },
                "spec": {"suspended": False},
            }

            # Test finding a manager for a resource with an owner reference
            manager = ApplicationManager.find_manager_for_resource(self.owner_ref_deployment, self.mock_connection)

            # Verify that a manager was found
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, ApplicationManager)

            # Verify that get_resource was called with the correct arguments
            mock_get_resource.assert_called_once_with("test-app-manager", "default")

    def test_lru_cache_functionality(self):
        """Test that the LRU cache for processed managers works correctly."""
        # Clear the cache to start fresh
        ResourceManager.clear_processed_managers()

        # Add a few managers to the cache
        ResourceManager.mark_manager_processed("default/manager-1")
        ResourceManager.mark_manager_processed("default/manager-2")

        # Check that the managers are in the cache
        self.assertTrue(ResourceManager.is_manager_processed("default/manager-1"))
        self.assertTrue(ResourceManager.is_manager_processed("default/manager-2"))

        # Add more managers to test the LRU behavior
        # We'll use a smaller cache size for testing
        original_cache_size = ResourceManager._LRU_CACHE_SIZE
        ResourceManager._LRU_CACHE_SIZE = 3

        ResourceManager.mark_manager_processed("default/manager-3")
        ResourceManager.mark_manager_processed("default/manager-4")  # This should evict manager-1

        # Check that manager-1 was evicted
        self.assertFalse(ResourceManager.is_manager_processed("default/manager-1"))
        self.assertTrue(ResourceManager.is_manager_processed("default/manager-2"))
        self.assertTrue(ResourceManager.is_manager_processed("default/manager-3"))
        self.assertTrue(ResourceManager.is_manager_processed("default/manager-4"))

        # Reset the cache size
        ResourceManager._LRU_CACHE_SIZE = original_cache_size

        # Clear the cache
        ResourceManager.clear_processed_managers()

        # Verify that the cache is empty
        self.assertFalse(ResourceManager.is_manager_processed("default/manager-2"))
        self.assertFalse(ResourceManager.is_manager_processed("default/manager-3"))
        self.assertFalse(ResourceManager.is_manager_processed("default/manager-4"))

    def test_get_current_state(self):
        """Test getting the current state of a resource manager."""
        # Create a mock resource manager
        mock_manager = {
            "metadata": {
                "name": "test-app-manager",
                "namespace": "default",
                "annotations": {},
            },
            "spec": {"suspended": False},
        }

        # Get the current state
        state = self.app_manager.get_current_state(mock_manager)

        # Verify that the state is correct
        self.assertFalse(state)

        # Change the state and test again
        mock_manager["spec"]["suspended"] = True
        state = self.app_manager.get_current_state(mock_manager)

        # Verify that the state is correct
        self.assertTrue(state)

    def test_suspend_and_resume_resource(self):
        """Test suspending and resuming a resource manager."""
        # Create a mock resource manager
        mock_manager = {
            "metadata": {
                "name": "test-app-manager",
                "namespace": "default",
                "annotations": {},
            },
            "spec": {"suspended": False},
        }

        # Suspend the resource
        self.app_manager.suspend_resource(mock_manager)

        # Verify that the resource was suspended
        self.assertTrue(mock_manager["spec"]["suspended"])

        # Resume the resource
        self.app_manager.resume_resource(mock_manager, False)

        # Verify that the resource was resumed
        self.assertFalse(mock_manager["spec"]["suspended"])

    def test_is_suspended(self):
        """Test checking if a resource manager is suspended."""
        # Create a mock resource manager
        mock_manager = {
            "metadata": {
                "name": "test-app-manager",
                "namespace": "default",
                "annotations": {},
            },
            "spec": {"suspended": False},
        }

        # Check if the resource is suspended
        is_suspended = self.app_manager.is_suspended(mock_manager)

        # Verify that the resource is not suspended
        self.assertFalse(is_suspended)

        # Change the state and test again
        mock_manager["spec"]["suspended"] = True
        is_suspended = self.app_manager.is_suspended(mock_manager)

        # Verify that the resource is suspended
        self.assertTrue(is_suspended)


if __name__ == "__main__":
    unittest.main()
